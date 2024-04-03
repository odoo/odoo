import sys

__all__ = ['reraise']


def exec_(_code_, _globs_=None, _locs_=None):
    """Execute code in a namespace."""
    if _globs_ is None:
        frame = sys._getframe(1)
        _globs_ = frame.f_globals
        if _locs_ is None:
            _locs_ = frame.f_locals
        del frame
    elif _locs_ is None:
        _locs_ = _globs_
    exec("""exec _code_ in _globs_, _locs_""")

exec_("""def reraise(tp, value, tb=None):
    try:
        raise tp, value, tb
    finally:
        tb = None
""")
