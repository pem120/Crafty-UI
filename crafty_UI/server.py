import dearpygui.dearpygui as dpg
import crafty_client
import colorlog
from crafty_UI.logging_config import logger, handler
from crafty_UI import crafttyWSAPI
import threading
import html
from crafty_UI.logparser import parse_logs


class Server:
    def __init__(self, crafty: crafty_client.Crafty4, serverUuid: str):

        if crafty is None:
            raise ValueError("Crafty client instance cannot be None")

        self.crafty = crafty
        self.logLength: list[float] = []
        self.stats = list[str]
        self.logs: list[str] = []
        self.serverUuid = serverUuid
        # Initialize plot data lists
        self.cpuPlotX = [0.0]
        self.cpuPlotY = [0.0]
        self.ramPlotX = [0.0]
        self.ramPlotY = [0.0]

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
        if self.logs:
            for l in range(len(self.logs)):
                self.logs[l] = html.unescape(self.logs[l])

        self.logger = colorlog.getLogger(self.parsed["name"])
        self.logger.addHandler(handler)
        self.logger.setLevel(colorlog.DEBUG)
        self.WSAPI = crafttyWSAPI.CraftyWSAPI(crafty, self.serverUuid)
        self.WSThread = threading.Thread(target=self.WSAPI.run, daemon=True)
        self.WSThread.start()

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
                    # logs child window (contains a table for parsed logs)
                    logs_child_tag = f"logs_child_{self.parsed['id']}"
                    logs_table_tag = f"logs_table_{self.parsed['id']}"

                    # create a table for structured logs
                    with dpg.table(
                        header_row=True,
                        resizable=True,
                        policy=dpg.mvTable_SizingFixedFit,
                        row_background=True,
                        borders_innerV=True,
                        borders_outerV=True,
                        borders_outerH=True,
                        tag=logs_table_tag,
                    ):
                        dpg.add_table_column(label="Time")
                        dpg.add_table_column(label="Location")
                        dpg.add_table_column(label="Type")
                        dpg.add_table_column(label="Root")
                        dpg.add_table_column(label="Message")
                    # ensure table is visible / sized
                    try:
                        dpg.configure_item(
                            logs_table_tag, width=-1, show=True  # height=-1,
                        )
                    except Exception:
                        pass
                    # populate initial table rows (limit to last 25 entries)
                    parsed = parse_logs(self.logs[-25:])
                    for entry in parsed:
                        with dpg.table_row(parent=logs_table_tag):
                            dpg.add_text(entry.get("time", ""), color=[200, 200, 200])
                            dpg.add_text(
                                entry.get("location", ""), color=[150, 255, 150]
                            )
                            log_type = entry.get("type", "")
                            type_color = [255, 255, 255]
                            if log_type == "WARN":
                                type_color = [255, 200, 0]
                            elif log_type == "ERROR":
                                type_color = [255, 50, 50]
                            elif log_type == "INFO":
                                type_color = [100, 200, 255]
                            dpg.add_text(log_type, color=type_color)
                            dpg.add_text(entry.get("root", ""), color=[180, 180, 180])
                            dpg.add_text(entry.get("message", ""))
                    with dpg.group(
                        horizontal=True,
                        tag=f"group_{self.parsed['id']}",
                    ):
                        dpg.add_button(label="start", callback=self.Start)
                        dpg.add_button(label="stop", callback=self.Stop)
                    self.commandInput = dpg.add_input_text(
                        label="command",
                        width=-1,
                        callback=self.CommandCallback,
                        on_enter=True,
                    )

                    self.logsTerm = logs_child_tag
                    self.logsTable = logs_table_tag

                    self.windowPos = dpg.get_item_pos(self.parsed["id"])
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

        # self.groupPos = dpg.get_item_pos(f"group_{self.parsed['id']}")
        # self.groupWidth = dpg.get_item_width(f"group_{self.parsed['id']}")

    def UpdateData(self):
        try:
            newLogs = []
            newStats = self.WSAPI.get_stats()
            newLogs = self.logs + self.WSAPI.get_logs()

            if newStats or newLogs:
                self.stats = newStats
                self.logs = newLogs
                try:
                    self.parsed = {
                        "id": self.stats["id"],
                        "name": self.parsed["name"],
                        "created_time": self.parsed["created_time"],
                        "running": self.stats["running"],
                        "crashed": self.stats["crashed"],
                        "size": self.stats["world_size"],
                        "mem": self.stats["mem"],
                        "cpu": self.stats["cpu"],
                    }
                except:
                    self.logger.exception("Faied to update Stats")
                print(self.parsed["cpu"])

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

                parsed = parse_logs(self.logs[-25:])
                try:
                    rows = dpg.get_item_children(self.logsTable, slot=1)
                    for row in rows:
                        dpg.delete_item(row)
                except:
                    pass
                if parsed:
                    for entry in parsed:
                        with dpg.table_row(parent=self.logsTable):
                            dpg.add_text(entry.get("time", ""), color=[200, 200, 200])
                            dpg.add_text(
                                entry.get("location", ""), color=[150, 255, 150]
                            )
                            log_type = entry.get("type", "")
                            type_color = [255, 255, 255]
                            if log_type == "WARN":
                                type_color = [255, 200, 0]
                            elif log_type == "ERROR":
                                type_color = [255, 50, 50]
                            elif log_type == "INFO":
                                type_color = [100, 200, 255]
                            dpg.add_text(log_type, color=type_color)
                            dpg.add_text(entry.get("root", ""), color=[180, 180, 180])
                            dpg.add_text(entry.get("message", ""))
                else:
                    """# fallback to raw text entries inside the child if parsing produced nothing
                    dpg.delete_item(self.logsTerm, children_only=True)
                    for log in self.logs[-25:]:
                        dpg.add_text(log, parent=self.logsTerm)
                        # scroll the logs child to bottom
                        dpg.set_y_scroll(self.logsTerm, -1)
                        # update debug counter and remember the count we last rendered
                        try:
                            dpg.set_value(self.logsCountText, f"Logs: {len(self.logs)}")
                        except Exception:
                            pass
                        # remember the count we last rendered
                        try:
                            self._last_logs_count = len(self.logs)
                        except Exception:
                            pass"""
                    pass

                self.ResizeCallback()

        except Exception:
            self.logger.exception("Failed to retrieve server statistics")
