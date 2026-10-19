"""tdxalert.engine — 预警引擎：吃快照，吐告警。

数据源无关：任何能产出 ``{code: {"price": float, "pct": float, "vol": float,
"name": str}}`` 快照的代码都能接入::

    engine = AlertEngine.from_config(cfg)
    for frame in your_snapshot_loop():      # 你的 REA 快照
        for msg in engine.feed(frame):
            ...                             # 已推送到配置的渠道
"""

from __future__ import annotations

from typing import Any, Dict, List

from .notify import build_notifiers
from .rules import Rule, evaluate, parse


class AlertEngine:
    def __init__(self, rules: List[Rule], notifiers: Dict[str, Any] | None = None):
        self.rules = rules
        self.notifiers = build_notifiers(notifiers or {})
        self.sent: List[str] = []

    @classmethod
    def from_config(cls, cfg: Dict[str, Any]) -> "AlertEngine":
        rules = [parse(c) for c in cfg.get("rules", [])]
        return cls(rules, cfg.get("notifiers", {}))

    def feed(self, quotes: Dict[str, Dict[str, Any]]) -> List[str]:
        """处理一帧全市场快照，返回触发的告警文本（同时推送渠道）。"""
        alerts: List[str] = []
        for rule in self.rules:
            for code, q in quotes.items():
                msg = evaluate(rule, code, q)
                if msg:
                    name = q.get("name", "")
                    alerts.append(f"{name} {msg}" if name else msg)
        if alerts:
            for text in alerts:
                self.sent.append(text)
                for n in self.notifiers.values():
                    n.send(text)
        return alerts
