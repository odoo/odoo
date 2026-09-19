import functools
import logging
import typing
import warnings
from collections import defaultdict
from collections.abc import Callable, Iterator

from odoo.libs.debug_log import DebugLog
from odoo.libs.func import locked
from odoo.tools import OrderedSet
from odoo.tools.misc import Collector

from ..components.model_graph import ModelGraph, TriggerTree
from ..parsing import regex_order
from ._registry_stubs import _RegistryStubs

if typing.TYPE_CHECKING:
    from odoo.fields import Field

    from .registry import Registry


_logger = logging.getLogger("odoo.registry")
_debug = DebugLog(__name__)
_schema = logging.getLogger("odoo.schema")


class _RegistryFieldsMixin(_RegistryStubs):
    model_graph: ModelGraph
    field_setup_dependents: Collector[Field, Field]
    many2one_company_dependents: Collector[str, Field]
    many2many_relations: defaultdict[tuple[str, str, str], OrderedSet]

    def _init_field_state(self) -> None:
        self.model_graph = ModelGraph()
        self.field_setup_dependents = Collector()
        self.many2one_company_dependents = Collector()
        self.many2many_relations = defaultdict(OrderedSet)

    def _publish_field_metadata(self) -> tuple:
        return self.field_inverses, self.field_computed

    def _get_field_triggers(self) -> dict:
        refused_at = self.__dict__.get("_field_triggers_refused_at")
        if refused_at is not None and refused_at != self.model_graph.trigger_epoch:
            _debug.logic(
                "registry.field_triggers.refused_rebuilt",
                refused_at=refused_at,
                epoch=self.model_graph.trigger_epoch,
            )
            self.__dict__.pop("_field_triggers", None)
            self.__dict__.pop("_field_triggers_refused_at", None)
        return self._field_triggers

    @property
    def field_depends(self) -> typing.Any:
        return self.model_graph.field_depends

    @property
    def field_depends_context(self) -> typing.Any:
        return self.model_graph.field_depends_context

    @functools.cached_property
    def field_inverses(self) -> Collector[Field, Field]:
        result: Collector[Field, Field] = Collector()
        for model_cls in self.models.values():
            for field in model_cls._fields.values():
                if field.relational:
                    field.setup_inverses(self, result)
        self.model_graph.set_inverses(result)
        _debug.perf.count(
            "registry.field_inverses_built",
            models=len(self.models),
            fields=len(result),
        )
        return result

    @functools.cached_property
    def order_key_inverses(self) -> dict[Field, tuple[Field, ...]]:
        field_inverses = self.field_inverses
        result: dict[Field, tuple[Field, ...]] = {}
        for model_cls in self.models.values():
            fields = model_cls._fields
            many2ones = tuple(
                field
                for field in fields.values()
                if field.is_many2one
                and any(invf.is_one2many for invf in field_inverses[field])
            )
            order = model_cls._order
            if not many2ones or not isinstance(order, str):
                continue
            for part in order.split(","):
                match = regex_order.match(part)
                if not match or match["property"] or match["field"] == "id":
                    continue
                if (field := fields.get(match["field"])) is not None:
                    result[field] = many2ones
        _debug.perf.count("registry.order_key_inverses_built", fields=len(result))
        return result

    @functools.cached_property
    def fields_by_comodel(self) -> dict[str, tuple[Field, ...]]:
        result: defaultdict[str, list[Field]] = defaultdict(list)
        for model_cls in self.models.values():
            for field in model_cls._fields.values():
                if field.relational and field.comodel_name:
                    result[field.comodel_name].append(field)
        _debug.perf.count(
            "registry.fields_by_comodel_built",
            comodels=len(result),
            fields=sum(len(fields) for fields in result.values()),
        )
        return {name: tuple(fields) for name, fields in result.items()}

    @functools.cached_property
    def fields_reading_through_a_reference(self) -> tuple[Field, ...]:
        result: list[Field] = []
        for model_cls in self.models.values():
            fields = model_cls._fields
            for field in fields.values():
                if field.store or not field.compute:
                    continue
                if any(
                    "." not in dep
                    and (dep_field := fields.get(dep)) is not None
                    and dep_field.type in ("many2one_reference", "reference")
                    for dep in self.field_depends.get(field, ())
                ):
                    result.append(field)
        _debug.perf.count(
            "registry.fields_reading_through_a_reference", fields=len(result)
        )
        return tuple(result)

    @functools.cached_property
    def models_cascading_from(self) -> dict[str, frozenset[str]]:
        result: defaultdict[str, set[str]] = defaultdict(set)
        for model_cls in self.models.values():
            for field in model_cls._fields.values():
                if (
                    field.is_many2one
                    and field.store
                    and field.comodel_name
                    and getattr(field, "ondelete", None) == "cascade"
                ):
                    result[field.comodel_name].add(field.model_name)
        _debug.perf.count(
            "registry.models_cascading_from_built",
            targets=len(result),
            edges=sum(len(models) for models in result.values()),
        )
        return {name: frozenset(models) for name, models in result.items()}

    @functools.cached_property
    def field_computed(self) -> dict[Field, list[Field]]:
        computed: dict[Field, list[Field]] = {}
        _debug.pipeline("registry.field_computed.begin", models=len(self.models))
        for model_name, Model in self.models.items():
            groups: defaultdict[Field, list[Field]] = defaultdict(list)
            for field in Model._fields.values():
                if field.compute:
                    compute_key = typing.cast("Field", field.compute)
                    computed[field] = group = groups[compute_key]
                    group.append(field)
            for fields in groups.values():
                if len(fields) < 2:
                    continue
                if len({field.compute_sudo for field in fields}) > 1:
                    fnames = ", ".join(field.name for field in fields)
                    warnings.warn(
                        f"{model_name}: inconsistent 'compute_sudo' for computed fields {fnames}. "
                        f"Either set 'compute_sudo' to the same value on all those fields, or "
                        f"use distinct compute methods for sudoed and non-sudoed fields.",
                        stacklevel=1,
                    )
                if len({field.precompute for field in fields}) > 1:
                    fnames = ", ".join(field.name for field in fields)
                    warnings.warn(
                        f"{model_name}: inconsistent 'precompute' for computed fields {fnames}. "
                        f"Either set all fields as precompute=True (if possible), or "
                        f"use distinct compute methods for precomputed and non-precomputed fields.",
                        stacklevel=1,
                    )
                if len({field.store for field in fields}) > 1:
                    fnames1 = ", ".join(
                        field.name for field in fields if not field.store
                    )
                    fnames2 = ", ".join(field.name for field in fields if field.store)
                    warnings.warn(
                        f"{model_name}: inconsistent 'store' for computed fields, "
                        f"accessing {fnames1} may recompute and update {fnames2}. "
                        f"Use distinct compute methods for stored and non-stored fields.",
                        stacklevel=1,
                    )
        self.model_graph.set_computed(computed)
        _debug.pipeline("registry.field_computed.end", fields=len(computed))
        return computed

    def get_trigger_tree(
        self, fields: list[Field], select: Callable[[Field], bool] = bool
    ) -> TriggerTree:
        self._get_field_triggers()
        return self.model_graph.get_trigger_tree(fields, select)

    def get_dependent_fields(self, field: Field) -> Iterator[Field]:
        self._get_field_triggers()
        return self.model_graph.get_dependent_fields(field)

    @locked
    def discard_fields(self, fields: list[Field]) -> None:
        _debug.lifecycle("registry.fields_discarded", fields=len(fields))
        self.model_graph.begin_invalidation()
        try:
            for f in fields:
                self.field_depends.pop(f, None)

            self.field_setup_dependents.discard_keys_and_values(fields)

            for f in fields:
                if f.is_many2many and f.relation and f.column1 and f.column2:
                    triple = (f.relation, f.column1, f.column2)
                    pairs = self.many2many_relations.get(triple)
                    if pairs is not None:
                        pairs.discard((f.model_name, f.name))
                        if not pairs:
                            del self.many2many_relations[triple]

            for _prop in (
                "_field_triggers",
                "field_inverses",
                "order_key_inverses",
                "field_computed",
                "fields_by_comodel",
                "fields_reading_through_a_reference",
                "models_cascading_from",
                "_prefetch_fields_by_model",
            ):
                self.__dict__.pop(_prop, None)

            self.model_graph.discard_fields(fields)
        finally:
            self.model_graph.end_invalidation()

    def get_field_trigger_tree(self, field: Field) -> TriggerTree:
        self._get_field_triggers()
        return self.model_graph.get_field_trigger_tree(field)

    @functools.cached_property
    def _field_triggers(self) -> dict:
        with _debug.perf("registry.field_triggers", models=len(self.models)) as span:
            graph = self.model_graph
            start_epoch = graph.trigger_epoch
            new_triggers: defaultdict = defaultdict(lambda: defaultdict(list))
            self._link_tree_siblings()
            for Model in self.models.values():
                if Model._abstract:
                    continue
                for field in Model._fields.values():
                    try:
                        dependencies = list(
                            field.resolve_depends(typing.cast("Registry", self))
                        )
                    except Exception as e:
                        if not field.base_field.manual:
                            raise
                        _logger.info(
                            "Could not resolve dependencies of manual field %s.%s; "
                            "ignoring them (%s: %s)",
                            field.model_name,
                            field.name,
                            type(e).__name__,
                            e,
                        )
                    else:
                        for dependency in dependencies:
                            *path, dep_field = dependency
                            key = tuple(reversed(path))
                            for actual in self._depended_fields_in_tree(dep_field):
                                bucket = new_triggers[actual][key]
                                if field not in bucket:
                                    bucket.append(field)

            span.set(
                triggered_fields=len(new_triggers),
                inheritance_trees=len(self.model_names_by_inheritance_root),
            )
            if not graph.set_triggers(
                new_triggers, epoch=start_epoch, fact_of=self._trigger_fact_of
            ):
                self.__dict__["_field_triggers_refused_at"] = graph.trigger_epoch
                span.set(published=False)
                return graph.published_triggers

            self.__dict__.pop("_field_triggers_refused_at", None)

            self._publish_field_metadata()

            graph.freeze()

            span.set(published=True)
            return graph.published_triggers

    def _link_tree_siblings(self) -> None:
        for names in self.model_names_by_inheritance_root.values():
            models = [self.models[name] for name in names]
            for model_cls in models:
                for fname, field in model_cls._fields.items():
                    field.tree_siblings = tuple(
                        other._fields[fname]
                        for other in models
                        if other is not model_cls and fname in other._fields
                    )

    def _trigger_fact_of(self, field: Field) -> Field | tuple[str, str]:
        model_cls = self.models.get(field.model_name)
        root = getattr(model_cls, "_table_inheritance_root", "")
        if not root:
            return field
        for name in self.model_names_by_inheritance_root.get(root, ()):
            other = self.models[name]
            if other._table == root and field.name in other._fields:
                return (root, field.name)
        return field

    def _depended_fields_in_tree(self, dep_field: Field) -> tuple[Field, ...]:
        model_cls = self.models.get(dep_field.model_name)
        if model_cls is None:
            return (dep_field,)
        root = getattr(model_cls, "_table_inheritance_root", "")
        if not root or model_cls._table != root:
            return (dep_field,)
        found = [dep_field]
        for name in self.model_names_by_inheritance_root.get(root, ()):
            other = self.models[name]
            if other._table != root and dep_field.name in other._fields:
                found.append(other._fields[dep_field.name])
        if len(found) > 1:
            _debug.logic(
                "registry.field_triggers.tree_expanded",
                field=f"{dep_field.model_name}.{dep_field.name}",
                models=len(found),
            )
        return tuple(found)

    def is_modifying_relations(self, field: Field) -> bool:
        self._get_field_triggers()
        return self.model_graph.is_modifying_relations(field)
