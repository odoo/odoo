# Try to import png library.
PngWriter = None

try:
    from png import Writer as PngWriter  # type: ignore  # noqa: F401
except ImportError:  # pragma: no cover
    pass
