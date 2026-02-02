import html
import re

logs = [
    "[21:55:46] [Server thread/INFO] [minecraft/MinecraftServer]: /forceload (add|remove|query)",
    "[09:49:47] [Server thread/WARN] [minecraft/MinecraftServer]: Can&#x27;t keep up! Is the server overloaded? Running 2652ms or 53 ticks behind",
]

log_pattern = re.compile(
    r"^\[(?P<time>.*?)\] \[(?P<location>.*?)\/(?P<type>.*?)\] \[(?P<root>.*?)\]: (?P<message>.*)$"
)


def parse_logs(log_list: list[str]) -> list[dict]:
    parsed_results = []

    for line in log_list:
        clean_line = html.unescape(line)

        match = log_pattern.match(clean_line)

        if match:
            parsed_results.append(match.groupdict())

    return parsed_results


# Execute and display
formatted_logs = parse_logs(logs)
for entry in formatted_logs[:5]:  # Show first 5 for brevity
    print(entry)
import dearpygui.dearpygui as dpg


# Assuming 'formatted_logs' is the list of dicts from your previous code
def show_logs_in_dpg(formatted_logs):
    dpg.create_context()

    with dpg.window(label="Minecraft Server Logs", width=800, height=600):
        # Create a table for alignment
        with dpg.table(
            header_row=True,
            resizable=True,
            policy=dpg.mvTable_SizingFixedFit,
            row_background=True,
            borders_innerV=True,
            borders_outerV=True,
            borders_outerH=True,
        ):

            dpg.add_table_column(label="Time")
            dpg.add_table_column(label="Location")
            dpg.add_table_column(label="Type")
            dpg.add_table_column(label="Root")
            dpg.add_table_column(label="Message")

            for entry in formatted_logs:
                with dpg.table_row():
                    dpg.add_text(entry["time"], color=[200, 200, 200])  # Gray
                    dpg.add_text(
                        entry["location"], color=[150, 255, 150]
                    )  # Light Green

                    # Logic for Type Coloringhttps://xiaomitools.com/mi-unlock-tool/
                    log_type = entry["type"]
                    type_color = [255, 255, 255]  # Default White
                    if log_type == "WARN":
                        type_color = [255, 200, 0]  # Gold/Yellow
                    elif log_type == "ERROR":
                        type_color = [255, 50, 50]  # Red
                    elif log_type == "INFO":
                        type_color = [100, 200, 255]  # Sky Blue

                    dpg.add_text(log_type, color=type_color)
                    dpg.add_text(entry["root"], color=[180, 180, 180])
                    dpg.add_text(entry["message"])

    dpg.create_viewport(title="Log Parser", width=850, height=650)
    dpg.setup_dearpygui()
    dpg.show_viewport()
    dpg.start_dearpygui()
    dpg.destroy_context()


# Run it
show_logs_in_dpg(formatted_logs)
