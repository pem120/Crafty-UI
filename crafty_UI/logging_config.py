import colorlog

handler = colorlog.StreamHandler()
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
    datefmt="[%Y-%m-%d](%H:%M:%S)",
)
handler.setFormatter(formatter)

logger = colorlog.getLogger("Main")
logger.addHandler(handler)
urllib_logger = colorlog.getLogger("Main.urllib3")
urllib_logger.setLevel(colorlog.WARNING)
urllib_logger.addHandler(handler)
