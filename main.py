from multiprocessing import set_forkserver_preload
from tkinter import Label
import dearpygui.dearpygui as dpg
import crafty_client
import toml
import urllib3
import scheduler
import colorlog


urllib3.disable_warnings()
try:
    conf = toml.load("server.toml")
    server_url = conf["server"]["url"]
    server_token = conf["server"]["token"]
    crafty = crafty_client.Crafty4(server_url, server_token)
except Exception as e:
    print(f"Failled to parse server.toml.{e}")

dpg.create_context()
dpg.create_viewport(title="Crafty UI")
dpg.setup_dearpygui()
handler = colorlog.StreamHandler()
formatter = colorlog.ColoredFormatter(
    "%(log_color)s%(levelname)-8s%(reset)s %(blue)s%(message)s",
    datefmt=None,
    reset=True,
    log_colors={
        "DEBUG": "cyan",
        "INFO": "green",
        "WARNING": "yellow",
        "ERROR": "red",
        "CRITICAL": "red,bg_white",
    },
    secondary_log_colors={},
    style="%",
)
handler.setFormatter(formatter)

logger = colorlog.getLogger("Main")
logger.addHandler(handler)
urllib_logger = colorlog.getLogger("urllib3")
urllib_logger.setLevel(colorlog.WARNING)
urllib_logger.addHandler(handler)


