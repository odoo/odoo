__all__ = [
    "ANY_UNIQUE",
    "ASSET_EXTENSIONS",
    "DOTTED_ASSET_EXTENSIONS",
    "EXTENSION_TO_WEB_MIMETYPES",
    "EXTERNAL_ASSET",
    "GC_UNLINK_LIMIT",
    "PREFETCH_MAX",
    "SCRIPT_EXTENSIONS",
    "STYLE_EXTENSIONS",
    "SUPPORTED_DEBUGGER",
    "TEMPLATE_EXTENSIONS",
]

SCRIPT_EXTENSIONS = ("js",)
STYLE_EXTENSIONS = ("css", "scss", "sass", "less")
TEMPLATE_EXTENSIONS = ("xml",)
ASSET_EXTENSIONS = SCRIPT_EXTENSIONS + STYLE_EXTENSIONS + TEMPLATE_EXTENSIONS

SUPPORTED_DEBUGGER = {"pdb", "ipdb", "wdb", "pudb"}
EXTERNAL_ASSET = object()

PREFETCH_MAX = 1000
"""Maximum number of prefetched records"""

GC_UNLINK_LIMIT = 100_000
"""Maximum number of records to clean in a single transaction."""

ANY_UNIQUE = "_" * 7
"""Sentinel placeholder for unique asset hashes in URLs."""

DOTTED_ASSET_EXTENSIONS = tuple(f".{ext}" for ext in ASSET_EXTENSIONS)
"""Asset extensions with leading dots (for URL/path matching)."""

# see also mimetypes module: https://docs.python.org/3/library/mimetypes.html
# and odoo.libs.filesystem.mimetypes
EXTENSION_TO_WEB_MIMETYPES = {
    ".css": "text/css",
    ".less": "text/less",
    ".scss": "text/scss",
    ".js": "text/javascript",
    ".xml": "text/xml",
    ".csv": "text/csv",
    ".html": "text/html",
}
"""Mapping of web file extensions to MIME types."""
