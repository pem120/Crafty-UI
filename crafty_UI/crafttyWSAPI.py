import json
import urllib.parse
from crafty_client import crafty4
from .logging_config import craftyWSAPI_logger
import websocket
import html
import ssl
import re


class CraftyWSAPI:
    def __init__(self, crafty: crafty4.Crafty4, server_uuid: str) -> None:
        self.URL = urllib.parse.urlparse(crafty.url)
        self.WSURL = f"wss://{self.URL.netloc}/ws?page=/panel/server_detail&page_query_params={urllib.parse.urlencode({'id':server_uuid})}&subpage=term"
        self.WSclient = websocket.WebSocketApp(
            self.WSURL,
            on_open=self.on_open,
            on_message=self.on_message,
            on_error=self.on_error,
            on_close=self.on_close,
            cookie=f"token={crafty.token}",
        )
        self.logger = craftyWSAPI_logger
        self.ssl_ctx = ssl.create_default_context()
        self.ssl_ctx.check_hostname = False
        self.ssl_ctx.verify_mode = ssl.CERT_NONE
        self.logs = []
        self.reexp = re.compile("<([^>]+)>")

    def on_message(self, ws, message):
        self.logger.debug(message)
        parsed = json.loads(str(message))
        data = parsed["data"]
        match parsed["event"]:
            case "update_server_details":
                self.stats = data
            case "vterm_new_line":
                self.logs.append(re.sub(self.reexp, "", html.unescape(data["line"])))
            case "notification":
                self.notification = data
            case _:
                self.logger.error(
                    f"Unknown messgae type '{parsed["event"]}'.Not parsing"
                )

    def on_error(self, ws, error):
        self.logger.error(error)

    def on_close(self, ws, code, msg):
        if code == 1011:
            self.logger.error(f"AUTH FAIl")
        else:
            self.logger.info(f"Closed {code}")

    def on_open(self, ws):
        self.logger.debug("Started Logging")

    def run(self):
        self.WSclient.run_forever(
            sslopt={"context": self.ssl_ctx},
            ping_interval=30,
            ping_timeout=10,
        )

    def get_logs(self):
        return self.logs