class Server:
    def __init__(self, crafty, server_uuid):
        try:
            self.stats = crafty.get_server_stats(server_uuid)
            self.logs = crafty.get_server_logs(server_uuid)
            self.crafty = crafty
            self.log_length = []

        except Exception as e:
            print("failed to get server stats,Retrying \n" + str(e))
            self.__init__(crafty, server_uuid)
        # Parse server data
        self.parsed = {
            "id": self.stats["server_id"]["server_id"],
            "name": self.stats["server_id"]["server_name"],
            "created_time": self.stats["created"],
            "running": self.stats["running"],
            "crashed": self.stats["crashed"],
            "size": self.stats["world_size"],
            "mem": self.stats["mem"],
            "cpu": self.stats["cpu"],
        }
        self.logger = colorlog.getLogger(self.parsed["name"])
        self.logger.addHandler(handler)
        self.logger.setLevel(colorlog.DEBUG)

    def start(self):
        try:
            crafty.start_server(self.parsed["id"])
        except Exception as e:
            self.logger.error(f"Failled to start the server", exc_info=True)

    def stop(self):
        try:
            crafty.stop_server(self.parsed["id"])
        except Exception as e:
            self.logger.exception("Failled to stop server")

    def command_callback(self, sender, app_data, user_data):
        try:
            crafty.run_command(self.parsed["id"], app_data)
        except Exception as e:
            self.logger.exception("Failled to execute command")

    def setup_window(self):

        self.window = dpg.window(
            label=self.parsed["name"],
            tag=self.parsed["id"],
            no_move=True,
            no_resize=True,
            show=True,
        )

        self.cpu_plot_x = [0]
        self.cpu_plot_y = [0]
        self.ram_plot_x = [0]
        self.ram_plot_y = [0]

        with self.window:
            self.tabs = dpg.tab_bar()
            with self.tabs:
                with dpg.tab(label="Terminal"):
                    # Create UI elements first

                    self.uuid = dpg.add_text(
                        default_value="UUID: ", label=self.parsed["id"], show_label=True
                    )
                    self.run_indicator = dpg.add_text(
                        default_value="Running: ",
                        label=self.parsed["running"],
                        show_label=True,
                    )
                    with dpg.child_window(
                        label="Terminalwin",
                        horizontal_scrollbar=True,
                        border=False,
                        autosize_x=True,
                        autosize_y=True,
                    ):

                        self.logs_term = dpg.add_listbox(
                            self.logs,
                            width=-1,
                            num_items=25,
                            tracked=True,
                        )
                    self.command_input = dpg.add_input_text(
                        label="command",
                        width=-1,
                        callback=self.command_callback,
                        on_enter=True,
                    )
                    self.window_pos = dpg.get_item_pos(self.parsed["id"])
                    self.button_group = None
                    with dpg.group(
                        horizontal=True,
                        tag=f"group_{self.parsed['id']}",
                    ):
                        dpg.add_button(label="start", callback=self.start)
                        dpg.add_button(label="stop", callback=self.stop)

                with dpg.tab(label="Graphs"):
                    self.plot_group = dpg.group(
                        horizontal=True,
                        tag=f"plot_{self.parsed['id']}",
                        width=-1,
                        height=-1,
                    )
                    with self.plot_group:
                        self.cpu_plot = dpg.plot(label="CPU Usage", width=-1)
                        self.ram_plot = dpg.plot(label="RAM Usage", width=-1)
                    with self.cpu_plot:
                        dpg.add_plot_axis(
                            dpg.mvXAxis,
                            label="Time",
                            tag=f"cpu_usage_x_{self.parsed['id']}",
                            auto_fit=True,
                        )
                        dpg.add_plot_axis(
                            dpg.mvYAxis,
                            label="y",
                            tag=f"cpu_usage_y_{self.parsed['id']}",
                            auto_fit=True,
                        )
                        dpg.add_line_series(
                            self.cpu_plot_x,
                            self.cpu_plot_y,
                            label="CPU Usage",
                            parent=f"cpu_usage_y_{self.parsed['id']}",
                            tag=f"cpu_line_{self.parsed['id']}",
                        )
                    with self.ram_plot:
                        dpg.add_plot_axis(
                            dpg.mvXAxis,
                            label="Time2",
                            tag=f"ram_usage_x_{self.parsed['id']}",
                            auto_fit=True,
                        )
                        dpg.add_plot_axis(
                            dpg.mvYAxis,
                            label="Usage",
                            tag=f"ram_usage_y_{self.parsed['id']}",
                            auto_fit=True,
                        )
                        dpg.add_line_series(
                            self.ram_plot_x,
                            self.ram_plot_y,
                            label="RAM Usage",
                            parent=f"ram_usage_y_{self.parsed['id']}",
                            tag=f"ram_line_{self.parsed['id']}",
                        )
                    dpg.fit_axis_data(f"ram_usage_y_{self.parsed['id']}")
                    dpg.fit_axis_data(f"ram_usage_x_{self.parsed['id']}")
                    dpg.fit_axis_data(f"cpu_usage_y_{self.parsed['id']}")
                    dpg.fit_axis_data(f"cpu_usage_x_{self.parsed['id']}")
                    self.button_pos = dpg.get_item_pos(f"group_{self.parsed['id']}")

    def resize_callback(self):
        self.viewport_width = dpg.get_viewport_client_width()
        self.viewport_height = dpg.get_viewport_client_height()
        self.window_width = dpg.get_item_width(self.parsed["id"])

        dpg.configure_item(
            self.parsed["id"],
            width=round(self.viewport_width * 3 / 4),
            height=self.viewport_height,
            pos=(
                round(self.window_pos[0] + self.viewport_width / 4),
                self.window_pos[1],
            ),
        )

        self.group_pos = dpg.get_item_pos(f"group_{self.parsed['id']}")
        self.group_width = dpg.get_item_width(f"group_{self.parsed['id']}")
        """
        dpg.configure_item(
            f"group_{self.parsed['id']}",
            pos=(
                round((self.window_width / 2) + self.group_width),
                self.viewport_height - 100,
            ),
        )"""

    def update_data(self):
        try:
            self.stats = crafty.get_server_stats(self.parsed["id"])
            self.logs = crafty.get_server_logs(self.parsed["id"])
            self.parsed = {
                "id": self.stats["server_id"]["server_id"],
                "name": self.stats["server_id"]["server_name"],
                "created_time": self.stats["created"],
                "running": self.stats["running"],
                "crashed": self.stats["crashed"],
                "size": self.stats["world_size"],
                "mem": self.stats["mem"],
                "cpu": self.stats["cpu"],
            }
            self.cpu_plot_x.append(self.cpu_plot_x[-1] + 0.5)
            self.cpu_plot_y.append(self.stats["cpu"] / 10)
            self.ram_plot_x.append(self.ram_plot_x[-1] + 0.5)

            if type(self.parsed["mem"]) == str:
                if self.parsed["mem"].endswith("GB"):
                    self.ram_plot_y.append(int(self.stats["mem"].strip("GB")))
                elif self.parsed["mem"].endswith("M"):
                    self.ram_plot_y.append(int(self.stats["mem"].strip("M")) / 1024)

            for log in self.logs:
                self.log_length.append(dpg.get_text_size(log)[0])
            print(max(self.log_length))

            dpg.configure_item(
                f"cpu_line_{self.parsed['id']}", x=self.cpu_plot_x, y=self.cpu_plot_y
            )
            dpg.configure_item(
                f"ram_line_{self.parsed['id']}", x=self.ram_plot_x, y=self.ram_plot_y
            )
            dpg.set_item_label(self.run_indicator, self.parsed["running"])
            dpg.configure_item(self.logs_term, items=self.logs)
            self.resize_callback()

        except Exception as e:
            self.logger.exception("Failled to retrive server statistics")


