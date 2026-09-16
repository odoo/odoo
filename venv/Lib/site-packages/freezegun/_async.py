import functools
from typing import Any, Callable, TypeVar, cast


_CallableT = TypeVar("_CallableT", bound=Callable[..., Any])


def wrap_coroutine(api: Any, coroutine: _CallableT) -> _CallableT:
    @functools.wraps(coroutine)
    async def wrapper(*args: Any, **kwargs: Any) -> Any:
        with api as time_factory:
            if api.as_arg:
                result = await coroutine(time_factory, *args, **kwargs)
            else:
                result = await coroutine(*args, **kwargs)
        return result

    return cast(_CallableT, wrapper)
