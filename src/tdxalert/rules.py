"""tdxalert.rules — 基础预警规则集。

规则在每帧快照上求值，返回告警消息（str）或 None。

所有规则通用字段：
    code      证券代码，"*" 表示全市场
    cooldown  同一规则对同一代码的告警冷却秒数（默认 300）

内置类型：
    price_above / price_below    价格上破 / 下破阈值
    pct_above / pct_below        涨跌幅超阈（%，正涨负跌）
    vol_spike                    成交量较滚动均值放大 ratio 倍
    change_dir                   方向反转（price 上穿/下穿 ref_price）
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional


@dataclass
class Rule:
    type: str
    code: str = "*"
    value: float = 0.0
    window: int = 20          # vol_spike 滚动窗口
    ratio: float = 3.0        # vol_spike 放大倍数
    cooldown: int = 300
    name: str = ""

    # 运行时状态
    last_fired: Dict[str, str] = field(default_factory=dict)   # code -> ISO 时间
    vol_hist: Dict[str, List[float]] = field(default_factory=dict)

    def matches(self, code: str) -> bool:
        return self.code in ("*", code)

    def _cooled(self, code: str) -> bool:
        t = self.last_fired.get(code)
        if not t:
            return True
        return (datetime.now() - datetime.fromisoformat(t)).total_seconds() >= self.cooldown

    def _fire(self, code: str) -> None:
        self.last_fired[code] = datetime.now().isoformat(timespec="seconds")


def parse(cfg: Dict[str, Any]) -> Rule:
    known = {"type", "code", "value", "window", "ratio", "cooldown", "name"}
    extra = set(cfg) - known
    if extra:
        raise ValueError(f"规则含未知字段: {extra}（规则: {cfg}）")
    r = Rule(type=cfg["type"], **{k: v for k, v in cfg.items() if k not in ("type", "name")})
    r.name = cfg.get("name") or cfg["type"]
    return r


def evaluate(rule: Rule, code: str, q: Dict[str, Any]) -> Optional[str]:
    """对单只股票快照求值。q 至少含 price；pct/vol/amount 可选。"""
    if not rule.matches(code) or not rule._cooled(code):
        return None
    price = q.get("price")
    if price is None:
        return None
    msg: Optional[str] = None

    if rule.type == "price_above" and price > rule.value:
        msg = f"价格 {price} 上破 {rule.value}"
    elif rule.type == "price_below" and price < rule.value:
        msg = f"价格 {price} 下破 {rule.value}"
    elif rule.type == "pct_above" and (q.get("pct") or 0) > rule.value:
        msg = f"涨幅 {q['pct']}% > {rule.value}%"
    elif rule.type == "pct_below" and (q.get("pct") or 0) < rule.value:
        msg = f"跌幅 {q['pct']}% < {rule.value}%"
    elif rule.type == "change_dir":
        ref = rule.value
        hist = rule.vol_hist.setdefault(code, [])
        prev = hist[-1] if hist else None
        hist.append(price)
        if prev is not None:
            if prev <= ref < price:
                msg = f"价格上穿 {ref}（{prev} -> {price}）"
            elif prev >= ref > price:
                msg = f"价格下穿 {ref}（{prev} -> {price}）"
    elif rule.type == "vol_spike":
        vol = q.get("vol")
        if vol:
            h = rule.vol_hist.setdefault(code, [])
            h.append(vol)
            if len(h) > rule.window:
                h.pop(0)
            if len(h) >= max(3, rule.window // 2):
                avg = sum(h[:-1]) / len(h[:-1])
                if avg > 0 and vol >= avg * rule.ratio:
                    msg = f"成交量 {vol:.0f} 为前{len(h)-1}根均值 {avg:.0f} 的 {vol/avg:.1f} 倍"

    if msg:
        rule._fire(code)
        if rule.type == "change_dir":
            rule.vol_hist[code] = [price]      # 重置基准，避免同一方向重复触发
        return f"[{rule.name}] {code} {msg}（现价 {price}）"
    return None
