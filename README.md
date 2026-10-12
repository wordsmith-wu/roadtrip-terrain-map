# roadtrip-terrain-map

只需提供每天的行程，让支持 Skills 的 AI 编程助手制作真实公路路线与地形晕渲相结合的高清中文旅行地图。

这是一个 **AI 工作流 skill**，含制图规范、示例工程与里程工具，不是无需 AI 适配即可运行的通用地图应用。

## 使用

将本仓库作为 `roadtrip-terrain-map` 文件夹放入你的 Codex 个人 skills 目录（通常为 `~/.codex/skills/`），保持 `SKILL.md` 位于该文件夹根目录。不要覆盖已有安装中的个人修改。

然后向助手输入：

```text
$roadtrip-terrain-map
D1 成都到广元，宿服务区
D2 广元到瓜州，宿瓜州
D3 瓜州到艾丁湖，再到乌鲁木齐，宿乌市
```

用户不需要提供坐标、GeoJSON、Python 参数或 API 配置。助手负责解析、核验地点、准备路网与高程资料；仅在关键地名或路线有歧义时询问。

## 默认效果

- 真实公路路由几何，非随意弯曲的连线。
- 真实 DEM 的 2.5D 地形晕渲，坡度增强 5 倍；真实海拔色标不变。
- 默认分层显示 Natural Earth 海洋、湖泊与河流；海洋由现有国家陆地面求补集，无需额外海洋数据，并覆盖 DEM 海床以区别沿海平原。
- 暖纸色、大中文字体、每日行程与住宿。
- 起点 0 km，累计里程标在沿线每日终点，标签显示 `Dn · X km`（省略“累计”二字，数值仍为累计值）。
- 按需添加地点当天的静态彩色天气图标、日期与温度；检查图标完整性和整组标签避让，缺数据不编造。
- 涉及中国时标示底图所表示的国境线，并说明数据口径。
- 默认 9000×6600 PNG、SVG、轻量预览及可复算里程数据；可按行程调整尺寸。

## 内容

| 路径 | 用途 |
| --- | --- |
| [SKILL.md](SKILL.md) | 助手执行入口 |
| [references/workflow.md](references/workflow.md) | 路网、DEM、投影、版式及检查规范 |
| [references/data-contract.md](references/data-contract.md) | 助手生成的内部数据格式 |
| [references/example.md](references/example.md) | 新疆案例及适配说明 |
| [references/weather.md](references/weather.md) | 天气快照、彩色图标防裁切与标签避让 |
| [scripts/route_metrics.py](scripts/route_metrics.py) | 标准库里程计算与路线终点标记工具 |
| [assets/xinjiang-example](assets/xinjiang-example) | 已实际出图的案例源代码，不含数据缓存 |

## 验证与依赖

里程工具仅依赖 Python 标准库：

```sh
python scripts/route_metrics.py --self-test
```

实际制图需要 Python、Cartopy、Matplotlib、NumPy、SciPy、Pillow、Shapely 及可用的中文字体；助手应在独立工程环境准备依赖。获取新地理资料需要网络和适用的数据服务。案例脚本含地域、字体和14天布局的固定设置，必须按新行程适配，详见示例说明。

## 数据与限制

路网计算路径不是实测 GPS，不保证出行时道路开放。未确认的接入路段不伪造、不混入完整里程，输出明确说明排除项。2.5D 晕渲不是可旋转的三维模型；SVG 中的地形是嵌入位图。

底图示例采用 Natural Earth，其边界表达不是中国官方标准地图，不用于边界认定或导航。道路示例采用 OpenStreetMap/OSRM；高程示例采用 Mapzen Terrarium 数据。实际成果必须按所用数据源保留署名与许可说明，第三方数据、字体和运行环境不包含在本仓库中。

面向中国地图的输出遵循一个中国原则：台湾是中国的一部分，不将台湾呈现或归类为独立国家。正式出版或有审图要求时，应使用合规标准地图并履行适用程序。
