from six import PY2


if PY2:  # pragma: no cover (PY2)
    import collections as collections_abc  # noqa: F401
else:  # pragma: no cover (PY3)
    import collections.abc as collections_abc  # noqa: F401
