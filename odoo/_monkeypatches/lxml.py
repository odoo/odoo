import re
from importlib.metadata import version

from odoo.tools import parse_version

ARIA_ATTRIBUTES = frozenset([
    "aria-activedescendant", "aria-atomic", "aria-autocomplete",
    "aria-braillelabel", "aria-brailleroledescription", "aria-busy",
    "aria-checked", "aria-colcount", "aria-colindex", "aria-colindextext",
    "aria-colspan", "aria-controls", "aria-current", "aria-describedby",
    "aria-description", "aria-details", "aria-disabled", "aria-dropeffect",
    "aria-errormessage", "aria-expanded", "aria-flowto", "aria-grabbed",
    "aria-haspopup", "aria-hidden", "aria-invalid", "aria-keyshortcuts",
    "aria-label", "aria-labelledby", "aria-level", "aria-live", "aria-modal",
    "aria-multiline", "aria-multiselectable", "aria-orientation", "aria-owns",
    "aria-placeholder", "aria-posinset", "aria-pressed", "aria-readonly",
    "aria-relevant", "aria-required", "aria-roledescription", "aria-rowcount",
    "aria-rowindex", "aria-rowindextext", "aria-rowspan", "aria-selected",
    "aria-setsize", "aria-sort", "aria-valuemax", "aria-valuemin",
    "aria-valuenow", "aria-valuetext", "role", "tabindex",
])


def patch_module():
    """
    Patches lxml to:
    1. Add ARIA attributes to the allowed whitelist for lxml.html.clean (versions < 7.0.0).
    2. Fix an issue where data URLs in style attributes are removed erroneously (versions 4.6.0 - 5.2.0).
    """
    lxml_version = parse_version(version("lxml"))

    # 1. Add missing ARIA attributes
    if lxml_version < parse_version("7.0.0"):
        import lxml.html.defs  # noqa: PLC0415
        lxml.html.defs.safe_attrs |= ARIA_ATTRIBUTES

    # 2. Fix Regex for Data URLs
    # Between these versions, the regex is too greedy, resulting in erroneously
    # removing style attributes or nodes with multiple data URLs.
    if parse_version("4.6.0") <= lxml_version < parse_version("5.2.0"):
        # ⚠️ Keep this import *after* the patch to lxml.html.defs
        import lxml.html.clean  # noqa: PLC0415
        lxml.html.clean._find_image_dataurls = re.compile(r'data:image/(.+?);base64,').findall
