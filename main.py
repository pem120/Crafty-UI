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
        }
        self.button_pos = dpg.get_item_pos(self.parsed["id"] + "button_group")
        self.buttons_group = dpg.group(
            horizontal=True, tag=self.parsed["id"] + "button_group"
        )

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
        )
        
        with self.window:
            dpg.add_text(
                default_value="UUID: ", label=self.parsed["id"], show_label=True
            )
            self.run_indicator = dpg.add_text(
                default_value="Running: ", label=self.parsed["running"], show_label=True
            )
            self.logs_term = dpg.add_listbox(
                self.logs, width=-1, num_items=len(self.logs) / 2 + 25
            )
            dpg.add_input_text(
                label="command", width=-1, callback=self.command_callback, on_enter=True
            )
            self.window_pos = dpg.get_item_pos(self.parsed["id"])
            with self.buttons_group:
                dpg.add_button(label="start", callback=self.start)
                dpg.add_button(label="stop", callback=self.stop)

    def resize_callback(self):
        self.viewport_width = dpg.get_viewport_client_width()
        self.viewport_height = dpg.get_viewport_client_height()
        dpg.configure_item(
            self.parsed["id"],
            width=round(self.viewport_width * 3 / 4),
            height=self.viewport_height,
            pos=(
                round(self.window_pos[0] + self.viewport_width / 4),
                self.window_pos[1],
            ),
        )
        dpg.configure_item(
            self.parsed["id"] + "button_group",
            pos=(
                round(self.button_pos[0] + self.viewport_width / 2),
                self.button_pos[1],
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
        }
        dpg.configure_item(self.logs_term, items=self.logs)
        dpg.set_item_label(self.run_indicator, self.parsed["running"])
        self.resize_callback()


class Main_Window:
    def __init__(self, crafty):
        self.crafty = crafty
        self.server_list = crafty.list_mc_servers()
        self.selected_server = self.server_list[1]["server_id"]

    def button_callback(self, sender, app_data, user_data):
        print("change" + user_data)
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
        with self.window:
            for server in self.server_list:
                print("id:" + server["server_id"])
                dpg.add_button(
                    label=server["server_name"],
                    user_data=server["server_id"],
                    callback=self.button_callback,
                )

    def update_server_data(self):
        print("updated: " + self.selected_server)
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
    print("Exiting...")
    update_timer.stop()
    update_timer._timer.cancel()
    dpg.stop_dearpygui()
    raise SystemExit


dpg.set_exit_callback(exit_callback)
dpg.show_viewport()
dpg.start_dearpygui()

update_timer.stop()
update_timer._timer.cancel()
