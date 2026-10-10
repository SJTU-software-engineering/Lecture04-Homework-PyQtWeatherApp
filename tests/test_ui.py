import threading
import time
from datetime import date

import pytest
from PyQt6.QtCore import QDate
from PyQt6.QtTest import QTest

from weather_app.models import CITIES, WeatherResult
from weather_app.service import WeatherError, WeatherService
from weather_app.ui import WeatherWindow

DAY = date(2026, 10, 10)


def wait_until(app, condition, timeout=3000):
    deadline = time.monotonic() + timeout / 1000
    while not condition() and time.monotonic() < deadline:
        app.processEvents()
        QTest.qWait(5)
    assert condition(), "Qt condition did not complete before timeout"


class FakeService:
    def __init__(self, failure=None, gate=None):
        self.failure = failure
        self.gate = gate
        self.calls = []
        self.started = threading.Event()

    def query(self, city, day, demo=False):
        self.calls.append((city, day, demo, threading.get_ident()))
        self.started.set()
        if self.gate is not None and not self.gate.wait(3):
            raise RuntimeError("test gate timed out")
        if self.failure is not None:
            raise self.failure
        return WeatherResult(city, day, 61, 12, 22.5, 1.2, 15,
                             "模拟测试来源" if demo else "测试来源", demo)


@pytest.fixture
def windows(app):
    created = []
    def factory(service):
        window = WeatherWindow(service)
        window.date_edit.setDate(QDate(DAY))
        window.show()
        app.processEvents()
        created.append(window)
        return window
    yield factory
    for window in created:
        if window.worker is not None:
            gate = getattr(window.service, "gate", None)
            if gate is not None: gate.set()
            wait_until(app, lambda: window.worker is None, 5000)
        window.close()
        window.deleteLater()
    app.processEvents()


def test_success_selected_inputs_and_actual_worker_thread(app, windows):
    service = FakeService()
    window = windows(service)
    window.city_combo.setCurrentIndex(1)
    window.query_button.click()
    wait_until(app, lambda: window.worker is None)
    assert service.calls[0][:3] == (CITIES[1], DAY, False)
    assert service.calls[0][3] != threading.get_ident()
    assert window.summary_label.text() == "上海 · 2026-10-10 · 小雨"
    assert window.metric_labels["temperature"].text() == "12.0 ～ 22.5 °C"
    assert window.metric_labels["precipitation"].text() == "1.2 mm"
    assert window.metric_labels["wind"].text() == "15.0 km/h"
    assert window.status_label.text() == "查询成功。"
    assert window.source_label.text() == "数据来源：测试来源"
    assert window.query_button.isEnabled()


@pytest.mark.parametrize("error,expected", [(WeatherError("网络不可用"), "网络不可用"),
                                           (RuntimeError("private diagnostic"), "意外错误")])
def test_error_clears_previous_results_and_recovers(app, windows, error, expected):
    service = FakeService()
    window = windows(service)
    window.start_query()
    wait_until(app, lambda: window.worker is None)
    service.failure = error
    window.start_query()
    wait_until(app, lambda: window.worker is None)
    assert expected in window.status_label.text()
    assert "private diagnostic" not in window.status_label.text()
    assert window.summary_label.text() == "尚无查询结果"
    assert all(label.text() == "—" for label in window.metric_labels.values())
    assert window.source_label.text() == "数据来源：—"
    assert all(widget.isEnabled() for widget in (window.city_combo, window.date_edit,
                                               window.demo_check, window.query_button))
    service.failure = None
    window.query_button.click()
    wait_until(app, lambda: window.worker is None)
    assert window.status_label.text() == "查询成功。" and len(service.calls) == 3


def test_busy_prevents_duplicate_and_ui_event_loop_remains_responsive(app, windows):
    gate = threading.Event()
    service = FakeService(gate=gate)
    window = windows(service)
    window.start_query()
    wait_until(app, service.started.is_set)
    worker = window.worker
    assert not any(widget.isEnabled() for widget in (window.city_combo, window.date_edit,
                                                    window.demo_check, window.query_button))
    window.start_query()
    window.query_button.click()
    app.processEvents()
    assert window.worker is worker and len(service.calls) == 1
    assert window.query_button.text() == "查询中…"
    gate.set()
    wait_until(app, lambda: window.worker is None)
    assert all(widget.isEnabled() for widget in (window.city_combo, window.date_edit,
                                               window.demo_check, window.query_button))


def test_demo_visible_labels(app, windows):
    window = windows(WeatherService(today=lambda: DAY))
    window.demo_check.setChecked(True)
    window.query_button.click()
    wait_until(app, lambda: window.worker is None)
    assert "模拟数据" in window.status_label.text() and "不能代表真实天气" in window.status_label.text()
    assert "模拟" in window.source_label.text() and "非真实天气" in window.source_label.text()


@pytest.mark.parametrize("day,expected", [(date(1939, 12, 31), "1940-01-01"),
                                         (date(2026, 10, 26), "最晚可选")])
def test_invalid_date_error_in_ui(app, windows, day, expected):
    def forbidden(_): pytest.fail("invalid date accessed network")
    window = windows(WeatherService(reader=forbidden, today=lambda: DAY))
    window.date_edit.setDate(QDate(day))
    window.start_query()
    wait_until(app, lambda: window.worker is None)
    assert expected in window.status_label.text()
    assert window.query_button.isEnabled()


@pytest.mark.parametrize("failure", [None, WeatherError("网络失败")])
def test_close_during_active_thread_waits_then_closes(app, windows, failure):
    gate = threading.Event()
    service = FakeService(failure=failure, gate=gate)
    window = windows(service)
    window.start_query()
    wait_until(app, service.started.is_set)
    assert window.worker.isRunning()
    assert window.close() is False
    assert window.isVisible() and window._closing
    assert "等待" in window.status_label.text()
    gate.set()
    wait_until(app, lambda: window.worker is None and not window.isVisible())
    assert len(service.calls) == 1
