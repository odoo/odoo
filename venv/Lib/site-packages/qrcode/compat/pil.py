# Try to import PIL in either of the two ways it can be installed.
Image = None
ImageDraw = None

try:
    from PIL import Image, ImageDraw  # type: ignore  # noqa: F401
except ImportError:  # pragma: no cover
    try:
        import Image  # type: ignore  # noqa: F401
        import ImageDraw  # type: ignore  # noqa: F401
    except ImportError:
        pass
