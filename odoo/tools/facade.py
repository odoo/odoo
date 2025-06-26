import functools
import inspect


class ProxyAttr:
    """
    Descriptor class for wrapping attributes of the wrapped instance.

    Used with the `Proxy` class, this class is used to set exposed attributes of the wrapped instance while providing
    optional type casting.
    """
    def __init__(self, cast=False):
        self._cast__ = cast

    def __set_name__(self, owner, name):
        cast = self._cast__
        if cast:
            def getter(self):
                value = getattr(self._wrapped__, name)
                return cast(value) if value is not None else None
        else:
            def getter(self):
                return getattr(self._wrapped__, name)

        def setter(self, value):
            return setattr(self._wrapped__, name, value)

        setattr(owner, name, property(getter, setter))


class ProxyFunc:
    """
    Descriptor class for wrapping functions of the wrapped instance.

    Used with the `Proxy` class, this class is used to set exposed functions of the wrapped instance
    while also allowing optional type casting on return values.
    """
    def __init__(self, cast=False):
        self._cast__ = cast

    def __set_name__(self, owner, name):
        func = getattr(owner._wrapped__, name)
        descriptor = inspect.getattr_static(owner._wrapped__, name)
        cast = self._cast__

        if isinstance(descriptor, staticmethod):
            if cast:
                def wrap_func(*args, **kwargs):
                    result = func(*args, **kwargs)
                    return cast(result) if result is not None else None
            elif cast is None:
                def wrap_func(*args, **kwargs):
                    func(*args, **kwargs)
            else:
                def wrap_func(*args, **kwargs):
                    return func(*args, **kwargs)

            functools.update_wrapper(wrap_func, func)
            wrap_func = staticmethod(wrap_func)

        elif isinstance(descriptor, classmethod):
            if cast:
                def wrap_func(cls, *args, **kwargs):
                    result = func(*args, **kwargs)
                    return cast(result) if result is not None else None
            elif cast is None:
                def wrap_func(cls, *args, **kwargs):
                    func(*args, **kwargs)
            else:
                def wrap_func(cls, *args, **kwargs):
                    return func(*args, **kwargs)

            functools.update_wrapper(wrap_func, func)
            wrap_func = classmethod(wrap_func)

        else:
            if cast:
                def wrap_func(self, *args, **kwargs):
                    result = func(self._wrapped__, *args, **kwargs)
                    return cast(result) if result is not None else None
            elif cast is None:
                def wrap_func(self, *args, **kwargs):
                    func(self._wrapped__, *args, **kwargs)
            else:
                def wrap_func(self, *args, **kwargs):
                    return func(self._wrapped__, *args, **kwargs)

            functools.update_wrapper(wrap_func, func)

        setattr(owner, name, wrap_func)


class ProxyMeta(type):
    def __new__(cls, clsname, bases, attrs):
        attrs.update({func: ProxyFunc() for func in ("__repr__", "__str__") if func not in attrs})
        proxy_class = super().__new__(cls, clsname, bases, attrs)
        # To preserve the docstring, signature, code of the wrapped class
        # `updated` to an emtpy list so it doesn't copy the `__dict__`
        # See `functools.WRAPPER_ASSIGNMENTS` and `functools.WRAPPER_UPDATES`
        functools.update_wrapper(proxy_class, proxy_class._wrapped__, updated=[])
        return proxy_class


class Proxy(metaclass=ProxyMeta):
    """
    A proxy class implementing the Facade pattern.

    This class delegates to an underlying instance while exposing a curated subset of its attributes and methods.
    Useful for controlling access, simplifying interfaces, or adding cross-cutting concerns.
    """
    _wrapped__ = object

    def __init__(self, instance):
        """
        Initializes the proxy by setting the wrapped instance.

        :param instance: The instance of the class to be wrapped.
        """
        object.__setattr__(self, "_wrapped__", instance)
