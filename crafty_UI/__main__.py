import dearpygui.dearpygui as dpg
import crafty_client
import toml
import urllib3
import colorlog

from crafty_UI.logging_config import logger
from crafty_UI.server import Server
from crafty_UI.main_window import MainWindow

# Disable urllib3 warnings
urllib3.disable_warnings()

# Initialize the crafty client
crafty = None
try:
    conf = toml.load("server.toml")
    server_url = conf["server"]["url"]
    server_token = conf["server"]["token"]
    crafty = crafty_client.Crafty4(server_url, server_token)
except Exception as e:
    print(f"Failed to parse server.toml: {e}")
    raise SystemExit


logger.log(colorlog.DEBUG, "Hello")

global win
win = None


def ExitCallback():
    logger.info("Shutting down")
    if win:
        win.running = False
    dpg.stop_dearpygui()
    raise SystemExit


def Run():
    try:
        dpg.create_context()
        dpg.create_viewport(title="Crafty UI")
        dpg.setup_dearpygui()

        win = MainWindow(crafty)
        win.SetupWindow()

        dpg.set_viewport_resize_callback(win.ResizeCallback)
        dpg.set_exit_callback(ExitCallback)
        dpg.show_viewport()
        dpg.show_item_registry()
        dpg.show_debug()
        dpg.start_dearpygui()

        ExitCallback()
    except Exception as e:
        logger.exception("Failed to start")
        exit(-1)


if __name__ == "__main__":
    Run()
