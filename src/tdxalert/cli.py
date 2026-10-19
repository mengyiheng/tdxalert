"""tdxalert.cli — 命令行：读 JSONL 快照流，跑规则，推微信。

用法:
  tdxalert run --config alert.json --input quotes.jsonl     # 快照文件/管道
  your_snapshot_source | tdxalert run --config alert.jsonl  # 接你自己的采集器

快照帧格式（每行一个 JSON）::
  {"600519": {"price": 1501.2, "pct": 1.2, "vol": 3200, "name": "贵州茅台"}, ...}
"""

from __future__ import annotations

import argparse
import json
import sys
import time


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="tdxalert", description="盘中预警推送引擎")
    sub = p.add_subparsers(dest="cmd", required=True)
    run = sub.add_parser("run", help="消费 JSONL 快照流并推送告警")
    run.add_argument("--config", required=True, help="配置 JSON（规则 + 推送渠道）")
    run.add_argument("--input", default="-", help="JSONL 快照流文件，默认 stdin")
    run.add_argument("--interval", type=float, default=0.0,
                     help="每帧之间的模拟间隔秒数（回放测试用）")
    a = p.parse_args(argv)

    from .engine import AlertEngine

    cfg = json.loads(open(a.config, encoding="utf-8-sig").read())
    engine = AlertEngine.from_config(cfg)
    print(f"[tdxalert] 规则 {len(engine.rules)} 条，渠道: {list(engine.notifiers)}")

    stream = sys.stdin if a.input == "-" else open(a.input, encoding="utf-8")
    n = 0
    for line in stream:
        line = line.strip().lstrip("\ufeff")
        if not line:
            continue
        frame = json.loads(line)
        alerts = engine.feed(frame)
        for text in alerts:
            print(f"[触发] {text}")
        n += 1
        if a.interval:
            time.sleep(a.interval)
    print(f"[tdxalert] 处理 {n} 帧，触发 {len(engine.sent)} 条告警")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
