# ruff: noqa: F401
"""Bus module JSON serialization — delegates to the centralized orjson wrapper."""
from odoo.libs.json.orjson_wrapper import dumps_bytes as dumps, loads
