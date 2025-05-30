import dearpygui.dearpygui as dpg
import crafty_client, scheduler
import toml
import urllib3

urllib3.disable_warnings()

conf = toml.load("server.toml")
server_url = conf["server"]["url"]
server_token = conf["server"]["token"]
crafty = crafty_client.Crafty4(server_url, server_token)

dpg.create_context()
dpg.create_viewport(title="Crafty UI")
dpg.setup_dearpygui()


class Server:
    def __init__(self, crafty, server_uuid):
        try:
            self.stats = crafty.get_server_stats(server_uuid)
            self.logs = crafty.get_server_logs(server_uuid)
            self.crafty = crafty
        except:
            print("failed to get server stats,Retrying")
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

    def start(self):
        self.crafty.start_server(self.parsed["id"])

    def stop(self):
        self.crafty.stop_server(self.parsed["id"])

    def command_callback(self, sender, app_data, user_data):
        crafty.run_command(self.parsed["id"], app_data)

    def setup_window(self):
        self.window = dpg.window(
            label=self.parsed["name"],
            tag=self.parsed["id"],
            no_move=True,
            no_resize=True,
            show=False,
        )
        self.button_group = dpg.group(horizontal=True, tag=f"group_{self.parsed['id']}")
        self.plot_group = dpg.group(horizontal=True, tag=f"plot_{self.parsed['id']}")

        self.cpu_plot_x = [0]
        self.cpu_plot_y = [0]
        self.ram_plot_x = [0]
        self.ram_plot_y = [0]
        with self.window:
            self.tabs = dpg.tab_bar()
            with self.tabs:
                #self.log_tab = dpg.tab(label="Terminal")
                #self.plots_tab = dpg.tab(label="Graphs")
                with dpg.tab(label="Terminal"):
                    dpg.add_text(
                        default_value="UUID: ", label=self.parsed["id"], show_label=True
                    )
                    self.run_indicator = dpg.add_text(
                        default_value="Running: ",
                        label=self.parsed["running"],
                        show_label=True,
                    )
                    self.logs_term = dpg.add_listbox(
                        self.logs, width=-1, num_items=len(self.logs) / 2 + 25
                    )
                    dpg.add_input_text(
                        label="command",
                        width=-1,
                        callback=self.command_callback,
                        on_enter=True,
                    )
                    self.window_pos = dpg.get_item_pos(self.parsed["id"])
                    with self.button_group:
                        dpg.add_button(label="start", callback=self.start)
                        dpg.add_button(label="stop", callback=self.stop)
                with dpg.tab(label="Graphs"):
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
        self.window_width = round(self.viewport_width * 3 / 4)

        dpg.configure_item(
            self.parsed["id"],
            width=self.window_width,
            height=self.viewport_height,
            pos=(
                round(self.window_pos[0] + self.viewport_width / 4),
                self.window_pos[1],
            ),
        )
        self.group_pos = dpg.get_item_pos(f"group_{self.parsed['id']}")
        self.group_width = dpg.get_item_width(f"group_{self.parsed['id']}")
        print((self.window_width / 2) + self.group_width / 2)
        dpg.configure_item(
            f"group_{self.parsed['id']}",
            pos=(
                round((self.window_width / 2) + self.group_width / 2),
                self.group_pos[1],
            ),
        )

    def update_data(self):
        try:
            self.stats = crafty.get_server_stats(self.parsed["id"])
            self.logs = crafty.get_server_logs(self.parsed["id"])
        except:
            pass
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

        if type(self.stats["mem"]) == str:
            self.ram_plot_y.append(float(self.stats["mem"].strip("GB")))
        else:
            self.ram_plot_y.append(self.stats["mem"])

        dpg.configure_item(
            f"cpu_line_{self.parsed['id']}", x=self.cpu_plot_x, y=self.cpu_plot_y
        )
        dpg.configure_item(
            f"ram_line_{self.parsed['id']}", x=self.ram_plot_x, y=self.ram_plot_y
        )
        dpg.set_item_label(self.run_indicator, self.parsed["running"])
        dpg.configure_item(self.logs_term, items=self.logs)
        self.resize_callback()


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


win = Main_Window(crafty)
win.setup_window()
dpg.set_viewport_resize_callback(win.resize_callback)
update_timer = scheduler.RepeatedTimer(1, win.update_server_data)


def exit_callback():
    update_timer.stop()
    update_timer._timer.cancel()
    dpg.stop_dearpygui()
    raise SystemExit


dpg.set_exit_callback(exit_callback)
dpg.show_viewport()
dpg.start_dearpygui()

update_timer.stop()
update_timer._timer.cancel()
