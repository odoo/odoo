import functools


def wrap_coroutine(api, coroutine):
    @functools.wraps(coroutine)
    async def wrapper(*args, **kwargs):
        with api as time_factory:
            if api.as_arg:
                result = await coroutine(time_factory, *args, **kwargs)
            else:
                result = await coroutine(*args, **kwargs)
        return result

    return wrapper
