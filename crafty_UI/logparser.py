import html
import re

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
