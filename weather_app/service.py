"""天气查询业务：日期路由、网络访问、严格解析与独立离线演示。"""
import hashlib
import json
import math
from datetime import date, datetime, timedelta, timezone
from typing import Callable
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from .models import City, WeatherResult

MIN_DATE = date(1940, 1, 1)
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"
DAILY_FIELDS = (
    "weather_code", "temperature_2m_min", "temperature_2m_max",
    "precipitation_sum", "wind_speed_10m_max",
)


class WeatherError(Exception):
    """可安全展示给用户的业务错误。"""


def china_today() -> date:
    return datetime.now(timezone(timedelta(hours=8))).date()


def validate_date(day: date, today: date) -> None:
    if day < MIN_DATE:
        raise WeatherError("历史天气最早支持 1940-01-01，请重新选择日期。")
    maximum = today + timedelta(days=15)
    if day > maximum:
        raise WeatherError(f"预报最多支持今天起 16 天（含今天），最晚可选 {maximum.isoformat()}。")


def read_json(url: str) -> dict:
    """网络操作设置超时与响应大小上限，调用者放在工作线程中。"""
    request = Request(url, headers={"User-Agent": "PyQtWeatherApp/1.0"})
    try:
        with urlopen(request, timeout=15) as response:
            raw = response.read(1_000_001)
        if len(raw) > 1_000_000:
            raise WeatherError("天气服务响应过大，请稍后重试。")
        data = json.loads(raw.decode("utf-8"))
        if not isinstance(data, dict):
            raise WeatherError("天气服务返回的数据格式不正确。")
        return data
    except HTTPError as exc:
        raise WeatherError(f"天气服务请求失败（HTTP {exc.code}），请稍后重试。") from exc
    except (URLError, TimeoutError, OSError) as exc:
        raise WeatherError("无法连接天气服务，请检查网络后重试，或手动选择离线演示模式。") from exc
    except (ValueError, UnicodeError) as exc:
        raise WeatherError("天气服务返回的数据无法解析，请稍后重试。") from exc


def parse_weather(data: dict, city: City, day: date, source: str) -> WeatherResult:
    """只接受所选日期的完整、有限数值；缺测不能伪装成零。"""
    try:
        if data.get("error"):
            raise WeatherError("天气服务拒绝了查询请求，请稍后重试。")
        daily = data["daily"]
        times = daily["time"]
        if not isinstance(times, list):
            raise ValueError("invalid time array")
        index = times.index(day.isoformat())
        values = []
        for key in DAILY_FIELDS:
            series = daily[key]
            if not isinstance(series, list) or len(series) != len(times):
                raise ValueError("invalid daily series")
            value = series[index]
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
                raise ValueError("missing or non-finite data")
            values.append(value)
        code, low, high, rain, wind = values
        if int(code) != code or low > high or rain < 0 or wind < 0:
            raise ValueError("invalid weather values")
        return WeatherResult(city, day, int(code), float(low), float(high), float(rain), float(wind), source)
    except (KeyError, TypeError, ValueError, IndexError, AttributeError, OverflowError) as exc:
        raise WeatherError("所选日期暂无完整天气数据，请稍后重试或选择其他日期。") from exc


class WeatherService:
    """通过注入 reader/today 支持无网络的独立单元测试。"""

    def __init__(self, reader: Callable[[str], dict] = read_json,
                 today: Callable[[], date] = china_today):
        self.reader = reader
        self.today = today

    def query(self, city: City, day: date, demo: bool = False) -> WeatherResult:
        today = self.today()
        validate_date(day, today)
        if demo:
            return self.demo_weather(city, day)
        historical = day < today - timedelta(days=92)
        endpoint = ARCHIVE_URL if historical else FORECAST_URL
        source = "Open-Meteo 历史再分析数据" if historical else (
            "Open-Meteo 近期历史模型数据" if day < today else "Open-Meteo 天气预报")
        params = {
            "latitude": city.latitude, "longitude": city.longitude,
            "start_date": day.isoformat(), "end_date": day.isoformat(),
            "daily": ",".join(DAILY_FIELDS), "timezone": "Asia/Shanghai",
            "temperature_unit": "celsius", "wind_speed_unit": "kmh",
            "precipitation_unit": "mm",
        }
        return parse_weather(self.reader(f"{endpoint}?{urlencode(params)}"), city, day, source)

    @staticmethod
    def demo_weather(city: City, day: date) -> WeatherResult:
        """稳定生成教学样例，显式标记，绝不作为网络失败的自动替代。"""
        seed = int.from_bytes(hashlib.sha256(f"{city.name}:{day.isoformat()}".encode()).digest()[:4], "big")
        code = (0, 2, 3, 61, 63, 71)[seed % 6]
        low = float(seed % 25 - 5)
        return WeatherResult(city, day, code, low, low + 5 + seed % 8,
                             float(seed % 12) if code in (61, 63, 71) else 0.0,
                             float(5 + seed % 30), "离线演示数据（模拟，非真实天气）", True)
