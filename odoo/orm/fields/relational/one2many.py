import typing
from collections import defaultdict
from collections.abc import (
    Sequence,
)
from operator import attrgetter
from typing import override

from odoo.exceptions import AccessError, UserError
from odoo.libs.debug_log import DebugLog
from odoo.tools import SQL, OrderedSet, Query, unique
from odoo.tools.misc import SENTINEL, Sentinel

from ...domain import Domain
from ...primitives import SQL_OPERATORS, NewId
from ..base import Field
from ..reference import Many2oneReference
from ._base import _RelationalMulti
from ._commands import CommandDelta
from .many2one import Many2one

_debug = DebugLog(__name__)

if typing.TYPE_CHECKING:
    from odoo.tools.misc import Collector

    from ..._typing import (
        CommandValue,
        Environment,
        ModelLike,
        Registry,
    )
    from ...models import BaseModel


class One2many(_RelationalMulti):
    type = "one2many"
    is_one2many = True

    inverse_name: str | None = None
    copy: bool = False
    _inverse_is_computed: bool = False

    def __init__(
        self,
        comodel_name: str | Sentinel = SENTINEL,
        inverse_name: str | Sentinel = SENTINEL,
        string: str | Sentinel = SENTINEL,
        **kwargs: typing.Any,
    ) -> None:
        super().__init__(
            comodel_name=comodel_name,
            inverse_name=inverse_name,
            string=string,
            **kwargs,
        )

    def _get_inverse_name(self) -> str:
        if self.inverse_name is None:
            raise TypeError(
                f"{self} has no inverse_name, so the many2one on "
                f"{self.comodel_name} that carries it cannot be named"
            )
        return self.inverse_name

    @override
    def setup_nonrelated(self, model: BaseModel) -> None:
        super().setup_nonrelated(model)
        if self.inverse_name:
            comodel = model.env[self.comodel_name]
            try:
                field = comodel._fields[self.inverse_name]
                field.setup(comodel)
            except KeyError:
                raise ValueError(
                    f"{self.inverse_name!r} declared in {self!r} does not exist on {comodel._name!r}."
                ) from None
            self._inverse_is_computed = bool(field.compute)
            if _debug.logic.enabled and self._inverse_is_computed:
                _debug.logic(
                    "field.one2many.inverse_is_computed",
                    model=self.model_name,
                    field=self.name,
                    inverse=f"{self.comodel_name}.{self.inverse_name}",
                )

    @override
    def setup_inverses(
        self, registry: Registry, inverses: Collector[Field, Field]
    ) -> None:
        if self.inverse_name:
            invf = registry[self.comodel_name]._fields[self.inverse_name]
            if isinstance(invf, (Many2one, Many2oneReference)):
                inverses.add(self, invf)
            inverses.add(invf, self)

    _description_relation_field = property(attrgetter("inverse_name"))

    @override
    def update_db(
        self, model: ModelLike, columns: dict[str, dict[str, typing.Any]]
    ) -> bool:
        if self.comodel_name in model.env:
            comodel = model.env[self.comodel_name]
            if self.inverse_name not in comodel._fields:
                raise UserError(
                    model.env._(
                        'No inverse field "%(inverse_field)s" found for "%(comodel)s"',
                        inverse_field=self.inverse_name,
                        comodel=self.comodel_name,
                    )
                )
        return False

    def _get_domain_additional(self, env: Environment) -> Domain:
        if self.comodel_name and self.inverse_name:
            comodel = env.registry[self.comodel_name]
            inverse_field = comodel._fields[self._get_inverse_name()]
            if inverse_field.is_many2one_reference:
                return Domain(inverse_field.model_field, "=", self.model_name)
        return Domain.TRUE

    @override
    def get_comodel_domain(self, model: ModelLike) -> Domain:
        return super().get_comodel_domain(model) & self._get_domain_additional(
            model.env
        )

    @override
    def _internal_description_domain_raw(self, env: Environment) -> str | list:
        domain = super()._internal_description_domain_raw(env)
        additional_domain = self._get_domain_additional(env)
        if additional_domain.is_true():
            return domain
        return f"({domain}) + ({additional_domain})"

    @typing.overload
    def __get__(self, records: None, owner: typing.Any = None) -> typing.Self: ...
    @typing.overload
    def __get__(self, records: BaseModel, owner: typing.Any = None) -> BaseModel: ...
    @typing.overload
    def __get__(self, records: object, owner: typing.Any = None) -> typing.Any: ...

    @override
    def __get__(
        self, records: typing.Any, owner: typing.Any = None
    ) -> BaseModel | typing.Self:
        if records is not None and self._inverse_is_computed:
            records.env[self.comodel_name]._recompute_model([self.inverse_name])
        return super().__get__(records, owner)

    @override
    def read(self, records: BaseModel) -> None:
        comodel = records.env[self.comodel_name].with_context(
            **self._prepare_read_context()
        )
        inverse = self.inverse_name
        inverse_field = comodel._fields[inverse]

        domain = self.get_comodel_domain(records) & Domain(inverse, "in", records.ids)
        field_names = [inverse]
        if comodel._active_name:
            field_names.append(comodel._active_name)
        try:
            lines = comodel.search_fetch(domain, field_names)
        except AccessError as e:
            raise AccessError(
                records.env._("Failed to read field %s", self) + "\n" + str(e)
            ) from e

        inv_cache = inverse_field._get_cache(comodel.env)
        group = defaultdict(list)
        missed = []
        _SENTINEL = SENTINEL
        for line_id in lines._ids:
            value = inv_cache.get(line_id, _SENTINEL)
            if value is _SENTINEL:
                missed.append(line_id)
            else:
                group[value or False].append(line_id)

        if missed:
            _debug.logic(
                "field.one2many.read.inverse_cache_missed",
                model=self.model_name,
                field=self.name,
                lines=len(lines),
                missed=len(missed),
            )
            get_id = (lambda rec: rec.id) if inverse_field.is_many2one else int
            for line in lines.browse(missed):
                group[get_id(line[inverse])].append(line.id)
            position = {id_: index for index, id_ in enumerate(lines._ids)}
            for line_ids in group.values():
                line_ids.sort(key=position.__getitem__)

        values = [tuple(group[id_]) for id_ in records._ids]
        self._insert_cache(records, values)
        _debug.pipeline(
            "field.one2many.read",
            model=self.model_name,
            field=self.name,
            comodel=self.comodel_name,
            records=len(records),
            lines=len(lines),
        )

    def _write_nonstored_commands(
        self,
        records: BaseModel,
        records_commands_list: Sequence[tuple[BaseModel, list[CommandValue]]],
        comodel: BaseModel,
        browse_lines: typing.Callable[..., BaseModel],
        update_line: typing.Callable[..., None],
    ) -> None:

        def link(record, lines):
            ids = record[self.name]._ids
            self._update_cache(record, tuple(unique(ids + lines._ids)))

        def unlink(lines):
            for record in records:
                self._update_cache(record, (record[self.name] - lines)._ids)

        for recs, commands in records_commands_list:
            delta = CommandDelta.fold(commands)
            _debug.logic(
                "field.one2many.delta",
                model=self.model_name,
                field=self.name,
                stored=False,
                records=len(recs),
                created=len(delta.created),
                updated=len(delta.updated),
                removed=len(delta.removed),
                linked=len(delta.linked),
                replaced=delta.replaced,
            )
            if delta.replaced:
                self._update_cache(recs, ())
                self._update_cache(recs[-1], browse_lines(delta.set_ids)._ids)
            for ref, vals in delta.created:
                for record in recs:
                    link(record, comodel.new(vals, ref=ref))
            for line_id, vals in delta.updated:
                update_line(browse_lines([line_id]), vals)
            if delta.removed:
                unlink(browse_lines(list(delta.removed)))
            if delta.linked:
                link(recs[-1], browse_lines(list(delta.linked)))

    def _get_orphan_lines(self, comodel, model, recs, lines, inverse):
        domain = (
            self.get_comodel_domain(model)
            & Domain(inverse, "in", recs.ids)
            & Domain("id", "not in", lines.ids)
        )
        orphans = comodel.with_context(active_test=False).search(  # noqa: E8507  see above
            domain
        )
        _debug.logic(
            "field.one2many.orphans_found",
            model=self.model_name,
            field=self.name,
            records=len(recs),
            orphans=len(orphans),
        )
        return orphans

    def _write_real_stored(
        self, records_commands_list, model, comodel, create: bool
    ) -> None:
        inverse = self.inverse_name
        inverse_field = comodel._fields[inverse]
        reference_model_field = (
            inverse_field.model_field if inverse_field.is_many2one_reference else None
        )
        to_create: list[dict] = []
        to_delete: list = []
        to_link: defaultdict[typing.Any, OrderedSet] = defaultdict(OrderedSet)
        allow_full_delete = not create

        def unlink(lines):
            cascade = getattr(comodel._fields[inverse], "ondelete", False) == "cascade"
            _debug.logic(
                "field.one2many.unlink_strategy",
                model=self.model_name,
                field=self.name,
                strategy="delete" if cascade else "detach",
                lines=len(lines),
            )
            if cascade:
                to_delete.extend(lines._ids)
            else:
                lines[inverse] = False

        def flush():
            _debug.pipeline(
                "field.one2many.flush",
                model=self.model_name,
                field=self.name,
                to_delete=len(to_delete),
                to_create=len(to_create),
                to_link=sum(len(ids) for ids in to_link.values()),
            )
            if to_link:
                before = {record: record[self.name] for record in to_link}
            if to_delete:
                comodel.browse(to_delete).unlink()
                to_delete.clear()
            if to_create:
                comodel.create(to_create)
                to_create.clear()
            if to_link:
                for record, line_ids in to_link.items():
                    lines = comodel.browse(line_ids) - before[record]
                    lines.mapped(inverse)
                    lines[inverse] = record
                    if reference_model_field:
                        lines[reference_model_field] = model._name
                to_link.clear()

        for recs, commands in records_commands_list:
            delta = CommandDelta.fold(commands, superseding=allow_full_delete)
            _debug.logic(
                "field.one2many.delta",
                model=self.model_name,
                field=self.name,
                stored=True,
                records=len(recs),
                created=len(delta.created),
                updated=len(delta.updated),
                deleted=len(delta.deleted),
                unlinked=len(delta.unlinked),
                linked=len(delta.linked),
                replaced=delta.replaced,
            )
            for line_id, vals in delta.updated:
                prefetch_ids = recs[self.name]._prefetch_ids
                comodel.browse(line_id).with_prefetch(prefetch_ids).write(vals)
            to_delete.extend(delta.deleted)
            if delta.unlinked:
                unlink(comodel.browse(list(delta.unlinked)))
            if delta.replaced:
                if not allow_full_delete:
                    if delta.set_ids:
                        to_link[recs[-1]].update(delta.set_ids)
                else:
                    flush()
                    lines = comodel.browse(delta.set_ids)
                    unlink(self._get_orphan_lines(comodel, model, recs, lines, inverse))
                    lines[inverse] = recs[-1]
            for _ref, vals in delta.created:
                line_vals = dict(vals)
                if reference_model_field:
                    line_vals[reference_model_field] = model._name
                to_create.extend({**line_vals, inverse: record.id} for record in recs)
            if delta.linked:
                to_link[recs[-1]].update(delta.linked)

        flush()

    def _write_real_unstored(self, records_commands_list, comodel) -> None:
        ids = OrderedSet(rid for recs, cs in records_commands_list for rid in recs._ids)
        records = records_commands_list[0][0].browse(ids)
        self._write_nonstored_commands(
            records,
            records_commands_list,
            comodel,
            comodel.browse,
            lambda lines, vals: lines.write(vals),
        )

    @override
    def write_real(
        self,
        records_commands_list: Sequence[tuple[BaseModel, list[CommandValue]]],
        create: bool = False,
    ) -> None:
        if not records_commands_list:
            return

        model, comodel = self._get_writer_models(records_commands_list)

        _debug.pipeline(
            "field.one2many.write_real",
            model=model._name,
            field=self.name,
            comodel=comodel._name,
            stored=self.store,
            create=create,
            groups=len(records_commands_list),
        )
        if self.store:
            self._write_real_stored(records_commands_list, model, comodel, create)
        else:
            self._write_real_unstored(records_commands_list, comodel)

    @override
    def write_new(
        self,
        records_commands_list: Sequence[tuple[BaseModel, list[CommandValue]]],
    ) -> None:
        if not records_commands_list:
            return

        model, comodel = self._get_writer_models(records_commands_list)

        ids = {record.id for records, _ in records_commands_list for record in records}
        records = model.browse(ids)
        _debug.pipeline(
            "field.one2many.write_new",
            model=model._name,
            field=self.name,
            comodel=comodel._name,
            stored=self.store,
            records=len(records),
            groups=len(records_commands_list),
        )

        def browse(ids):
            return comodel.browse([id_ and NewId(id_) for id_ in ids])

        records[self.name]

        if self.store:
            inverse = self._get_inverse_name()

            inverse_field = comodel._fields[inverse]
            for record in records:
                inverse_field._update_cache(record[self.name], record.id)

            for recs, commands in records_commands_list:
                delta = CommandDelta.fold(commands, lambda id_: id_ and NewId(id_))
                if delta.replaced:
                    last, lines = recs[-1], comodel.browse(delta.set_ids)
                    for record in recs:
                        if removed := record[self.name] - lines:
                            removed[inverse] = False
                    self._update_cache(recs, ())
                    self._update_cache(last, lines._ids)
                    inverse_field._update_cache(lines, last.id)
                for ref, vals in delta.created:
                    for record in recs:
                        line = comodel.new(vals, ref=ref)
                        line[inverse] = record
                for line_id, vals in delta.updated:
                    comodel.browse([line_id]).update(vals)
                if delta.removed:
                    comodel.browse(list(delta.removed))[inverse] = False
                if delta.linked:
                    comodel.browse(list(delta.linked))[inverse] = recs[-1]

        else:
            self._write_nonstored_commands(
                records,
                records_commands_list,
                comodel,
                browse,
                lambda lines, vals: lines.update(vals),
            )

    @override
    def _get_query_for_condition_value(
        self,
        model: BaseModel,
        comodel: BaseModel,
        operator: str,
        value: Domain | Query,
    ) -> Query:
        inverse_field = comodel._fields[self._get_inverse_name()]
        if inverse_field not in comodel.env.registry.not_null_fields:
            _debug.logic(
                "field.one2many.inverse_not_null_added",
                model=model._name,
                field=self.name,
                inverse=f"{comodel._name}.{inverse_field.name}",
                value_kind="domain" if isinstance(value, Domain) else "query",
            )
            if isinstance(value, Domain):
                value &= Domain(inverse_field.name, "not in", {False})
            else:
                coquery = super()._get_query_for_condition_value(
                    model, comodel, operator, value
                )
                coquery.add_where(
                    SQL(
                        "%s IS NOT NULL",
                        comodel._field_to_sql(
                            coquery.table, inverse_field.name, coquery
                        ),
                    )
                )
                return coquery
        return super()._get_query_for_condition_value(model, comodel, operator, value)

    @override
    def _condition_to_sql_relational(
        self,
        model: BaseModel,
        alias: str,
        exists: bool,
        coquery: Query,
        query: Query,
    ) -> SQL:
        if coquery.is_empty():
            _debug.logic(
                "field.one2many.condition_strategy",
                model=model._name,
                field=self.name,
                strategy="empty_subquery",
                exists=exists,
            )
            return Domain(not exists)._to_sql(model, alias, query)

        comodel = model.env[self.comodel_name].sudo()
        inverse_field = comodel._fields[self.inverse_name]
        _debug.logic(
            "field.one2many.condition_strategy",
            model=model._name,
            field=self.name,
            strategy="exists" if inverse_field.store else "unstored_inverse_in_memory",
            exists=exists,
        )
        if not inverse_field.store:
            recs = comodel.browse(coquery).with_context(prefetch_fields=False)
            if inverse_field.relational:
                inverses = inverse_field.__get__(recs)
            else:
                inverses = model.browse(inverse_field.__get__(rec) for rec in recs)
            subselect = inverses._as_query(ordered=False).subselect()
            return SQL(
                "%s%s%s",
                SQL.identifier(alias, "id"),
                SQL_OPERATORS["in" if exists else "not in"],
                subselect,
            )

        subselect = coquery.subselect(
            SQL(
                "%s AS __inverse",
                comodel._field_to_sql(coquery.table, inverse_field.name, coquery),
            )
        )
        return SQL(
            "%sEXISTS(SELECT FROM %s AS __sub WHERE __inverse = %s)",
            SQL.EMPTY if exists else SQL("NOT "),
            subselect,
            SQL.identifier(alias, "id"),
        )
