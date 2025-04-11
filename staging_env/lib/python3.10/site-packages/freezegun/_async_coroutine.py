import functools

import asyncio


def wrap_coroutine(api, coroutine):
    @functools.wraps(coroutine)
    @asyncio.coroutine
    def wrapper(*args, **kwargs):
        with api as time_factory:
            if api.as_arg:
                result = yield from coroutine(time_factory, *args, **kwargs)
            else:
                result = yield from coroutine(*args, **kwargs)
        return result

    return wrapper
