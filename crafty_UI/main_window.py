import threading
import os
import time
import dearpygui.dearpygui as dpg
from logging_config import logger
from server import Server


class MainWindow:
    def __init__(self, crafty):
        self.crafty = crafty
        self.serverList = crafty.list_mc_servers()
        self.selectedServer = (
            self.serverList[0]["server_id"] if self.serverList else None
        )
        self.running = True

        # Initialize server instances
        self.serverWindow = dict()
        for server in self.serverList:
            try:
                serverInstance = Server(self.crafty, server["server_id"])
                self.serverWindow[server["server_id"]] = serverInstance
            except Exception as e:
                logger.error(f"Failed to initialize server {server['server_id']}: {e}")

        # Calculate number of threads and servers per thread
        self.numThreads = min(os.cpu_count() or 1, len(self.serverList))
        self.updateThreads = []

        # Distribute servers across threads
        serversPerThread = len(self.serverList) // self.numThreads
        extraServers = len(self.serverList) % self.numThreads

        # Start update threads
        startIdx = 0
        for i in range(self.numThreads):
            # Calculate how many servers this thread will handle
            numServers = serversPerThread + (1 if i < extraServers else 0)
            endIdx = startIdx + numServers

            # Get the server IDs for this thread
            threadServers = [
                self.serverList[j]["server_id"] for j in range(startIdx, endIdx)
            ]

            # Create and start the thread
            thread = threading.Thread(
                target=self.UpdateLoop, args=(threadServers,), daemon=True
            )
            self.updateThreads.append(thread)
            thread.start()

            startIdx = endIdx

    def UpdateLoop(self, serverIds):
        period = 1.0 / 0.3
        while self.running:
            startTime = time.time()

            # Update only assigned servers
            for serverId in serverIds:
                try:
                    server = self.serverWindow[serverId]
                    server.UpdateData()
                except Exception:
                    logger.exception(f"Error updating server {serverId}")

            elapsedTime = time.time() - startTime
            sleepTime = max(0, period - elapsedTime)
            time.sleep(sleepTime)
        else:
            raise SystemExit

    def ButtonCallback(self, sender, app_data, user_data):
        self.selectedServer = user_data
        # Show selected server
        dpg.configure_item(user_data, show=True)
        self.ResizeCallback()
        # Hide all other servers
        for server in self.serverList:
            if server["server_id"] != user_data:
                dpg.configure_item(server["server_id"], show=False)

    def SetupWindow(self):
        # Create main window
        self.window = dpg.window(
            label="Crafty-UI", tag="main", no_move=True, no_resize=True
        )
        self.viewportWidth = dpg.get_viewport_client_width()
        self.viewportHeight = dpg.get_viewport_client_height()

        # Setup server windows
        for serverId, serverInstance in self.serverWindow.items():
            serverInstance.SetupWindow()
            # Initially hide all servers except the selected one
            dpg.configure_item(serverId, show=serverId == self.selectedServer)

        # Create server selection buttons
        self.windowPos = (0, 0)  # dpg.get_item_pos("main")
        with self.window:
            for server in self.serverList:
                dpg.add_button(
                    label=server["server_name"],
                    user_data=server["server_id"],
                    callback=self.ButtonCallback,
                )

    def ResizeCallback(self):
        self.viewportWidth = dpg.get_viewport_client_width()
        self.viewportHeight = dpg.get_viewport_client_height()
        dpg.configure_item(
            "main", width=round(self.viewportWidth / 4), height=self.viewportHeight
        )
        self.serverWindow[self.selectedServer].ResizeCallback()
