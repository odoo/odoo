def tuplify(key):
    if isinstance(key, list):
        key = tuple(key)
    return key
