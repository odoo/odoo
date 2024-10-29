try:
    import lxml.etree as ET  # type: ignore  # noqa: F401
except ImportError:
    import xml.etree.ElementTree as ET  # type: ignore  # noqa: F401
