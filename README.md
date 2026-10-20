# 第四讲课后作业：PyQt 日期天气查询

Python 3.10+ / PyQt6 中文桌面应用，选择城市及日期后展示每日天气、最低/最高温、降水总量、最大风速。默认查询真实网络服务，也可手动启用明确标注的离线演示模式。

公开仓库：[第四讲课后作业：PyQt 日期天气查询](https://github.com/SJTU-software-engineering/Lecture04-Homework-PyQtWeatherApp)。

## 安装与运行（Windows PowerShell）

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe main.py
```

如果已有 `.venv`，可跳过创建步骤。在线模式需联网，无需 API 密钥。选择北京、上海等八座预设城市，选择日期，点击“查询天气”。结果中的温度单位为 °C，降水为 mm，最大风速为 km/h。历史数据为再分析/模型结果，并非逐站实测；未来数据为预报，并非已发生天气。

依赖固定为 PyQt6 6.8.1 与 Qt6 6.8.2：本机 Anaconda Python 3.13.9 环境中，PyQt6 6.11 出现 QtCore DLL 加载失败，测试工程师确认上述组合可以正常加载并通过测试。固定版本用于复现本次验证环境；`requirements-dev.txt` 继续引用相同运行依赖。

## 日期范围与错误处理

- 今天以中国时区 UTC+8 计算。
- 支持从 1940-01-01 到今天后第 15 天（含边界），即未来预报窗口为含今天的 16 天。
- 92 天以内历史日期使用 Forecast API；更早日期使用 Historical Weather API。
- 日期过早或过晚会显示明确解释。界面允许输入超范围日期以展示校验。
- 单次网络读写超时为 15 秒，并非整次请求的总截止时间；总请求耗时及关闭窗口的等待时间可能更长。网络失败、接口异常、缺失或非有限数值会显示错误，可手动重试，不会偷偷使用模拟天气。
- 勾选“离线演示”可无网络展示稳定的模拟样例，结果和来源持续标注模拟性质。模拟模式也执行相同日期校验。
- 网络查询在 QThread 中运行，查询期间禁用输入避免结果错配。查询中关闭窗口会等待请求结束，避免销毁活动线程。

## 设计与文件

| 文件 | 职责 |
| --- | --- |
| `main.py` | 应用入口 |
| `weather_app/models.py` | 城市、天气结果与 WMO 天气码说明 |
| `weather_app/service.py` | 日期校验、接口路由、响应解析、离线模拟 |
| `weather_app/ui.py` | PyQt6 界面和异步查询线程 |
| `requirements.txt` | 运行依赖 |
| `requirements-dev.txt` | 运行及测试依赖 |

服务层不依赖 Qt，可注入日期提供器与 JSON 读取器进行稳定、独立于网络的测试。界面也可注入服务对象。模块使用标准库 urllib 访问 HTTPS，设置超时与 1 MB 响应上限；仅展示请求日期的完整数据。

## 测试运行

测试由 TestEngineer Agent 独立编写，加入测试文件后运行：

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m pytest -v
```

建议覆盖日期边界、历史/预报路由、缺测与异常数据、网络错误、模拟标识和界面异步行为。真实联网查询属于补充集成检查，不应让自动化测试依赖外部网络。

## 官方数据来源与说明

- [Open-Meteo Forecast API](https://open-meteo.com/en/docs)：最多 16 天预报、最多 92 天近期历史、每日变量及 WMO 天气码。
- [Open-Meteo Historical Weather API](https://open-meteo.com/en/docs/historical-weather-api)：1940 年起的历史再分析。
- [Open-Meteo](https://open-meteo.com/)：天气数据提供方，本项目保留数据归属说明。

本课程演示采用公开免费接口；实际可用数据范围与可用性受天气服务影响，缺测时会提示用户。
