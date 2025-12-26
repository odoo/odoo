try:
    from collections.abc import Mapping
except ImportError:  # pragma: no cover
    # Python < 3.3
    from collections.abc import Mapping  # pragma: no cover


def string_types():
    """Taken from https://git.io/JIv5J"""

    return (str,)


def is_namedtuple(value):
    """https://stackoverflow.com/a/2166841/1843746
    But modified to handle subclasses of namedtuples.
    Taken from https://git.io/JIsfY
    """
    if not isinstance(value, tuple):
        return False
    f = getattr(type(value), "_fields", None)
    if not isinstance(f, tuple):
        return False
    return all(isinstance(n, str) for n in f)


def iteritems(d, **kw):
    """Override iteritems for support multiple versions python.
    Taken from https://git.io/JIvMi
    """
    return iter(d.items(**kw))


def varmap(func, var, context=None, name=None):
    """Executes ``func(key_name, value)`` on all values
    recurisively discovering dict and list scoped
    values. Taken from https://git.io/JIvMN
    """
    if context is None:
        context = {}
    objid = id(var)
    if objid in context:
        return func(name, "<...>")
    context[objid] = 1

    if isinstance(var, list | tuple) and not is_namedtuple(var):
        ret = [varmap(func, f, context, name) for f in var]
    else:
        ret = func(name, var)
        if isinstance(ret, Mapping):
            ret = {k: varmap(func, v, context, k) for k, v in iteritems(var)}
    del context[objid]
    return ret


def get_environ(environ):
    """Returns our whitelisted environment variables.
    Taken from https://git.io/JIsf2
    """
    for key in ("REMOTE_ADDR", "SERVER_NAME", "SERVER_PORT"):
        if key in environ:
            yield key, environ[key]
