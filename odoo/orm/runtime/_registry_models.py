import functools
import typing
from collections import deque
from collections.abc import Iterable, Iterator, Mapping
from operator import attrgetter

from odoo.libs.debug_log import DebugLog
from odoo.tools import OrderedSet

from ._registry_stubs import _RegistryStubs

if typing.TYPE_CHECKING:
    from odoo.models import BaseModel

    from ..fields import Field

_debug = DebugLog(__name__)


def index_model_names_by_inheritance_root(
    models: Mapping[str, type[BaseModel]],
) -> dict[str, tuple[str, ...]]:
    by_root: dict[str, list[str]] = {}
    for name, model_cls in models.items():
        root = model_cls._table_inheritance_root
        if root and not model_cls._abstract:
            by_root.setdefault(root, []).append(name)
    return {root: tuple(names) for root, names in by_root.items()}


class _RegistryModelsMixin(_RegistryStubs):
    __slots__ = ()

    models: dict[str, type[BaseModel]]

    def _init_models_container(self) -> None:
        self.models = {}

    def __len__(self) -> int:
        return len(self.models)

    def __iter__(self) -> Iterator[str]:
        return iter(self.models)

    def __getitem__(self, model_name: str) -> type[BaseModel]:
        return self.models[model_name]

    def __setitem__(self, model_name: str, model: type[BaseModel]) -> None:
        self.models[model_name] = model

    def __delitem__(self, model_name: str) -> None:
        del self.models[model_name]
        _debug.lifecycle("registry.model_removed", model=model_name)
        for Model in self.models.values():
            Model._inherit_children.discard(model_name)

    @functools.cached_property
    def models_by_table(self) -> dict[str, type[BaseModel]]:
        by_table: dict[str, type[BaseModel]] = {}
        for model_cls in self.models.values():
            table = getattr(model_cls, "_table", None)
            if not table:
                continue
            incumbent = by_table.get(table)
            if incumbent is None or model_cls._name in self._get_ancestors(incumbent):
                by_table[table] = model_cls
        _debug.perf.count(
            "registry.models_by_table_built",
            models=len(self.models),
            tables=len(by_table),
        )
        return by_table

    @functools.cached_property
    def model_names_by_inheritance_root(self) -> dict[str, tuple[str, ...]]:
        return index_model_names_by_inheritance_root(self.models)

    @functools.cached_property
    def _prefetch_fields_by_model(self) -> dict[str, tuple[tuple[Field, ...], bool]]:
        return {}

    def prefetch_fields(self, model_name: str) -> tuple[tuple[Field, ...], bool]:
        try:
            return self._prefetch_fields_by_model[model_name]
        except KeyError:
            fields = tuple(
                field
                for field in self.models[model_name]._fields.values()
                if field.prefetch is True
            )
            entry = (fields, any(field.groups for field in fields))
            self._prefetch_fields_by_model[model_name] = entry
            return entry

    def _get_ancestors(self, model_cls: type[BaseModel]) -> set[str]:
        seen: set[str] = set()
        queue = deque(getattr(model_cls, "_inherit", ()) or ())
        while queue:
            name = queue.popleft()
            if name in seen:
                continue
            seen.add(name)
            parent = self.models.get(name)
            if parent is not None:
                queue.extend(getattr(parent, "_inherit", ()) or ())
        return seen

    def get_descendants(
        self,
        model_names: Iterable[str],
        *kinds: typing.Literal["_inherit", "_inherits"],
    ) -> OrderedSet[str]:
        if not all(kind in ("_inherit", "_inherits") for kind in kinds):
            raise ValueError(
                f"descendants: kinds must be '_inherit'/'_inherits', got {kinds!r}"
            )
        funcs = [attrgetter(kind + "_children") for kind in kinds]

        models: OrderedSet[str] = OrderedSet()
        queue = deque(model_names)
        while queue:
            model = self.models.get(queue.popleft())
            if model is None or model._name in models:
                continue
            models.add(model._name)
            for func in funcs:
                queue.extend(func(model))
        return models
