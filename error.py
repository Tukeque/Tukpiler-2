import config
from rich import print

errors = []

def error(msg: str):
    print(f"[red]<!!error!!> -> {msg}")
    errors.append(msg)

def debug(msg):
    if config.debug:
        print(f"[yellow]\[debug] {msg}")