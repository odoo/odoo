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

_CASCADE_PATH_MAX_MODELS = 4


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
    def cascades_into_inheritance_trees(self) -> dict[str, tuple[tuple[str, str], ...]]:
        referrers: dict[str, list[tuple[str, str]]] = {}
        for root_table, names in self.model_names_by_inheritance_root.items():
            root_fields: Mapping[str, Field] = next(
                (
                    self.models[name]._fields
                    for name in names
                    if self.models[name]._table == root_table
                ),
                {},
            )
            for name in names:
                model_cls = self.models[name]
                for field in model_cls._fields.values():
                    if (
                        field.is_many2one
                        and field.store
                        and field.column_type
                        and field.ondelete == "cascade"
                        and field.comodel_name
                        and (
                            model_cls._table == root_table
                            or field.name not in root_fields
                        )
                    ):
                        referrers.setdefault(field.comodel_name, []).append(
                            (name, field.name)
                        )
        self._extend_cascades_through_plain_models(referrers)
        return {comodel: tuple(sorted(pairs)) for comodel, pairs in referrers.items()}

    def _extend_cascades_through_plain_models(
        self, referrers: dict[str, list[tuple[str, str]]]
    ) -> None:
        in_trees = {
            name
            for names in self.model_names_by_inheritance_root.values()
            for name in names
        }
        frontier: list[tuple[str, str, str, tuple[str, ...]]] = [
            (comodel, leaf, path, (comodel,))
            for comodel, pairs in referrers.items()
            for leaf, path in pairs
        ]
        while frontier:
            comodel, leaf, path, trail = frontier.pop()
            model_cls = self.models.get(comodel)
            if (
                model_cls is None
                or comodel in in_trees
                or model_cls._abstract
                or len(trail) > _CASCADE_PATH_MAX_MODELS
            ):
                continue
            for field in model_cls._fields.values():
                if (
                    field.is_many2one
                    and field.store
                    and field.column_type
                    and field.ondelete == "cascade"
                    and field.comodel_name
                    and field.comodel_name not in trail
                ):
                    longer = f"{path}.{field.name}"
                    referrers.setdefault(field.comodel_name, []).append((leaf, longer))
                    frontier.append(
                        (field.comodel_name, leaf, longer, (*trail, field.comodel_name))
                    )

    @functools.cached_property
    def _prefetch_fields_by_model(
        self,
    ) -> dict[tuple[str, typing.Any], tuple[Field, ...]]:
        return {}

    def prefetch_fields(
        self, model_name: str, prefetch: typing.Any = True
    ) -> tuple[Field, ...]:
        key = (model_name, prefetch)
        try:
            return self._prefetch_fields_by_model[key]
        except KeyError:
            fields = tuple(
                field
                for field in self.models[model_name]._fields.values()
                if field.prefetch == prefetch
            )
            self._prefetch_fields_by_model[key] = fields
            return fields

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
