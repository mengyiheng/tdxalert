from datetime import datetime

import pytest

from tdxalert import AlertEngine, parse
from tdxalert.notify import ConsoleNotifier


def _engine(rules, sent):
    e = AlertEngine(rules, {})
    e.notifiers = {"console": ConsoleNotifier()}
    e.sent = sent
    return e


def test_price_threshold_and_cooldown():
    cfg = [{"type": "price_above", "code": "600519", "value": 1500, "cooldown": 300}]
    e = _engine([parse(c) for c in cfg], [])
    q = {"600519": {"price": 1501, "name": "贵州茅台"}}
    assert len(e.feed(q)) == 1
    assert len(e.feed(q)) == 0          # 冷却期内不重复


def test_pct_and_vol_spike():
    cfg = [
        {"type": "pct_below", "code": "*", "value": -2},
        {"type": "vol_spike", "code": "000001", "window": 4, "ratio": 3},
    ]
    e = _engine([parse(c) for c in cfg], [])
    base = {"000001": {"price": 10, "pct": -3, "vol": 100}}
    assert len(e.feed(base)) == 1                       # 跌幅触发
    for _ in range(3):                                  # 平量若干根
        e.feed({"000001": {"price": 10, "pct": 0, "vol": 100}})
    alerts = e.feed({"000001": {"price": 10, "pct": 0, "vol": 500}})
    assert any("成交量" in a for a in alerts)           # 5 倍放量触发


def test_change_dir_resets_baseline():
    e = _engine([parse({"type": "change_dir", "code": "600519", "value": 10, "cooldown": 0})], [])
    e.feed({"600519": {"price": 9}})
    assert len(e.feed({"600519": {"price": 11}})) == 1   # 上穿
    assert len(e.feed({"600519": {"price": 11}})) == 0   # 不在同一方向重复
    assert len(e.feed({"600519": {"price": 9}})) == 1    # 回落再次下穿


def test_wildcard_and_name_in_message():
    e = _engine([parse({"type": "price_below", "code": "*", "value": 5})], [])
    alerts = e.feed({"000001": {"price": 4.9, "name": "平安银行"}})
    assert alerts and "平安银行" in alerts[0]


def test_config_load():
    cfg = {
        "notifiers": {"console": {}},
        "rules": [{"type": "price_above", "code": "600519", "value": 1}],
    }
    e = AlertEngine.from_config(cfg)
    assert len(e.rules) == 1 and "console" in e.notifiers


def test_unknown_rule_field_rejected():
    with pytest.raises(ValueError):
        parse({"type": "price_above", "code": "600519", "value": 1, "foo": 2})
