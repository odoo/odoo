
from functools import wraps
import logging
import sys

def lw(original_function=None, logger_name=None, loglevel=logging.DEBUG):
    """
    Log wrapper decorator factory.
    Can be use to wrap a sensible function to log its start and end with its arguments and result.

    Examples::

    ```python
    from log_utils import lw

    # As decorator:
    @lw
    def foo():
        print('foo')

    foo()
    '''
    DEBUG:__main__:foo starting with args:() kwargs:{}
    foo
    DEBUG:__main__:foo finished with result: None
    '''


    @lw(logger_name="test bar", loglevel=logging.ERROR)
    def bar(arg=0):
        print(f"bar {arg}")
        return arg

    bar(2)
    '''
    ERROR:test bar:bar starting with args:(2,) kwargs:{}
    bar 2
    ERROR:test bar:bar finished with result: 2
    '''

    # Inline calls:
    def baz(arg=0):
        print(f"baz {arg}")
        return arg

    lw(baz)(3)
    '''
    DEBUG:__main__:baz starting with args:(3,) kwargs:{}
    baz 3
    DEBUG:__main__:baz finished with result: 3
    '''

    lw(baz, loglevel=logging.ERROR)(4)
    '''
    ERROR:__main__:baz starting with args:(4,) kwargs:{}
    baz 4
    ERROR:__main__:baz finished with result: 4
    '''

    lw(print)("hello", "world")
    '''
    DEBUG:__main__:print starting with args:('hello', 'world') kwargs:{}
    hello world
    DEBUG:__main__:print finished with result: None
    '''

    print(lw(sum)((40, 2)))
    '''
    DEBUG:__main__:print finished with result: None
    DEBUG:__main__:sum starting with args:((40, 2),) kwargs:{}
    DEBUG:__main__:sum finished with result: 42
    42
    '''
    ```

    :param original_function: the function to wrap
    :param logger_name: the logger name to use (default: logger name of the function module will be used)
    :param loglevel: the log level to use (default: logging.DEBUG)
    :return: the decorated function
    """
    def decorator(function):
        @wraps(function)
        def wrapper(*args, **kwargs):
            logger = logging.getLogger(logger_name or function.__module__)
            logger.log(loglevel, "%s starting with args:%s kwargs:%s", function.__name__, args, kwargs)
            result = function(*args, **kwargs)
            logger.log(loglevel, "%s finished with result: %s", function.__name__, result)
            return result
        return wrapper
    if original_function:
        # In the case of inline call of the decorator with functions outside of the IoT addons,
        # we might use the wrong logger_name if we use function.__module__.
        #
        # e.g: `lw(print)()`
        # does have `function.__module__ == 'builtins'`
        # which will log outside of the logger scope (so it won't appear in the IoT logs)
        #
        # Note: decorated functions will not have this issue as they are written in Odoo IoT addons
        if logger_name is None:
            # inspired by: https://stackoverflow.com/a/5071539
            logger_name = sys._getframe(1).f_globals['__name__']
        return decorator(original_function)
    return decorator
