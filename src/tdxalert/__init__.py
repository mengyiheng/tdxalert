"""tdxalert — 盘中预警推送引擎（数据源无关）。

数据源可插拔：任何能产出 ``{code: {"price": .., "pct": .., "vol": ..}}``
快照帧的代码都能接入，包括你自己的全市场采集器、pytdx、或 tdxreplay 回放流。

    from tdxalert import AlertEngine

    engine = AlertEngine.from_config({
        "notifiers": {"serverchan": {"key": "SCTxxx"}},
        "rules": [
            {"type": "price_above", "code": "600519", "value": 1500},
            {"type": "vol_spike", "code": "*", "window": 20, "ratio": 3},
        ],
    })
    for frame in your_snapshot_loop():     # 你的 REA 全市场快照
        engine.feed(frame)                 # 触发即推送微信
"""

from .engine import AlertEngine
from .rules import Rule, evaluate, parse

__version__ = "0.1.0"
__all__ = ["AlertEngine", "Rule", "evaluate", "parse", "__version__"]
