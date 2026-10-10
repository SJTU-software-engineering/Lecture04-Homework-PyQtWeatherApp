# TestEngineer 完整测试报告

测试日期：2026-10-10（Asia/Shanghai）  
项目：PyQt 日期天气查询  
角色：TestEngineer；独立读取业务源码、编写测试、执行验证。业务源码和依赖配置由 CodeWriter 修改。

## 最终结论

交付状态的离线自动化测试 **89 / 89 通过，通过率 100%**，失败 0、错误 0、跳过 0。包含 80 个服务/模型用例和 9 个真实 PyQt 窗口及 QThread 集成用例。最终 pytest 终端报告耗时 **0.75 秒**。全部离线测试采用受控输入，不依赖真实天气接口。

另行执行两项真实联网 smoke：北京 2026-10-10 天气预报、北京 2020-01-01 历史再分析，**2 / 2 通过**。这两项不计入上述 89 个测试或离线通过率。

本轮发现并完成修复一个运行环境兼容缺陷（B1）；没有发现尚未修复的业务 bug。在线检查只证明本次请求成功，不代表服务始终可用或模型天气精度。

## 环境

| 项目 | 实际环境 |
| --- | --- |
| 操作系统 | Windows，64 位 |
| workspace | `E:\Code\sofwar_engineing\PyQtWeatherApp` |
| 解释器 | `.venv\Scripts\python.exe` |
| Python | 3.13.9，Anaconda 构建，MSC v.1929 |
| pytest | 9.1.1 |
| PyQt6 / Qt | 6.8.1 / 6.8.2 |
| PyQt6-sip | 13.13.0 |
| Qt 平台 | `offscreen`（由 tests/conftest.py 在 Qt 导入前设置） |
| 业务“今天” | 单元测试固定 2026-10-10；联网 smoke 使用实际 UTC+8 日期 |

## 测试代码与证据

| 文件 | 用途 |
| --- | --- |
| `tests/conftest.py` | Qt offscreen 配置、会话级 QApplication |
| `tests/test_service.py` | 80 个业务、模型和网络读取用例 |
| `tests/test_ui.py` | 9 个实际窗口、信号和工作线程集成用例 |
| `tests/smoke_online.py` | 单独执行的真实联网 smoke，不由 pytest 收集 |
| `reports/pytest_output.txt` | 最终逐项用例清单、PASS 状态、汇总和实际终端输出 |
| `reports/junit.xml` | 最终 JUnit XML：89 tests、0 failures、0 errors、0 skipped |
| `reports/dependency_install.txt` | 按最终 requirements-dev.txt 安装/依赖检查输出 |
| `reports/online_smoke.json` | 两次真实接口调用的完整结果（UTF-8） |
| `reports/online_smoke_output.txt` | 联网 smoke 终端输出；Windows 输出编码可能影响中文显示，JSON 文件保留正确中文 |

逐个参数化用例的名称及结果见 `pytest_output.txt` 和 `junit.xml`，不是仅依据收集数推断通过。

## 实际执行命令

