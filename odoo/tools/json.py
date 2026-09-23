import dataclasses
import typing
from datetime import date, datetime

from odoo.libs.collections import ReadonlyDict
from odoo.libs.func import lazy
from odoo.libs.json import (
    ScriptSafeJSON as JSON,
)
from odoo.libs.json import (
    dumps as fast_dumps,
)
from odoo.libs.json import (
    dumps_bytes as fast_dumps_bytes,
)
from odoo.libs.json import (
    fast_clone,
    scriptsafe,
)
from odoo.libs.json import (
    loads as fast_loads,
)

__all__ = [
    "JSON",
    "ReadonlyDict",
    "fast_clone",
    "fast_dumps",
    "fast_dumps_bytes",
    "fast_loads",
    "json_default",
    "lazy",
    "orjson_default",
    "scriptsafe",
]


_fields: typing.Any = None


def _odoo_fields() -> typing.Any:
    global _fields  # noqa: PLW0603  one-time lazy binding of a module that imports us
    if _fields is None:
        from odoo import fields

        _fields = fields
    return _fields


def _convert(obj: object) -> object:
    fields = _odoo_fields()

    if isinstance(obj, datetime):
        return fields.Datetime.to_string(obj)
    if isinstance(obj, date):
        return fields.Date.to_string(obj)
    if isinstance(obj, ReadonlyDict):
        return dict(obj)
    if isinstance(obj, bytes):
        return obj.decode()
    if isinstance(obj, fields.Domain):
        return list(obj)
    if dataclasses.is_dataclass(obj) and not isinstance(obj, type):
        return dataclasses.asdict(obj)
    return str(obj)


def json_default(obj: object) -> object:
    if isinstance(obj, lazy):
        return obj._value
    return _convert(obj)


# orjson hands whatever a default returns back to the encoder, which calls the
# default again for anything it cannot encode natively, so one policy serves both.
orjson_default = json_default
