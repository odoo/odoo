__all__ = [
    "ANY_UNIQUE",
    "ASSET_EXTENSIONS",
    "DOTTED_ASSET_EXTENSIONS",
    "ESM_BRIDGE_REFRESH_DAYS",
    "EXTENSION_TO_WEB_MIMETYPES",
    "EXTERNAL_ASSET",
    "SCRIPT_EXTENSIONS",
    "STYLE_EXTENSIONS",
    "TEMPLATE_EXTENSIONS",
    "ExternalAsset",
]

SCRIPT_EXTENSIONS = ("js",)
STYLE_EXTENSIONS = ("css", "scss", "sass")
TEMPLATE_EXTENSIONS = ("xml",)
ASSET_EXTENSIONS = SCRIPT_EXTENSIONS + STYLE_EXTENSIONS + TEMPLATE_EXTENSIONS


class ExternalAsset:
    __slots__ = ()

    def __repr__(self) -> str:
        return "EXTERNAL_ASSET"


EXTERNAL_ASSET = ExternalAsset()

ANY_UNIQUE = "_" * 7

ESM_BRIDGE_REFRESH_DAYS = 1.0

DOTTED_ASSET_EXTENSIONS = tuple(f".{ext}" for ext in ASSET_EXTENSIONS)

EXTENSION_TO_WEB_MIMETYPES = {
    ".css": "text/css",
    ".scss": "text/scss",
    ".js": "text/javascript",
    ".xml": "text/xml",
    ".csv": "text/csv",
    ".html": "text/html",
}
