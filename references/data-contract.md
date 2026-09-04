# 内部数据约定

这份 JSON 由执行 skill 的 agent 从用户原文及核验结果生成，不要求用户提供。字段可扩展，但运行附带里程脚本时遵守以下最小结构：

```json
{
  "title": "旅行路线",
  "days": [
    {
      "day": 1,
      "date": "9/24",
      "requested_stops": ["成都", "广元"],
      "lodging": "服务区（未指定）",
      "route_status": "complete",
      "unmodelled": [],
      "segments": [
        {
          "distance_m": 293700,
          "geometry": {"type": "LineString", "coordinates": [[104.06,30.67],[105.84,32.44]]},
          "source": "测试示意数据，不是真实公路轨迹"
        }
      ]
    }
  ]
}
```

上例的两点线只展示 schema，不能用于冒充真实道路。实际输入使用路由服务返回的完整坐标数组和 distance。

- `day` 必须为从 1 开始的连续整数；日期可省略。
- `route_status` 为 `complete`、`partial` 或 `unavailable`。
- `segments` 是当天按真实行驶顺序排列的已建模路段，`distance_m` 是路由距离（非直线距离）。有往返时重复列出实际行驶段，不能去重。
- `partial` 必须提供非空 `unmodelled` 说明，例如“景区入口至遗址往返未建模”；缺口两侧保留独立 segment，不能把几何数组直接连成假路。
- `unavailable` 的 segments 为空，也必须说明 unmodelled；此时不生成当天终点里程标签，因为未知终点路由坐标。
- 几何坐标为 `[longitude, latitude]` WGS84，distance 以米计。记录每段请求 URL/参数、时间和来源等附加字段；计算脚本不代替真实性及路况审查。
- 如缺口位于当天末尾，可追加 `endpoint_modelled: false`，以免把最后已知点标成住宿终点。

调用：

```text
python <skill>/scripts/route_metrics.py <project>/itinerary.json --out <project>/derived
python <skill>/scripts/route_metrics.py --self-test
```

脚本使用标准库。先把每天所有已建模路段米数相加，转换 km 并按 Decimal ROUND_HALF_UP 保留一位；累计加的是展示的每日一位值，保证逐项可复算。输出总数可能与直接对全部原始米数一次四舍五入不同，必须保留口径说明。存在任何缺口则 scope 为 `modelled_roads_only`，以“已计算路网累计”展示；未知天显示未知，不把它标成 0 km 已完成。

里程点使用真实 route 起终点；分开的返程终点不要用地点名称合并。若用户要求每500 km等中途里程牌，需沿线段按 geodesic 长度比例定位，并注明按路由距离分配的近似桩号；这不是当前脚本的默认输出。
