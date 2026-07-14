def hashable(key):
    """Make a channel usable as a dict key or set member.

    Channels read back from JSON come out as lists, while the ones built in
    Python are tuples; converting them makes both forms compare equal.
    """
    if isinstance(key, list):
        key = tuple(key)
    return key
