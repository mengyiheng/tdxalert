"""tdxalert.notify — 推送渠道（可插拔，纯标准库实现）。"""

from __future__ import annotations

import json
import urllib.parse
import urllib.request
from typing import Any, Dict, Protocol


class Notifier(Protocol):
    def send(self, text: str) -> None: ...


class ConsoleNotifier:
    """本地控制台输出（默认兜底渠道）。"""

    def send(self, text: str) -> None:
        print(f"[tdxalert] {text}")


class ServerChanNotifier:
    """Server酱·Turbo 版：https://sct.ftqq.com/ 微信服务号消息。"""

    def __init__(self, key: str):
        self.key = key

    def send(self, text: str) -> None:
        data = urllib.parse.urlencode({"title": text[:32], "desp": text}).encode()
        urllib.request.urlopen(f"https://sctapi.ftqq.com/{self.key}.send",
                               data=data, timeout=10)


class PushPlusNotifier:
    """PushPlus：https://www.pushplus.plus/ 微信公众号消息。"""

    def __init__(self, token: str):
        self.token = token

    def send(self, text: str) -> None:
        body = json.dumps({"token": self.token, "title": text[:64],
                           "content": text, "template": "txt"}).encode()
        req = urllib.request.Request("https://www.pushplus.plus/send", data=body,
                                     headers={"Content-Type": "application/json"})
        urllib.request.urlopen(req, timeout=10)


class WebhookNotifier:
    """通用 webhook（钉钉/企微机器人等 POST JSON 接口）。"""

    def __init__(self, url: str):
        self.url = url

    def send(self, text: str) -> None:
        body = json.dumps({"msgtype": "text", "text": {"content": text}}).encode()
        req = urllib.request.Request(self.url, data=body,
                                     headers={"Content-Type": "application/json"})
        urllib.request.urlopen(req, timeout=10)


_BUILDERS = {
    "console": lambda cfg: ConsoleNotifier(),
    "serverchan": lambda cfg: ServerChanNotifier(cfg["key"]),
    "pushplus": lambda cfg: PushPlusNotifier(cfg["token"]),
    "webhook": lambda cfg: WebhookNotifier(cfg["url"]),
}


def build_notifiers(cfg: Dict[str, Any]) -> Dict[str, Notifier]:
    out: Dict[str, Notifier] = {}
    if not cfg:
        out["console"] = ConsoleNotifier()
        return out
    for name, c in cfg.items():
        if name not in _BUILDERS:
            raise ValueError(f"未知推送渠道: {name}（支持 {list(_BUILDERS)}）")
        out[name] = _BUILDERS[name](c if isinstance(c, dict) else {"key": c})
    return out
