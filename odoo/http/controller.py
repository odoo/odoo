import collections
import logging
from collections.abc import Collection, Generator, Iterable
from typing import TYPE_CHECKING, Any

from odoo.libs.debug_log import DebugLog

from .core import request

if TYPE_CHECKING:
    import odoo.api

_logger = logging.getLogger(__name__)
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


def _is_from_installed_addon(cls: type, modules: Collection[str]) -> bool:
    path = cls.__module__.split(".")
    return path[:2] == ["odoo", "addons"] and path[2] in modules


def _get_leaf_classes(cls: type, modules: Collection[str]) -> list[type]:
    result = []
    for subcls in cls.__subclasses__():
        if _is_from_installed_addon(subcls, modules):
            result.extend(_get_leaf_classes(subcls, modules))
    if not result and _is_from_installed_addon(cls, modules):
        result.append(cls)
    return _get_classes_newest_by_identity(result)


def _group_controller_trees(
    trees: Iterable[tuple[type, list[type]]],
) -> list[tuple[type, list[type]]]:
    groups: list[list[type]] = []
    tops: list[type] = []
    owner: dict[type, int] = {}

    for top_ctrl, leaves in trees:
        if not leaves:
            continue
        hits = sorted({owner[leaf] for leaf in leaves if leaf in owner})
        if hits:
            target, *also = hits
            for other in also:
                groups[target].extend(groups[other])
                groups[other] = []
            groups[target] = _get_classes_newest_by_identity([*groups[target], *leaves])
        else:
            target = len(groups)
            groups.append(list(leaves))
            tops.append(top_ctrl)
        for leaf in groups[target]:
            owner[leaf] = target

    _debug.pipeline(
        "http.controller.trees_grouped",
        trees=len(tops),
        groups=sum(1 for group in groups if group),
    )
    return [(tops[i], group) for i, group in enumerate(groups) if group]


def _get_controllers(modules: Collection[str]) -> Generator[Controller]:
    yield from (ctrl() for ctrl in Controller.children_classes.get("", []))

    highest_controllers = []
    for module in modules:
        highest_controllers.extend(Controller.children_classes.get(module, []))
    _debug.pipeline(
        "http.controller.roots",
        modules=len(modules),
        tops=len(highest_controllers),
        server_wide=len(Controller.children_classes.get("", [])),
    )

    trees = (
        (top_ctrl, _get_leaf_classes(top_ctrl, modules))
        for top_ctrl in highest_controllers
    )

    for top_ctrl, leaf_controllers in _group_controller_trees(trees):
        name = top_ctrl.__name__
        if leaf_controllers != [top_ctrl]:
            extended_by = ", ".join(
                bot_ctrl.__name__
                for bot_ctrl in leaf_controllers
                if bot_ctrl is not top_ctrl
            )
            name += f" (extended by {extended_by})"

        _debug.pipeline(
            "http.controller.assembled", controller=name, leaves=len(leaf_controllers)
        )
        try:
            Ctrl = type(name, tuple(reversed(leaf_controllers)), {})
        except TypeError:
            _debug.logic("http.controller.mro_conflict", controller=top_ctrl.__name__)
            _logger.error(
                "Cannot combine the controllers %s: they extend a shared base "
                "in incompatible orders, so no method resolution order exists "
                "for them. Their routes are not served. Make the base order "
                "agree between them. (%s)",
                ", ".join(f"{c.__module__}.{c.__qualname__}" for c in leaf_controllers),
                " / ".join(
                    f"{c.__name__}: {' -> '.join(b.__name__ for b in c.__mro__[:-2])}"
                    for c in leaf_controllers
                ),
            )
            continue
        yield Ctrl()
