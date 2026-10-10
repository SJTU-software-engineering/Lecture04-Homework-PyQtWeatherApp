import io
import json
from datetime import date, timedelta
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, urlparse

import pytest

from weather_app.models import CITIES, weather_description
from weather_app import service

TODAY = date(2026, 10, 10)
CITY = CITIES[0]


def payload(day=TODAY):
    return {"daily": {"time": [day.isoformat()], "weather_code": [61],
                      "temperature_2m_min": [12], "temperature_2m_max": [22.5],
                      "precipitation_sum": [1.2], "wind_speed_10m_max": [15]}}


@pytest.mark.parametrize("day", [service.MIN_DATE, TODAY - timedelta(days=92), TODAY, TODAY + timedelta(days=15)])
def test_valid_date_boundaries(day):
    service.validate_date(day, TODAY)


def test_china_today_requests_utc_plus_eight(monkeypatch):
    from datetime import datetime
    class Clock:
        @staticmethod
        def now(tz):
            assert tz.utcoffset(None) == timedelta(hours=8)
            return datetime(2026, 10, 11, 0, 1, tzinfo=tz)
    monkeypatch.setattr(service, "datetime", Clock)
    assert service.china_today() == date(2026, 10, 11)


@pytest.mark.parametrize("day", [service.MIN_DATE - timedelta(days=1), TODAY + timedelta(days=16)])
@pytest.mark.parametrize("demo", [False, True])
def test_invalid_dates_never_access_network(day, demo):
    def forbidden(_):
        pytest.fail("invalid date accessed network")
    with pytest.raises(service.WeatherError):
        service.WeatherService(forbidden, lambda: TODAY).query(CITY, day, demo)


@pytest.mark.parametrize("offset,endpoint,label", [(-93, service.ARCHIVE_URL, "历史再分析"),
    (-92, service.FORECAST_URL, "近期历史"), (-1, service.FORECAST_URL, "近期历史"),
    (0, service.FORECAST_URL, "天气预报"), (15, service.FORECAST_URL, "天气预报")])
def test_route_and_query_parameters(offset, endpoint, label):
    day = TODAY + timedelta(days=offset)
    urls = []
    def reader(url):
        urls.append(url)
        return payload(day)
    result = service.WeatherService(reader, lambda: TODAY).query(CITY, day)
    parsed = urlparse(urls[0])
    assert parsed.scheme + "://" + parsed.netloc + parsed.path == endpoint
    params = parse_qs(parsed.query)
    assert params["start_date"] == params["end_date"] == [day.isoformat()]
    assert params["latitude"] == [str(CITY.latitude)]
    assert params["longitude"] == [str(CITY.longitude)]
    assert params["timezone"] == ["Asia/Shanghai"]
    assert params["daily"] == [",".join(service.DAILY_FIELDS)]
    assert params["temperature_unit"] == ["celsius"]
    assert params["wind_speed_unit"] == ["kmh"]
    assert params["precipitation_unit"] == ["mm"]
    assert label in result.source
    assert result.day == day and not result.is_demo


def test_complete_payload_uses_selected_date():
    data = payload()
    data["daily"]["time"].insert(0, "2026-10-09")
    for key in service.DAILY_FIELDS:
        data["daily"][key].insert(0, 0)
    result = service.parse_weather(data, CITY, TODAY, "test source")
    assert (result.weather_code, result.temperature_min, result.temperature_max,
            result.precipitation, result.wind_speed_max) == (61, 12.0, 22.5, 1.2, 15.0)
    assert result.city == CITY and result.source == "test source"


@pytest.mark.parametrize("key", service.DAILY_FIELDS)
@pytest.mark.parametrize("bad", [None, True, "12", float("nan"), float("inf"), float("-inf")])
def test_missing_invalid_nonfinite_values(key, bad):
    data = payload()
    data["daily"][key] = [bad]
    with pytest.raises(service.WeatherError, match="暂无完整"):
        service.parse_weather(data, CITY, TODAY, "test")


@pytest.mark.parametrize("bad", [{}, {"daily": None}, {"daily": {}},
    {"daily": {"time": "2026-10-10"}}, {"error": True}, [], None])
def test_malformed_payload(bad):
    with pytest.raises(service.WeatherError):
        service.parse_weather(bad, CITY, TODAY, "test")


