import functools
import urllib.parse
import warnings
from itertools import starmap

orig_urlencode = urllib.parse.urlencode


def check_pair_no_seq(key, value):
    if value is None:
        warnings.warn(f"urlencode got None value for {key!r}, and will not automatically remove it.")
    if not isinstance(value, (bytes, str)):
        warnings.warn(
            f"urlencode expected a str value, but got {type(value).__name__} instead for {key!r}."
            " Did you mean to use `urlencode(..., doseq=True)`?"
        )
    return key, value


def check_pair_do_seq(key, value):
    if value is None:
        warnings.warn(f"urlencode got None value for {key!r}, and will not automatically remove it.")
        return key, value
    if isinstance(value, (bytes, str)):
        return key, value

    try:
        len(value)
    except TypeError:
        warnings.warn(f"urlencode expected a sequence, got {type(value).__name__} instead.")
    else:
        for val in value:
            check_pair_no_seq(key, val)

    return key, value


@functools.wraps(orig_urlencode)
def urlencode(query, **kwargs):
    do_seq = kwargs.get('do_seq', False)
    check_pair = check_pair_do_seq if do_seq else check_pair_no_seq
    if hasattr(query, "items"):
        query = query.items()

    return orig_urlencode(list(starmap(check_pair, query)), **kwargs)


def patch_module():
    urllib.parse.urlencode = urlencode
