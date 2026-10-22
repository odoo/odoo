import json as _json
from collections.abc import Mapping
from datetime import date, datetime

from .binary import BinaryValue
from .func import lazy


class Simple:
    """ Simple namespace for basic str -> json and json -> str operations.
    Instances can be used to whitelist these two properties together, or as a
    safe "json module" to pass to untrusted code.
    """
    __slots__ = ()
    loads = staticmethod(_json.loads)
    dumps = staticmethod(_json.dumps)


simple = Simple()


def json_default(obj):
    from odoo import fields  # noqa: PLC0415
    if isinstance(obj, datetime):
        return fields.Datetime.to_string(obj)
    if isinstance(obj, date):
        return fields.Date.to_string(obj)
    if isinstance(obj, lazy):
        return obj._value
    if isinstance(obj, Mapping):
        return dict(obj)
    if isinstance(obj, bytes):
        return obj.decode()
    if isinstance(obj, BinaryValue):
        return obj.content.decode()
    if isinstance(obj, fields.Domain):
        return list(obj)
    if (as_dict_func := getattr(obj, 'as_dict', None)) and callable(as_dict_func):
        return as_dict_func()
    return str(obj)


def stringify_keys(obj):
    """Recursively convert mapping keys to strings.

    Webhook sample payloads may contain mappings with non-string keys,
    such as ``frozendict`` instances. Since ``json.dumps`` requires
    JSON-compatible mapping keys, such payloads must be normalized before
    serialization.
    """

    if isinstance(obj, Mapping):
        return {
            str(k): stringify_keys(v)
            for k, v in obj.items()
        }

    return obj
