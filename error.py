import config

errors = []

def error(msg: str):
    print(f"error! -> {msg}")
    errors.append(msg)

def debug(msg):
    if config.debug:
        print(f"[debug] {msg}")