class Main_Window:
    def __init__(self, crafty):
        self.crafty = crafty
        self.server_list = crafty.list_mc_servers()
        self.selected_server = self.server_list[0]["server_id"]

    def button_callback(self, sender, app_data, user_data):
        self.selected_server = user_data
        dpg.configure_item(user_data, show=True)
        self.resize_callback()
        for server in self.server_list:
            if server["server_id"] == user_data:
                pass
            else:
                dpg.configure_item(server["server_id"], show=False)

    def setup_window(self):
        self.window = dpg.window(
            label="Crafty-UI", tag="main", no_move=True, no_resize=True
        )
        self.server_window = dict()
        self.viewport_width = dpg.get_viewport_client_width()
        self.viewport_height = dpg.get_viewport_client_height()
        for server in self.server_list:
            self.server_window[server["server_id"]] = Server(
                self.crafty, server["server_id"]
            )
            self.server_window[server["server_id"]].setup_window()
        self.window_pos = (0, 0)  # dpg.get_item_pos("main")
        dpg.configure_item(self.selected_server, show=True)
        with self.window:
            for server in self.server_list:
                dpg.add_button(
                    label=server["server_name"],
                    user_data=server["server_id"],
                    callback=self.button_callback,
                )

    def update_server_data(self):
        self.viewport_width = dpg.get_viewport_client_width()
        self.viewport_height = dpg.get_viewport_client_height()
        self.resize_callback()
        self.server_window[self.selected_server].update_data()
        self.server_window[self.selected_server].resize_callback()

    def resize_callback(self):
        self.viewport_width = dpg.get_viewport_client_width()
        self.viewport_height = dpg.get_viewport_client_height()
        dpg.configure_item(
            "main", width=round(self.viewport_width / 4), height=self.viewport_height
        )
        self.server_window[self.selected_server].resize_callback()


try:
    win = Main_Window(crafty)
    win.setup_window()
    dpg.set_viewport_resize_callback(win.resize_callback)
    schd = scheduler.RepeatedTimer(0.05, win.update_server_data)
    schd.start()
    dpg.show_item_registry()
    dpg.show_metrics()
except Exception as e:
    logger.exception("Failed to start")
    raise SystemExit


def exit_callback():
    logger.info("Shutting down")
    schd.stop()
    dpg.stop_dearpygui()
    raise SystemExit


dpg.set_exit_callback(exit_callback)
dpg.show_viewport()
dpg.start_dearpygui()
exit_callback()
