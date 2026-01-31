import urllib.parse
import logging_config
import websocket
import urllib
import html
class CraftyWSAPI():
    def __init__(self,server_url:str,token:str,server_uuid:str) -> None:
        self.URL = urllib.parse.urlparse(server_url)
        self.WSURL = f"wss://{self.URL.netloc}/ws?page=/panel/server_detail&page_query_params={html.escape({"id":server_uuid})}&subpage=term"
        self.WSclient =  websocket.WebSocketApp(
        self.WSURL,
        on_open=self.on_open,
        on_message=self.on_message,
        on_error=self.on_error,
        on_close=self.on_close,
        cookie=f"token={token}",
    )
        
    def on_message(self,ws,message):
        pass
    def on_error(self,ws, error):
        print(f"[ERROR] {error}", file=sys.stderr)

    def on_close(self,ws, code, msg):
        if code == 1011:
            print("[AUTH FAILED] Check your API key", file=sys.stderr)
        else:
            print(f"[CLOSED] code={code}", file=sys.stderr)


    def on_open(self,ws):
        print("[CONNECTED] Streaming server logs (Ctrl+C to quit)", file=sys.stderr)
        print("-" * 60, file=sys.stderr)