以下命令从项目根目录以 PowerShell 执行。测试及安装命令均返回 exit code 0。

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt 2>&1 | Tee-Object -FilePath reports/dependency_install.txt
.\.venv\Scripts\python.exe -m pytest -v --junitxml=reports/junit.xml 2>&1 | Tee-Object -FilePath reports/pytest_output.txt
.\.venv\Scripts\python.exe -m tests.smoke_online 2>&1 | Tee-Object -FilePath reports/online_smoke_output.txt
```

最终安装验证运行于已经修复的现有 `.venv`，确认 requirements 可以解析且版本吻合；本轮没有删除环境并重新创建一个全新虚拟环境，因此不声称完成全新机器安装测试。

## 覆盖范围与结果

| 领域 | 用例/断言内容 | 结果 |
| --- | --- | --- |
| 日期边界 | 1940-01-01、过去 92 天、今天、今天+15 天有效；1940 前一天、今天+16 天在真实/模拟模式均拒绝，且不访问网络 | 通过 |
| 中国时区 | china_today 显式调用 UTC+8，模拟跨午夜结果得到中国日期 | 通过 |
| 路由与参数 | 过去 93 天 Archive；过去 92 天/昨天 Forecast 近期历史；今天/+15 天 Forecast 预报；经纬度、相同开始结束日期、daily 字段、时区和单位 | 通过 |
| 完整数据 | 多日期数组定位所选日期；结果字段、来源保留；0 降水/风速、负温度有效 | 通过 |
| 数据质量 | 5 个字段分别对 null、布尔、字符串、NaN、正/负 Infinity 拒绝；空/错误结构、服务 error、无选定日期、缺字段、长短数组、非 list、非整数天气码、倒置温度、负降水/风速 | 通过 |
| 天气描述 | 晴、小雨、雷雨和未知代码可读回退 | 通过 |
| 网络读取 | 请求带 User-Agent、timeout=15、读取上限 1,000,001 bytes；1,000,000 bytes JSON 有效、1,000,001 拒绝；非法 UTF-8、非法 JSON、非 object 拒绝；HTTP 503、URLError、TimeoutError、OSError 转可展示错误 | 通过 |
| 模拟模式 | 确定性结果、完全不调用 reader、模拟与非真实来源标签；网络失败不自动转模拟 | 通过 |
| UI 成功 | 实际 QApplication/窗口运行，选城市及日期传到服务；服务线程 id 与 GUI 主线程不同；真实 Qt 信号完成更新；天气/温度/降水/风速/来源显示准确 | 通过 |
| UI 错误恢复 | 业务错误与意外异常均清空旧数据；意外异常不暴露内部细节；控件恢复后可再次成功查询 | 通过 |
| 防重复与响应 | 阻塞假服务期间处理 Qt 事件；全部输入禁用；直接再次 start_query 与点击按钮均不创建第二线程；结束后控件恢复 | 通过 |
| UI 模拟及日期错误 | 使用实际 WeatherService 演示数据，界面状态及来源包含模拟警示；不支持日期可见错误并恢复控件 | 通过 |
| 活动线程关闭 | 受控活动线程执行期间 close 被拒绝、窗口保持可见并提示等待；释放服务后成功与失败两种分支均最终隐藏窗口、清理 worker，未发生活动线程销毁崩溃 | 通过 |

GUI 用例通过 QApplication、窗口显示、事件循环和真实 QThread 运行验证功能。未进行人工屏幕视觉检查、截图布局审查、不同 DPI/缩放或原生 Windows 平台插件视觉验证；不得把 offscreen 功能通过描述成视觉验收通过。

## Bug 清单与修复迭代

| 编号 | 类型/严重性 | 复现步骤 | 实际结果 / 期望结果 | 修复及复测 |
| --- | --- | --- | --- | --- |
| B1 | 当前环境启动阻断，高 | 初始 requirements 为 `PyQt6>=6.8,<7`，安装选择 PyQt6 6.11.0 / Qt 6.11.2；在现有 Anaconda Python 3.13.9 `.venv` 执行 `python -c "from PyQt6.QtCore import QT_VERSION_STR"` | 实际 ImportError: DLL load failed while importing QtCore（找不到指定的程序）；期望可导入并启动程序 | TestEngineer 向主控报告后将环境调整为 PyQt6 6.8.1 / Qt 6.8.2，导入成功；主控委派 CodeWriter 将 requirements 固定为上述版本并更新 README。最终 pip 依赖检查成功，89/89 回归通过。 |

B1 的精确底层 DLL 原因未进行二进制调试，不将“某一特定 DLL 冲突”当作已证明根因。记录的是可复现的版本/环境组合及已验证的解决办法。

迭代顺序：首次运行发现导入阻断 → 上报主控 → 验证兼容版本 → 首次 89/89 通过（3.87 秒）→ CodeWriter 固定依赖并补文档 → 按最终依赖配置安装验证 → 最终 89/89 通过（0.75 秒）。当前证据文件对应最终回归；初测耗时仅为工作过程记录。

## 补充在线检查

| 用例 | 真实接口结果 | 状态 |
| --- | --- | --- |
| 北京 2026-10-10 | Forecast；阴；15.5 ～ 26.5 °C；降水 0.0 mm；最大风速 7.9 km/h；is_demo=false | PASS |
| 北京 2020-01-01 | Archive；晴；-10.7 ～ -0.7 °C；降水 0.0 mm；最大风速 7.9 km/h；is_demo=false | PASS |

未穷举全部 8 个城市、全部可查询历史日、最远未来日的实际接口完整性；日期上界及缺测处理由离线测试覆盖。气象数值为接口模型结果，测试未对照气象实测验证其真实性/准确性。

## 已知限制

- 网络 socket 单次阻塞超时为 15 秒；整次请求无固定总截止时间。关闭窗口会等待工作线程结束。CodeReviewer 指出的低风险提示文案已由 CodeWriter 修改，现有设计限制仍保留。
- 响应体限制 1 MB，服务错误不自动回退模拟；联网失败时用户需手动重试或勾选演示。
- 本次离线测试不模拟实际操作系统 socket hang/逐字节慢速响应，只验证可控异常与线程生命周期；不声称验证所有网络故障情形。
- 通过的用例代表已覆盖行为，本轮没有执行覆盖率测量、长时压力测试、跨平台或全新机器安装测试。