@pytest.mark.parametrize("mutation", ["missing_date", "missing_field", "short_series", "long_series",
    "non_list", "fractional_code", "reversed_temperatures", "negative_rain", "negative_wind"])
def test_semantically_invalid_payload(mutation):
    data = payload()
    daily = data["daily"]
    if mutation == "missing_date": daily["time"] = ["2026-10-09"]
    elif mutation == "missing_field": del daily["weather_code"]
    elif mutation == "short_series": daily["weather_code"] = []
    elif mutation == "long_series": daily["weather_code"] = [61, 61]
    elif mutation == "non_list": daily["weather_code"] = (61,)
    elif mutation == "fractional_code": daily["weather_code"] = [61.5]
    elif mutation == "reversed_temperatures": daily["temperature_2m_min"] = [30]
    elif mutation == "negative_rain": daily["precipitation_sum"] = [-1]
    elif mutation == "negative_wind": daily["wind_speed_10m_max"] = [-1]
    with pytest.raises(service.WeatherError):
        service.parse_weather(data, CITY, TODAY, "test")


def test_zero_values_and_negative_temperature_valid():
    data = payload()
    data["daily"].update(weather_code=[0], temperature_2m_min=[-10], temperature_2m_max=[-1],
                         precipitation_sum=[0], wind_speed_10m_max=[0])
    result = service.parse_weather(data, CITY, TODAY, "test")
    assert result.precipitation == result.wind_speed_max == 0
    assert result.temperature_min == -10


def test_demo_is_deterministic_and_does_not_access_network():
    def forbidden(_): pytest.fail("demo accessed network")
    instance = service.WeatherService(forbidden, lambda: TODAY)
    first = instance.query(CITY, TODAY, True)
    assert first == instance.query(CITY, TODAY, True)
    assert first.is_demo and "模拟" in first.source and "非真实" in first.source
    assert first.temperature_min <= first.temperature_max


def test_network_error_does_not_fallback_to_demo():
    def failure(_): raise service.WeatherError("network failed")
    with pytest.raises(service.WeatherError, match="network failed"):
        service.WeatherService(failure, lambda: TODAY).query(CITY, TODAY)


@pytest.mark.parametrize("code,description", [(0, "晴"), (61, "小雨"), (95, "雷雨"), (1234, "未知天气（代码 1234）")])
def test_weather_description(code, description):
    assert weather_description(code) == description


def install_response(monkeypatch, raw):
    observed = {}
    class Response(io.BytesIO):
        def read(self, size=-1):
            observed["read_size"] = size
            return super().read(size)
    def opener(request, timeout):
        observed["request"] = request
        observed["timeout"] = timeout
        return Response(raw)
    monkeypatch.setattr(service, "urlopen", opener)
    return observed


def test_read_json_valid_and_timeout_and_size_limit(monkeypatch):
    observed = install_response(monkeypatch, json.dumps(payload()).encode())
    assert service.read_json("https://example.invalid/weather") == payload()
    assert observed["timeout"] == 15 and observed["read_size"] == 1_000_001
    assert observed["request"].get_header("User-agent") == "PyQtWeatherApp/1.0"


@pytest.mark.parametrize("size,valid", [(1_000_000, True), (1_000_001, False)])
def test_response_byte_limit(monkeypatch, size, valid):
    install_response(monkeypatch, b"{}" + b" " * (size - 2))
    if valid: assert service.read_json("https://example.invalid") == {}
    else:
        with pytest.raises(service.WeatherError, match="响应过大"):
            service.read_json("https://example.invalid")


@pytest.mark.parametrize("raw", [b"not json", b"\xff", b"[]", b"null", b'"text"'])
def test_read_json_invalid_content(monkeypatch, raw):
    install_response(monkeypatch, raw)
    with pytest.raises(service.WeatherError): service.read_json("https://example.invalid")


@pytest.mark.parametrize("error,expected", [(HTTPError("url", 503, "unavailable", {}, None), "HTTP 503"),
    (URLError("offline"), "无法连接"), (TimeoutError(), "无法连接"), (OSError(), "无法连接")])
def test_read_json_network_exceptions(monkeypatch, error, expected):
    def opener(*args, **kwargs): raise error
    monkeypatch.setattr(service, "urlopen", opener)
    with pytest.raises(service.WeatherError, match=expected): service.read_json("https://example.invalid")
