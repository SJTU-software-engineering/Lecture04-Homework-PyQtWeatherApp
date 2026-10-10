"""与界面无关的数据模型与天气码说明。"""
from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class City:
    name: str
    latitude: float
    longitude: float


CITIES = (
    City("北京", 39.9042, 116.4074),
    City("上海", 31.2304, 121.4737),
    City("广州", 23.1291, 113.2644),
    City("深圳", 22.5431, 114.0579),
    City("成都", 30.5728, 104.0668),
    City("杭州", 30.2741, 120.1551),
    City("武汉", 30.5928, 114.3055),
    City("西安", 34.3416, 108.9398),
)


@dataclass(frozen=True)
class WeatherResult:
    city: City
    day: date
    weather_code: int
    temperature_min: float
    temperature_max: float
    precipitation: float
    wind_speed_max: float
    source: str
    is_demo: bool = False


WEATHER_CODES = {
    0: "晴", 1: "大部晴朗", 2: "多云", 3: "阴",
    45: "雾", 48: "冻雾", 51: "轻毛毛雨", 53: "毛毛雨", 55: "强毛毛雨",
    56: "轻冻毛毛雨", 57: "强冻毛毛雨", 61: "小雨", 63: "中雨", 65: "大雨",
    66: "轻冻雨", 67: "强冻雨", 71: "小雪", 73: "中雪", 75: "大雪",
    77: "雪粒", 80: "小阵雨", 81: "中阵雨", 82: "强阵雨",
    85: "小阵雪", 86: "强阵雪", 95: "雷雨", 96: "雷雨伴小冰雹", 99: "雷雨伴大冰雹",
}


def weather_description(code: int) -> str:
    return WEATHER_CODES.get(code, f"未知天气（代码 {code}）")
