import typing
from typing import override

from odoo.libs.debug_log import DebugLog
from odoo.tools.misc import SENTINEL, Sentinel

from .._recordset import is_recordset, is_search_overridden
from ..domain import Domain
from .numeric import Integer

if typing.TYPE_CHECKING:
    from .._typing import BaseModel, ModelClass

COUNTABLE_TYPES = ("one2many", "many2many")

_debug = DebugLog(__name__)


class Count(Integer):
    count_of: str = ""

    counts_in_database: bool = False

    def __init__(
        self,
        count_of: str | Sentinel = SENTINEL,
        string: str | Sentinel = SENTINEL,
        **kwargs: typing.Any,
    ) -> None:
        super().__init__(
            count_of=count_of,
            string=string,
            compute=self._compute_count,
            **kwargs,
        )

    @override
    def _get_attrs(self, model_class: ModelClass, name: str) -> dict[str, typing.Any]:
        attrs = super()._get_attrs(model_class, name)
        if attrs.get("inherited"):
            attrs.pop("compute", None)
            attrs.pop("_depends", None)
            return attrs
        if attrs.get("related"):
            raise TypeError(
                f"Field {model_class._name}.{name}: a Count cannot be related; "
                f"count_of names a field on this model."
            )
        count_of = attrs.get("count_of") or self.count_of
        if not count_of:
            raise TypeError(
                f"Field {model_class._name}.{name}: Count requires count_of."
            )
        attrs.setdefault("_depends", (count_of,))
        return attrs

    @override
    def setup_nonrelated(self, model: BaseModel) -> None:
        super().setup_nonrelated(model)
        try:
            counted = self._get_counted_field(model)
        except KeyError:
            if model._abstract:
                return
            raise ValueError(
                f"{self.count_of!r} declared in {self!r} does not exist on "
                f"{model._name!r}."
            ) from None
        counted.setup(model)
        if counted.type not in COUNTABLE_TYPES:
            raise TypeError(
                f"{self}: count_of={self.count_of!r} is a {counted.type} field; "
                f"a Count counts a one2many or a many2many."
            )
        self.counts_in_database = self._can_count_in_database(model, counted)

        comodel = model.env[counted.comodel_name]
        if (
            self._depends_context is None
            and not self.store
            and comodel._active_name
            and "active_test" not in counted.context
        ):
            self._depends_context = ("active_test",)
        _debug.logic(
            "field.count.setup",
            model=self.model_name,
            field=self.name,
            count_of=self.count_of,
            in_database=self.counts_in_database,
            depends_context=self._depends_context,
        )

    @override
    def get_depends(
        self, model: BaseModel
    ) -> tuple[typing.Iterable[str], typing.Iterable[str]]:
        depends, depends_context = super().get_depends(model)
        if self.inherited or not self.count_of:
            return depends, depends_context
        counted: typing.Any = model._fields.get(self.count_of)
        if counted is None:
            return depends, depends_context
        comodel = model.env[counted.comodel_name]

        if not counted.store:
            return depends, depends_context

        paths: list[str] = []
        domain = counted.domain
        if domain and not callable(domain) and not isinstance(domain, str):
            paths.extend(
                condition.field_expr for condition in Domain(domain).iter_conditions()
            )
        if comodel._active_name and counted.context.get("active_test", True):
            paths.append(comodel._active_name)
        if paths:
            mirror = self._get_mirror_field_name(counted, comodel)
            if mirror:
                paths.insert(0, mirror)

        extra = []
        for path in paths:
            head = path.split(".", 1)[0]
            if head == "id" or head not in comodel._fields:
                continue
            dotted = f"{self.count_of}.{path}"
            if dotted not in depends and dotted not in extra:
                extra.append(dotted)
        return (*depends, *extra), depends_context

    @staticmethod
    def _get_mirror_field_name(counted: typing.Any, comodel: BaseModel) -> str | None:
        if not counted.is_many2many:
            return None
        relation, column1, column2 = counted.relation, counted.column1, counted.column2
        if not (relation and column1 and column2):
            return None
        for name, field in comodel._fields.items():
            if (
                field.is_many2many
                and field.relation == relation
                and field.column1 == column2
                and field.column2 == column1
            ):
                return name
        return None

    def _get_counted_field(self, model: BaseModel) -> typing.Any:
        return model._fields[self.count_of]

    def _can_count_in_database(self, model: BaseModel, counted: typing.Any) -> bool:
        if counted.compute and not counted.store:
            return False
        if counted.is_one2many:
            inverse_name = counted.inverse_name
            if not inverse_name:
                return False
            comodel = model.env[counted.comodel_name]
            inverse = comodel._fields.get(inverse_name)
            return bool(inverse is not None and inverse.store)
        return bool(counted.relation and counted.column1 and counted.column2)

    def _compute_count(self, records: BaseModel) -> None:
        counted = self._get_counted_field(records)
        name = counted.name
        counts: dict[typing.Any, int] = {}
        pending: list[int] = []
        if self.counts_in_database:
            cached = counted._get_cache(records.env)
            pending = [
                record.id
                for record in records
                if isinstance(record.id, int) and record.id not in cached
            ]
        if pending:
            counts = self._count_in_database(records.browse(pending))
        _debug.logic(
            "field.count.computed",
            model=self.model_name,
            field=self.name,
            records=len(records),
            from_database=len(counts),
        )
        for record in records:
            id_ = record.id
            if id_ in counts:
                record[self.name] = counts[id_]
            else:
                record[self.name] = len(record[name])

    def _count_in_database(self, records: BaseModel) -> dict[typing.Any, int]:
        counted = self._get_counted_field(records)
        env = records.env
        Comodel = env.registry[counted.comodel_name]
        active_test = counted.context.get(
            "active_test", env.context.get("active_test", True)
        )
        context = dict(counted.context)
        context["active_test"] = bool(Comodel._active_name and active_test)
        comodel = env[counted.comodel_name].with_context(**context)
        domain = counted.get_comodel_domain(records)
        result: dict[typing.Any, int] = dict.fromkeys(records.ids, 0)

        if counted.is_one2many:
            inverse_name = counted.inverse_name
            with _debug.perf(
                "field.count.query",
                cr=env.cr,
                model=self.model_name,
                field=self.name,
                kind="one2many",
                records=len(records),
            ):
                groups = comodel._read_group(
                    domain & Domain(inverse_name, "in", records.ids),
                    [inverse_name],
                    ["__count"],
                )
            for key, count in groups:
                result[key.id if is_recordset(key) else key] = count
            return result

        bypass_access = counted.bypass_search_access and is_search_overridden(
            type(comodel)
        )
        with _debug.perf(
            "field.count.query",
            cr=env.cr,
            model=self.model_name,
            field=self.name,
            kind="many2many",
            records=len(records),
            bypass_access=bypass_access,
        ):
            query = comodel._search(domain, bypass_access=bypass_access)
            # the pairs a pending write would add or drop, as the statement's
            # to_flush did before the count went through the port
            records.flush_recordset([counted.name])
            relation, column1, column2 = counted._get_relation_columns()
            result.update(
                env.backend.count_m2m_groups(records, relation, column1, column2, query)
            )
        return result
