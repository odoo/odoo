_MAP = {
    "y": True,
    "yes": True,
    "t": True,
    "true": True,
    "on": True,
    "1": True,
    "n": False,
    "no": False,
    "f": False,
    "false": False,
    "off": False,
    "0": False,
}


def strtobool(value):
    result = _MAP.get(str(value).strip().lower())

    if result is None:
        raise ValueError(f"Invalid boolean value: {repr(value)}")

    return result
