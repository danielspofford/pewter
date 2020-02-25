import inspect
import json
from datetime import datetime

import click

from . import puter


def text(data):
    """
    Logs a string, `data`, to stdout.
    """
    click.echo(f"{data}")


def data(data, frame_info=False):
    """
    Logs a dict, `data`, both to stdout and as a structured json log to the log file.

    All logs include the following meta information:

    - inspect stack
    - log timestamp
    """
    text(f"{data}")
    stack = frame_info or inspect.stack()[1:]
    commit(data, stack)


def commit(data, stack):
    """
    Logs an exception, `e`, as a structured json log to the log file.
    """
    timestamp = datetime.now().isoformat()
    log_dict = {
        **data,
        "meta": {"stack": f"{stack}", "datetime": timestamp},
    }
    log_path = puter.data_dir() / "log.txt"
    # log_path.touch(mode=0o600)
    with open(log_path, "a") as file:
        log_json = json.dumps(log_dict)
        file.write(f"{log_json}\n")


def exception(e):
    """
    Logs an exception, `e`, as a structured json log to the log file and immediately re-raises it.
    """
    frame_info = inspect.stack()[1:]
    data({"exception": f"{e}"}, inspect.stack())
    raise e
