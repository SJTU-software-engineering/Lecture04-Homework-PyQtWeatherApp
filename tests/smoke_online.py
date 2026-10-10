"""Optional real-network smoke; not part of pytest or the offline pass rate."""
import json
from dataclasses import asdict
from datetime import date
from pathlib import Path

from weather_app.models import CITIES
from weather_app.service import WeatherService, china_today


def main():
    service = WeatherService()
    results = []
    for label, day in (("forecast_today", china_today()),
                       ("archive_historical", date(2020, 1, 1))):
        try:
            result = service.query(CITIES[0], day)
            entry = {"case": label, "status": "PASS", "result": asdict(result)}
        except Exception as exc:
            entry = {"case": label, "status": "FAIL", "error": str(exc),
                     "exception": type(exc).__name__}
        results.append(entry)
        print(json.dumps(entry, ensure_ascii=False, default=str))
    output = Path("reports/online_smoke.json")
    output.parent.mkdir(exist_ok=True)
    output.write_text(json.dumps(results, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    return 0 if all(item["status"] == "PASS" for item in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
