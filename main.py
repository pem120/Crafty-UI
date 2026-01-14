import threading
import os
import time
import dearpygui.dearpygui as dpg
import crafty_client
import toml
import urllib3
import colorlog
import sched

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


handler = colorlog.StreamHandler()
colorlog.basicConfig
formatter = colorlog.ColoredFormatter(
    "%(asctime)s %(log_color)s [%(name)s] %(levelname)s: %(message)s",
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
    datefmt="%Y-%m-%d %H:%M:%S",
)
handler.setFormatter(formatter)

logger = colorlog.getLogger("Main")
logger.addHandler(handler)
urllib_logger = colorlog.getLogger("Main.urllib3")
urllib_logger.setLevel(colorlog.WARNING)
urllib_logger.addHandler(handler)
logger.log(colorlog.DEBUG, "Helllo")


class Server:
    def __init__(self, crafty: crafty_client.Crafty4, server_uuid: str):
        if crafty is None:
            raise ValueError("Crafty client instance cannot be None")

        self.crafty = crafty
        self.log_length: list[float] = []
        self.stats = None
        self.logs: list[str] = []
        self.server_uuid = server_uuid

        try:
            self.stats = self.crafty.get_server_stats(server_uuid)
            self.logs = self.crafty.get_server_logs(server_uuid) or []
        except Exception as e:
            logger.error(f"Failed to get server stats: {e}")
            raise
        # Parse server data
        if self.stats:
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
        else:
            self.parsed = {
                "id": server_uuid,
                "name": "Unknown",
                "created_time": "",
                "running": False,
                "crashed": False,
                "size": 0,
                "mem": 0,
                "cpu": 0,
            }
        self.logger = colorlog.getLogger(self.parsed["name"])
        self.logger.addHandler(handler)
        self.logger.setLevel(colorlog.DEBUG)

    def start(self):
        try:
            self.crafty.start_server(self.parsed["id"])
        except Exception as e:
            self.logger.error(f"Failed to start the server", exc_info=True)

    def stop(self):
        try:
            self.crafty.stop_server(self.parsed["id"])
        except Exception as e:
            self.logger.exception("Failed to stop server")

    def command_callback(self, sender, app_data, user_data):
        try:
            self.crafty.run_command(self.parsed["id"], app_data)
        except Exception as e:
            self.logger.exception("Failed to execute command")

    def setup_window(self):
        self.window = dpg.window(
            label=self.parsed["name"],
            tag=self.parsed["id"],
            no_move=True,
            no_resize=True,
            show=True,
        )

        self.cpu_plot_x = [0.0]
        self.cpu_plot_y = [0.0]
        self.ram_plot_x = [0.0]
        self.ram_plot_y = [0.0]

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

    def update_data(self):
        try:
            new_stats = self.crafty.get_server_stats(self.parsed["id"])
            new_logs = self.crafty.get_server_logs(self.parsed["id"]) or []

            if new_stats:
                self.stats = new_stats
                self.logs = new_logs
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

                self.cpu_plot_x.append(self.cpu_plot_x[-1] + 1 / 60)
                self.cpu_plot_y.append(float(self.stats["cpu"]) / 10)
                self.ram_plot_x.append(self.ram_plot_x[-1] + 1 / 60)

                if isinstance(self.parsed["mem"], str):
                    if self.parsed["mem"].endswith("GB"):
                        self.ram_plot_y.append(float(self.stats["mem"].strip("GB")))
                    elif self.parsed["mem"].endswith("M"):
                        self.ram_plot_y.append(
                            float(self.stats["mem"].strip("M")) / 1024
                        )
                else:
                    self.ram_plot_y.append(float(self.stats["mem"]))

                self.logger.debug(f"RAM usage: {self.ram_plot_y[-1]}")

                for log in self.logs:
                    if isinstance(log, str):
                        self.log_length.append(dpg.get_text_size(log)[0])

                dpg.configure_item(
                    f"cpu_line_{self.parsed['id']}",
                    x=self.cpu_plot_x,
                    y=self.cpu_plot_y,
                )
                dpg.configure_item(
                    f"ram_line_{self.parsed['id']}",
                    x=self.ram_plot_x,
                    y=self.ram_plot_y,
                )
                dpg.set_item_label(self.run_indicator, str(self.parsed["running"]))
                dpg.configure_item(self.logs_term, items=self.logs)
                self.resize_callback()

        except Exception:
            self.logger.exception("Failed to retrieve server statistics")


