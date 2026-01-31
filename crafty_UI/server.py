import dearpygui.dearpygui as dpg
import crafty_client
import colorlog
from logging_config import logger, handler
import websocket


class Server:
    def __init__(self, crafty: crafty_client.Crafty4, serverUuid: str):
        if crafty is None:
            raise ValueError("Crafty client instance cannot be None")

        self.crafty = crafty
        self.logLength: list[float] = []
        self.stats = None
        self.logs: list[str] = []
        self.serverUuid = serverUuid
        print(serverUuid)

        try:
            self.stats = self.crafty.get_server_stats(serverUuid)
            self.logs = self.crafty.get_server_logs(serverUuid) or []
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
                "id": serverUuid,
                "name": "Unknown",
                "created_time": "",
                "running": False,
                "crashed": False,
                "size": -1,
                "mem": -1,
                "cpu": -1,
            }
        self.logger = colorlog.getLogger(self.parsed["name"])
        self.logger.addHandler(handler)
        self.logger.setLevel(colorlog.DEBUG)

    def Start(self):
        try:
            self.crafty.start_server(self.parsed["id"])
        except Exception as e:
            self.logger.error(f"Failed to start the server", exc_info=True)

    def Stop(self):
        try:
            self.crafty.stop_server(self.parsed["id"])
        except Exception as e:
            self.logger.exception("Failed to stop server")

    def CommandCallback(self, sender, app_data, user_data):
        try:
            self.crafty.run_command(self.parsed["id"], app_data)
        except Exception as e:
            self.logger.exception("Failed to execute command")

    def SetupWindow(self):
        self.window = dpg.window(
            label=self.parsed["name"],
            tag=self.parsed["id"],
            no_move=True,
            no_resize=True,
            show=True,
        )

        self.cpuPlotX = [0.0]
        self.cpuPlotY = [0.0]
        self.ramPlotX = [0.0]
        self.ramPlotY = [0.0]

        with self.window:
            self.tabs = dpg.tab_bar()
            with self.tabs:
                with dpg.tab(label="Terminal"):
                    self.uuid = dpg.add_text(
                        default_value="UUID: ", label=self.parsed["id"], show_label=True
                    )
                    self.runIndicator = dpg.add_text(
                        default_value="Running: ",
                        label=self.parsed["running"],
                        show_label=True,
                    )
                    with dpg.child_window(
                        label="Terminalwin",
                        horizontal_scrollbar=True,
                        border=False,
                        # autosize_x=True,
                        # autosize_y=False,
                        height=-1,
                    ):
                        self.logsTerm = dpg.add_listbox(
                            self.logs,
                            width=-1,
                            num_items=25,
                            tracked=True,
                        )
                        self.commandInput = dpg.add_input_text(
                            label="command",
                            width=-1,
                            callback=self.CommandCallback,
                            on_enter=True,
                        )
                        self.windowPos = dpg.get_item_pos(self.parsed["id"])
                        self.buttonGroup = None
                        with dpg.group(
                            horizontal=True,
                            tag=f"group_{self.parsed['id']}",
                        ):
                            dpg.add_button(label="start", callback=self.Start)
                            dpg.add_button(label="stop", callback=self.Stop)

                with dpg.tab(label="Graphs"):
                    self.plotGroup = dpg.group(
                        horizontal=True,
                        tag=f"plot_{self.parsed['id']}",
                        width=-1,
                        height=-1,
                    )
                    with self.plotGroup:
                        self.cpuPlot = dpg.plot(label="CPU Usage", width=-1)
                        self.ramPlot = dpg.plot(label="RAM Usage", width=-1)
                    with self.cpuPlot:
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
                            self.cpuPlotX,
                            self.cpuPlotY,
                            label="CPU Usage",
                            parent=f"cpu_usage_y_{self.parsed['id']}",
                            tag=f"cpu_line_{self.parsed['id']}",
                        )
                    with self.ramPlot:
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
                            self.ramPlotX,
                            self.ramPlotY,
                            label="RAM Usage",
                            parent=f"ram_usage_y_{self.parsed['id']}",
                            tag=f"ram_line_{self.parsed['id']}",
                        )
                    dpg.fit_axis_data(f"ram_usage_y_{self.parsed['id']}")
                    dpg.fit_axis_data(f"ram_usage_x_{self.parsed['id']}")
                    dpg.fit_axis_data(f"cpu_usage_y_{self.parsed['id']}")
                    dpg.fit_axis_data(f"cpu_usage_x_{self.parsed['id']}")
                    self.buttonPos = dpg.get_item_pos(f"group_{self.parsed['id']}")

    def ResizeCallback(self):
        self.viewportWidth = dpg.get_viewport_client_width()
        self.viewportHeight = dpg.get_viewport_client_height()
        self.windowWidth = dpg.get_item_width(self.parsed["id"])

        dpg.configure_item(
            self.parsed["id"],
            width=round(self.viewportWidth * 3 / 4),
            height=self.viewportHeight,
            pos=(
                round(self.windowPos[0] + self.viewportWidth / 4),
                self.windowPos[1],
            ),
        )

        self.groupPos = dpg.get_item_pos(f"group_{self.parsed['id']}")
        self.groupWidth = dpg.get_item_width(f"group_{self.parsed['id']}")

    def UpdateData(self):
        try:
            newStats = self.crafty.get_server_stats(self.parsed["id"])
            newLogs = self.crafty.get_server_logs(self.parsed["id"]) or []

            if newStats:
                self.stats = newStats
                self.logs = newLogs
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

                self.cpuPlotX.append(self.cpuPlotX[-1] + 1 / 0.3)
                self.cpuPlotY.append(float(self.stats["cpu"]) / 10)
                self.ramPlotX.append(self.ramPlotX[-1] + 1 / 0.3)

                if isinstance(self.parsed["mem"], str):
                    if float(self.parsed["mem"].strip("GB").strip("MB")) == 0.0:
                        self.ramPlotY.append(0.0)
                    else:
                        if self.parsed["mem"].endswith("GB"):
                            self.ramPlotY.append(float(self.stats["mem"].strip("GB")))
                        elif self.parsed["mem"].endswith("MB"):
                            self.ramPlotY.append(
                                float(self.stats["mem"].strip("MB")) / 1000
                            )
                else:
                    self.ramPlotY.append(float(self.stats["mem"]))

                for log in self.logs:
                    if isinstance(log, str):
                        self.logLength.append(dpg.get_text_size(log)[0])
                print(self.logs)

                dpg.configure_item(
                    f"cpu_line_{self.parsed['id']}",
                    x=self.cpuPlotX,
                    y=self.cpuPlotY,
                )
                dpg.configure_item(
                    f"ram_line_{self.parsed['id']}",
                    x=self.ramPlotX,
                    y=self.ramPlotY,
                )
                dpg.set_item_label(self.runIndicator, str(self.parsed["running"]))
                dpg.configure_item(self.logsTerm, items=self.logs)
                self.ResizeCallback()

        except Exception:
            self.logger.exception("Failed to retrieve server statistics")
