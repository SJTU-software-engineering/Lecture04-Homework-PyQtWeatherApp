"""运行方式：python main.py。"""
import sys
from PyQt6.QtWidgets import QApplication
from weather_app.ui import WeatherWindow


def main() -> int:
    app = QApplication(sys.argv)
    window = WeatherWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
