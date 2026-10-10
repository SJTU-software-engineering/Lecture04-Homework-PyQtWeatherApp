"""PyQt6 中文界面；网络查询始终在工作线程执行。"""
from PyQt6.QtCore import QDate, QThread, Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QCheckBox, QComboBox, QDateEdit, QFormLayout, QGroupBox,
    QHBoxLayout, QLabel, QMainWindow, QPushButton, QVBoxLayout, QWidget,
)

from .models import CITIES, weather_description
from .service import MIN_DATE, WeatherError, WeatherService, china_today


class QueryThread(QThread):
    result_ready = pyqtSignal(object)
    error_ready = pyqtSignal(str)

    def __init__(self, service, city, day, demo, parent=None):
        super().__init__(parent)
        self.service, self.city, self.day, self.demo = service, city, day, demo

    def run(self):
        try:
            self.result_ready.emit(self.service.query(self.city, self.day, self.demo))
        except WeatherError as exc:
            self.error_ready.emit(str(exc))
        except Exception:
            self.error_ready.emit("查询发生意外错误，请稍后重试。")


class WeatherWindow(QMainWindow):
    def __init__(self, service=None):
        super().__init__()
        self.service = service if service is not None else WeatherService()
        self.worker = None
        self._closing = False
        self.setWindowTitle("日期天气查询 · PyQt 课程作业")
        self.resize(660, 520)
        root = QWidget()
        self.setCentralWidget(root)
        layout = QVBoxLayout(root)
        layout.setContentsMargins(28, 24, 28, 24)
        title = QLabel("日期天气查询")
        title.setObjectName("title")
        layout.addWidget(title)
        hint = QLabel("选择城市和日期，查询每日天气、温度、降水与最大风速。")
        hint.setWordWrap(True)
        layout.addWidget(hint)
        form = QFormLayout()
        self.city_combo = QComboBox()
        for city in CITIES:
            self.city_combo.addItem(city.name, city)
        form.addRow("城市", self.city_combo)
        self.date_edit = QDateEdit()
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setDisplayFormat("yyyy-MM-dd")
        self.date_edit.setDate(QDate(china_today()))
        # 放宽控件范围，让业务层对不支持日期给出可见解释。
        self.date_edit.setDateRange(QDate(1900, 1, 1), QDate(2100, 12, 31))
        form.addRow("日期", self.date_edit)
        layout.addLayout(form)
        self.demo_check = QCheckBox("离线演示（模拟数据，非真实天气）")
        layout.addWidget(self.demo_check)
        self.query_button = QPushButton("查询天气")
        self.query_button.clicked.connect(self.start_query)
        layout.addWidget(self.query_button)
        self.status_label = QLabel("准备就绪。支持 1940 年起的历史数据及今天起 16 天内的预报。")
        self.status_label.setWordWrap(True)
        self.status_label.setTextFormat(Qt.TextFormat.PlainText)
        layout.addWidget(self.status_label)
        box = QGroupBox("查询结果")
        result_layout = QVBoxLayout(box)
        self.summary_label = QLabel("尚未查询")
        self.summary_label.setObjectName("summary")
        result_layout.addWidget(self.summary_label)
        metrics = QFormLayout()
        self.metric_labels = {}
        for key, caption in (("temperature", "温度范围"), ("precipitation", "全天降水量"), ("wind", "最大风速")):
            value = QLabel("—")
            self.metric_labels[key] = value
            metrics.addRow(caption, value)
        result_layout.addLayout(metrics)
        self.source_label = QLabel("数据来源：—")
        self.source_label.setWordWrap(True)
        self.source_label.setTextFormat(Qt.TextFormat.PlainText)
        result_layout.addWidget(self.source_label)
        layout.addWidget(box)
        footer = QLabel("天气预报与历史再分析具有模型误差。数据由 Open-Meteo 提供。")
        footer.setWordWrap(True)
        layout.addWidget(footer)
        layout.addStretch()
        self.setStyleSheet("""
            QMainWindow { background: #f2f6fb; }
            QWidget { font-family: 'Microsoft YaHei'; font-size: 14px; color: #243247; }
            QLabel#title { font-size: 28px; font-weight: bold; color: #1759a8; }
            QLabel#summary { font-size: 20px; font-weight: bold; }
            QGroupBox { border: 1px solid #ccd7e5; border-radius: 8px; margin-top: 14px; padding: 18px 12px 12px; background: white; }
            QGroupBox::title { subcontrol-origin: margin; left: 12px; }
            QPushButton { background: #236ac2; color: white; border: 0; border-radius: 6px; padding: 11px; }
            QPushButton:disabled { background: #93afcf; }
            QComboBox, QDateEdit { padding: 6px; background: white; }
        """)

    def set_busy(self, busy):
        for widget in (self.city_combo, self.date_edit, self.demo_check, self.query_button):
            widget.setEnabled(not busy)
        self.query_button.setText("查询中…" if busy else "查询天气")

    def clear_result(self):
        self.summary_label.setText("尚无查询结果")
        for label in self.metric_labels.values():
            label.setText("—")
        self.source_label.setText("数据来源：—")

    def start_query(self):
        if self.worker is not None:
            return
        self.clear_result()
        self.set_busy(True)
        self.status_label.setText("正在查询，请稍候…")
        self.worker = QueryThread(self.service, self.city_combo.currentData(),
                                  self.date_edit.date().toPyDate(), self.demo_check.isChecked(), self)
        self.worker.result_ready.connect(self.show_result)
        self.worker.error_ready.connect(self.show_error)
        self.worker.finished.connect(self.query_finished)
        self.worker.start()

    def show_result(self, result):
        self.summary_label.setText(f"{result.city.name} · {result.day.isoformat()} · {weather_description(result.weather_code)}")
        self.metric_labels["temperature"].setText(f"{result.temperature_min:.1f} ～ {result.temperature_max:.1f} °C")
        self.metric_labels["precipitation"].setText(f"{result.precipitation:.1f} mm")
        self.metric_labels["wind"].setText(f"{result.wind_speed_max:.1f} km/h")
        self.source_label.setText(f"数据来源：{result.source}")
        self.status_label.setText("离线演示完成：以下为模拟数据，不能代表真实天气。" if result.is_demo else "查询成功。")

    def show_error(self, message):
        self.clear_result()
        self.status_label.setText(f"查询失败：{message}")

    def query_finished(self):
        worker = self.worker
        self.worker = None
        if worker is not None:
            worker.deleteLater()
        self.set_busy(False)
        if self._closing:
            self.close()

    def closeEvent(self, event):
        # 活动线程必须存活到退出；不能在网络请求中途销毁 QThread。
        if self.worker is not None:
            self._closing = True
            self.status_label.setText("正在等待当前查询结束后关闭…")
            event.ignore()
        else:
            event.accept()