class Main_Window:
    def __init__(self, crafty):
        self.crafty = crafty
        self.server_list = crafty.list_mc_servers()
        self.selected_server = (
            self.server_list[0]["server_id"] if self.server_list else None
        )
        self.running = True

        # Initialize server instances
        self.server_window = dict()
        for server in self.server_list:
            try:
                server_instance = Server(self.crafty, server["server_id"])
                self.server_window[server["server_id"]] = server_instance
            except Exception as e:
                logger.error(f"Failed to initialize server {server['server_id']}: {e}")

        # Calculate number of threads and servers per thread
        self.num_threads = min(os.cpu_count() or 1, len(self.server_list))
        self.update_threads = []

        # Distribute servers across threads
        servers_per_thread = len(self.server_list) // self.num_threads
        extra_servers = len(self.server_list) % self.num_threads

        # Start update threads
        start_idx = 0
        for i in range(self.num_threads):
            # Calculate how many servers this thread will handle
            num_servers = servers_per_thread + (1 if i < extra_servers else 0)
            end_idx = start_idx + num_servers

            # Get the server IDs for this thread
            thread_servers = [
                self.server_list[j]["server_id"] for j in range(start_idx, end_idx)
            ]

            # Create and start the thread
            thread = threading.Thread(
                target=self.update_loop, args=(thread_servers,), daemon=True
            )
            self.update_threads.append(thread)
            thread.start()

            start_idx = end_idx

    def update_loop(self, server_ids):
        period = 1.0 / 60
        while self.running:
            start_time = time.time()

            # Update only assigned servers
            for server_id in server_ids:
                try:
                    server = self.server_window[server_id]
                    # Update server data directly
                    server.update_data()
                except Exception as e:
                    logger.exception(f"Error updating server {server_id}")

            elapsed_time = time.time() - start_time
            sleep_time = max(0, period - elapsed_time)
            time.sleep(sleep_time)
        else:
            raise SystemExit

    def button_callback(self, sender, app_data, user_data):
        self.selected_server = user_data
        # Show selected server
        dpg.configure_item(user_data, show=True)
        self.resize_callback()
        # Hide all other servers
        for server in self.server_list:
            if server["server_id"] != user_data:
                dpg.configure_item(server["server_id"], show=False)

    def setup_window(self):
        # Create main window
        self.window = dpg.window(
            label="Crafty-UI", tag="main", no_move=True, no_resize=True
        )
        self.viewport_width = dpg.get_viewport_client_width()
        self.viewport_height = dpg.get_viewport_client_height()

        # Setup server windows
        for server_id, server_instance in self.server_window.items():
            server_instance.setup_window()
            # Initially hide all servers except the selected one
            dpg.configure_item(server_id, show=server_id == self.selected_server)

        # Create server selection buttons
        self.window_pos = (0, 0)  # dpg.get_item_pos("main")
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

    def resize_callback(self):
        self.viewport_width = dpg.get_viewport_client_width()
        self.viewport_height = dpg.get_viewport_client_height()
        dpg.configure_item(
            "main", width=round(self.viewport_width / 4), height=self.viewport_height
        )


def exit_callback():
    logger.info("Shutting down")
    win.running = False
    schduler.cancel(event)
    dpg.stop_dearpygui()
    raise SystemExit


if __name__ == "__main__":
    try:
        dpg.create_context()
        dpg.create_viewport(title="Crafty UI")
        dpg.setup_dearpygui()

        win = Main_Window(crafty)
        win.setup_window()

        schduler = sched.scheduler(time.time, time.sleep)
        event = schduler.enter(0.05, 1, win.update_server_data)
        schduler.run(blocking=False)

        dpg.set_viewport_resize_callback(win.resize_callback)
        dpg.set_exit_callback(exit_callback)
        dpg.show_viewport()
        dpg.start_dearpygui()

        exit_callback()
    except Exception as e:
        logger.exception("Failed to start")
        exit(-1)
