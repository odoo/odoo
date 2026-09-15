import collections
from collections.abc import Iterable
from typing import TYPE_CHECKING, Any

from odoo.libs.debug_log import DebugLog

from .core import request

if TYPE_CHECKING:
    import odoo.api

_debug = DebugLog(__name__)


def _get_classes_newest_by_identity(classes: Iterable[type]) -> list[type]:
    by_key: dict[tuple[str, str], int] = {}
    result: list[type] = []
    for cls in classes:
        key = (cls.__module__, cls.__qualname__)
        idx = by_key.get(key)
        if idx is None:
            by_key[key] = len(result)
            result.append(cls)
        else:
            result[idx] = cls
    return result


class Controller:
    children_classes: collections.defaultdict[str, list[type[Controller]]] = (
        collections.defaultdict(list)
    )

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        if Controller in cls.__bases__:
            path = cls.__module__.split(".")
            module = path[2] if len(path) > 2 and path[:2] == ["odoo", "addons"] else ""
            bucket = Controller.children_classes[module]
            bucket[:] = _get_classes_newest_by_identity([*bucket, cls])
            _debug.lifecycle(
                "http.controller.registered",
                module=module or None,
                controller=cls.__qualname__,
                bucket=len(bucket),
            )

    @property
    def env(self) -> odoo.api.Environment | None:
        return request.env if request else None
