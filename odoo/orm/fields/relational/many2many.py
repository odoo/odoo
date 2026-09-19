import itertools
import typing
from collections import defaultdict
from collections.abc import (
    Sequence,
)
from typing import override

from odoo.exceptions import AccessError
from odoo.libs.debug_log import DebugLog
from odoo.tools import SQL, OrderedSet, Query, unique
from odoo.tools.misc import PENDING, SENTINEL, Sentinel

from ..._recordset import is_search_overridden
from ...primitives import NewId
from ...validation import check_pg_name
from .. import _field_ddl as _ddl
from ..base import Field
from ._base import _is_cache_order_stable, _RelationalMulti
from ._commands import CommandDelta

_debug = DebugLog(__name__)

if typing.TYPE_CHECKING:
    from odoo.tools.misc import Collector

    from ..._typing import (
        CommandValue,
        ModelLike,
        Registry,
    )
    from ...models import BaseModel

    OnDelete = typing.Literal["cascade", "set null", "restrict"]


def _remove_from_relations(old_relation: dict, new_relation: dict, ys) -> None:
    for ys1 in old_relation.values():
        ys1 -= ys
    for ys1 in new_relation.values():
        ys1 -= ys


class Many2many(_RelationalMulti):
    type = "many2many"
    is_many2many = True

    _explicit: bool = True
    relation: str | None = None
    column1: str | None = None
    column2: str | None = None
    ondelete: OnDelete | None = "cascade"

    def __init__(
        self,
        comodel_name: str | Sentinel = SENTINEL,
        relation: str | Sentinel = SENTINEL,
        column1: str | Sentinel = SENTINEL,
        column2: str | Sentinel = SENTINEL,
        string: str | Sentinel = SENTINEL,
        **kwargs: typing.Any,
    ) -> None:
        super().__init__(
            comodel_name=comodel_name,
            relation=relation,
            column1=column1,
            column2=column2,
            string=string,
            **kwargs,
        )

    def _get_relation_columns(self) -> tuple[str, str, str]:
        relation, column1, column2 = self.relation, self.column1, self.column2
        assert relation and column1 and column2, (
            f"{self}: row I/O before setup resolved the relation table"
        )
        return relation, column1, column2

    @override
    def setup_nonrelated(self, model: BaseModel) -> None:
        super().setup_nonrelated(model)
        if self.ondelete not in ("cascade", "restrict"):
            raise ValueError(
                f"The m2m field {self.name} of model {model._name} declares its ondelete policy "
                f"as being {self.ondelete!r}. Only 'restrict' and 'cascade' make sense."
            )
        if self.store:
            if not (self.relation and self.column1 and self.column2):
                if not self.relation:
                    self._explicit = False
                comodel = model.env[self.comodel_name]
                if not self.relation:
                    tables = sorted([model._table, comodel._table])
                    assert tables[0] != tables[1], (
                        f"{self}: Implicit/canonical naming of many2many relationship "
                        "table is not possible when source and destination models "
                        "are the same"
                    )
                    self.relation = f"{tables[0]}_{tables[1]}_rel"
                if not self.column1:
                    self.column1 = f"{model._table}_id"
                if not self.column2:
                    self.column2 = f"{comodel._table}_id"
                _debug.logic(
                    "field.many2many.relation_defaulted",
                    model=self.model_name,
                    field=self.name,
                    relation=self.relation,
                    column1=self.column1,
                    column2=self.column2,
                    explicit=self._explicit,
                )
            check_pg_name(self.relation)
        else:
            self.relation = self.column1 = self.column2 = None

        if self.relation:
            fields = model.pool.many2many_relations[self._get_relation_triple()]
            for mname, fname in fields:
                field = model.pool[mname]._fields[fname]
                if (
                    (field is self)
                    or (
                        self.model_name == field.model_name
                        and self.comodel_name == field.comodel_name
                        and self._explicit
                        and field._explicit
                    )
                    or (
                        self.model_name != field.model_name
                        and not (model._auto and model.env[field.model_name]._auto)
                    )
                    or self._shares_inheritance_tree(model, field)
                ):
                    continue
                raise TypeError(
                    f"Many2many fields {self} and {field} use the same table and columns"
                )
            fields.add((self.model_name, self.name))

    def _shares_inheritance_tree(self, model, field) -> bool:
        if self.comodel_name != field.comodel_name:
            return False
        root = model._table_inheritance_root
        shared = (
            bool(root) and root == model.env[field.model_name]._table_inheritance_root
        )
        if shared:
            _debug.logic(
                "field.many2many.relation_shared_in_tree",
                relation=self.relation,
                models=(self.model_name, field.model_name),
            )
        return shared

    def _get_relation_triple(self) -> tuple[str, str, str]:
        if not (self.relation and self.column1 and self.column2):
            raise TypeError(
                f"{self} has no relation table: the three of relation, column1 and "
                f"column2 are set together, and are None on a field that is not stored"
            )
        return self.relation, self.column1, self.column2

    @override
    def setup_inverses(
        self, registry: Registry, inverses: Collector[Field, Field]
    ) -> None:
        if self.relation:
            relation, column1, column2 = self._get_relation_triple()
            for mname, fname in registry.many2many_relations[
                relation, column2, column1
            ]:
                field = registry[mname]._fields[fname]
                inverses.add(self, field)
                inverses.add(field, self)

    @override
    def update_db(
        self, model: ModelLike, columns: dict[str, dict[str, typing.Any]]
    ) -> bool:
        return _ddl.update_db_relation_table(self, model)

    def update_db_foreign_keys(self, model: BaseModel) -> None:
        _ddl.update_db_foreign_keys(self, model)

    @override
    def read(self, records: BaseModel) -> None:
        comodel = records.env[self.comodel_name].with_context(
            **self._prepare_read_context()
        )

        filter_access = self.bypass_search_access and is_search_overridden(
            type(comodel)
        )

        domain = self.get_comodel_domain(records)
        try:
            query = comodel._search(
                domain, order=comodel._order, bypass_access=filter_access
            )
        except AccessError as e:
            raise AccessError(
                records.env._("Failed to read field %s", self) + "\n" + str(e)
            ) from e

        relation, column1, column2 = self._get_relation_columns()
        group = records.env.backend.read_m2m_groups(
            records, relation, column1, column2, query
        )
        _debug.logic(
            "field.many2many.read_groups",
            model=self.model_name,
            field=self.name,
            records=len(records),
            filter_access=filter_access,
        )

        if filter_access and group:
            corecord_ids = OrderedSet(id_ for ids in group.values() for id_ in ids)
            accessible_corecords = comodel.browse(corecord_ids)._filtered_access("read")
            if len(accessible_corecords) < len(corecord_ids):
                _debug.logic(
                    "field.many2many.read.filtered_by_access",
                    model=self.model_name,
                    field=self.name,
                    corecords=len(corecord_ids),
                    dropped=len(corecord_ids) - len(accessible_corecords),
                )
                accessible_ids = set(accessible_corecords._ids)
                for id1, ids in group.items():
                    group[id1] = [id_ for id_ in ids if id_ in accessible_ids]

        values = [tuple(group[id_]) for id_ in records._ids]
        self._insert_cache(records, values)
        _debug.pipeline(
            "field.many2many.read",
            model=self.model_name,
            field=self.name,
            comodel=self.comodel_name,
            records=len(records),
            links=sum(len(ids) for ids in values),
        )

    def _invalidate_relation_siblings(self, records: BaseModel) -> None:
        # Two fields of one model may read the same relation table the same way
        # round, one of them through a domain (product.product's variant values
        # beside its attribute values). A write through one changes what the
        # other reads, and `create` has already cached the other as empty.
        model = records.pool[self.model_name]
        for mname, fname in records.pool.many2many_relations[
            self._get_relation_triple()
        ]:
            if fname == self.name or mname not in (self.model_name, records._name):
                continue
            sibling = model._fields.get(fname)
            if sibling is None or sibling is self:
                continue
            _debug.logic(
                "field.many2many.sibling_invalidated",
                model=self.model_name,
                field=self.name,
                sibling=fname,
                records=len(records),
            )
            sibling._invalidate_cache(records.env, records._ids)

    def _apply_relation_delta(
        self,
        records: BaseModel,
        comodel: BaseModel,
        old_relation: dict,
        new_relation: dict,
        *,
        store: bool,
        created: bool = False,
    ) -> None:
        for record in records:
            ids = tuple(new_relation[record.id])
            if store and not _is_cache_order_stable(comodel, ids):
                # a stored slot reads as a fetch would: in the comodel's order
                # when the sort keys are in memory, else in the commands'
                # order; a computed value keeps the order its compute produced
                sorted_ids = comodel.browse(ids)._sorted_by_ids(comodel._order, False)
                if sorted_ids is not None:
                    ids = sorted_ids
                elif _debug.logic.enabled:
                    _debug.logic(
                        "field.many2many.written_unsorted",
                        model=self.model_name,
                        field=self.name,
                        record=record.id,
                        ids=len(ids),
                    )
            self._update_cache(record, ids, created=created)

        if store:
            self._invalidate_relation_siblings(records)

        modified_corecord_ids = set()

        pairs = [(x, y) for x, ys in new_relation.items() for y in ys - old_relation[x]]
        if pairs:
            if store:
                records.env.backend.link_m2m_pairs(
                    records, *self._get_relation_columns(), pairs
                )

            y_to_xs: defaultdict[typing.Any, typing.Any] = defaultdict(OrderedSet)
            for x, y in pairs:
                y_to_xs[y].add(x)
                modified_corecord_ids.add(y)
            for invf in records.pool.field_inverses[self]:
                invf = typing.cast("_RelationalMulti", invf)
                domain = invf.get_comodel_domain(comodel)
                valid_ids = set(records.filtered_domain(domain)._ids)
                if not valid_ids:
                    continue
                inv_cache = invf._get_cache(comodel.env)
                linked_by_y = {
                    y: tuple(x for x in xs if x in valid_ids)
                    for y, xs in y_to_xs.items()
                }
                invf._sync_added_to_other_scopes(comodel.env, linked_by_y)
                for y, linked in linked_by_y.items():
                    corecord = comodel.browse((y,))
                    ids0 = inv_cache.get(corecord.id, SENTINEL)
                    if ids0 is SENTINEL:
                        if corecord.id:
                            continue
                        ids0 = ()
                    ids1 = tuple(unique(itertools.chain(ids0, linked)))
                    invf._update_cache(corecord, ids1, keep_other_scopes=True)

        unlink_pairs = [
            (x, y) for x, ys in old_relation.items() for y in ys - new_relation[x]
        ]
        _debug.logic(
            "field.many2many.relation_delta",
            model=self.model_name,
            field=self.name,
            records=len(records),
            linked=len(pairs),
            unlinked=len(unlink_pairs),
            store=store,
        )
        pairs = unlink_pairs
        if pairs:
            y_to_xs = defaultdict(set)
            for x, y in pairs:
                y_to_xs[y].add(x)
                modified_corecord_ids.add(y)

            if store:
                records.env.backend.unlink_m2m_pairs(
                    records, *self._get_relation_columns(), pairs
                )

            for invf in records.pool.field_inverses[self]:
                invf = typing.cast("_RelationalMulti", invf)
                inv_cache = invf._get_cache(comodel.env)
                for y, xs in y_to_xs.items():
                    corecord = comodel.browse((y,))
                    invf._sync_other_scopes(comodel.env, y, removed=xs)
                    try:
                        ids0 = inv_cache[corecord.id]
                        ids1 = tuple(id_ for id_ in ids0 if id_ not in xs)
                        invf._update_cache(corecord, ids1, keep_other_scopes=True)
                    except KeyError:
                        pass

        if modified_corecord_ids:
            corecords = comodel.browse(modified_corecord_ids)
            _debug.pipeline(
                "field.many2many.corecords_modified",
                model=self.model_name,
                field=self.name,
                comodel=comodel._name,
                corecords=len(corecords),
                inverses=len(records.pool.field_inverses[self]),
            )
            corecords.modified(
                [
                    invf.name
                    for invf in records.pool.field_inverses[self]
                    if invf.model_name == self.comodel_name
                ]
            )

    def _write_real_apply_commands(
        self, records_commands_list, comodel, old_relation: dict, new_relation: dict
    ) -> None:
        for recs, commands in records_commands_list:
            delta = CommandDelta.fold(commands)
            _debug.logic(
                "field.many2many.delta",
                model=self.model_name,
                field=self.name,
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
            created_ids: tuple = ()
            if delta.created:
                created_ids = comodel.create(
                    [vals for _ref, vals in delta.created]
                )._ids
            for x in recs._ids:
                new_relation[x] = delta.get_final_ids(new_relation[x], created_ids)
            if delta.deleted:
                comodel.browse(list(delta.deleted)).unlink()
                _remove_from_relations(old_relation, new_relation, delta.deleted)

    def _check_new_relation_access(
        self, model, comodel, old_relation: dict, new_relation: dict
    ) -> None:
        try:
            comodel.browse(
                co_id
                for rec_id, new_co_ids in new_relation.items()
                for co_id in new_co_ids - old_relation[rec_id]
            ).check_access("read")
        except AccessError as e:
            raise AccessError(
                model.env._("Failed to write field %s", self) + "\n" + str(e)
            ) from e

    @override
    def write_real(
        self,
        records_commands_list: Sequence[tuple[BaseModel, list[CommandValue]]],
        create: bool = False,
    ) -> None:
        if not records_commands_list:
            return

        model, comodel = self._get_writer_models(records_commands_list)

        ids = OrderedSet(rid for recs, cs in records_commands_list for rid in recs.ids)
        records = model.browse(ids)

        if self.store:
            missing_ids = set(self._iter_cache_missing_ids(records))
            if missing_ids:
                _debug.logic(
                    "field.many2many.write.read_before_write",
                    model=self.model_name,
                    field=self.name,
                    records=len(records),
                    missing=len(missing_ids),
                )
                self._read_missing_with_batch(records_commands_list, missing_ids)

        old_relation = {
            record.id: OrderedSet(self._get_raw_ids(record))
            for record in records.with_context(active_test=False)
        }
        new_relation = {x: OrderedSet(ys) for x, ys in old_relation.items()}

        self._write_real_apply_commands(
            records_commands_list, comodel, old_relation, new_relation
        )

        if not model.env.su:
            _debug.logic(
                "field.many2many.new_links_access_checked",
                model=self.model_name,
                field=self.name,
                uid=model.env.uid,
                records=len(records),
            )
            self._check_new_relation_access(model, comodel, old_relation, new_relation)

        self._apply_relation_delta(
            records,
            comodel,
            old_relation,
            new_relation,
            store=self.store,
            created=create,
        )

    def _read_missing_with_batch(
        self,
        records_commands_list: Sequence[tuple[BaseModel, list[CommandValue]]],
        missing_ids: set,
    ) -> None:
        # a compute assigning the field record by record over a batch hands
        # each record with the batch as its prefetch: the relation is read for
        # the batch once, as a getter would, not once per assignment
        for recs, _commands in records_commands_list:
            field_cache = self._get_cache(recs.env)
            for record in recs:
                if record.id in missing_ids and (
                    record.id not in field_cache or field_cache[record.id] is PENDING
                ):
                    self.read(self._to_prefetch(record))

    @override
    def write_new(
        self,
        records_commands_list: Sequence[tuple[BaseModel, list[CommandValue]]],
    ) -> None:
        if not records_commands_list:
            return

        model, comodel = self._get_writer_models(records_commands_list)

        def new(id_):
            return id_ and NewId(id_)

        old_relation = {
            record.id: OrderedSet(self._get_raw_ids(record))
            for records, _ in records_commands_list
            for record in records
        }
        new_relation = {x: OrderedSet(ys) for x, ys in old_relation.items()}

        for recs, commands in records_commands_list:
            delta = CommandDelta.fold(commands, new)
            created_ids = [comodel.new(vals, ref=ref).id for ref, vals in delta.created]
            for line_id, vals in delta.updated:
                comodel.browse([line_id]).update(vals)
            for id_ in recs._ids:
                new_relation[id_] = delta.get_final_ids(new_relation[id_], created_ids)

        if new_relation == old_relation:
            _debug.logic(
                "field.many2many.write_new_unchanged",
                model=self.model_name,
                field=self.name,
                records=len(old_relation),
            )
            return

        records = model.browse(old_relation)
        self._apply_relation_delta(
            records, comodel, old_relation, new_relation, store=False
        )

    @override
    def _condition_to_sql_relational(
        self,
        model: BaseModel,
        alias: str,
        exists: bool,
        coquery: Query,
        query: Query,
    ) -> SQL:
        _debug.logic(
            "field.many2many.condition_strategy",
            model=model._name,
            field=self.name,
            exists=exists,
            strategy="empty_subquery"
            if coquery.is_empty()
            else "any_link"
            if not coquery.where_clause
            else "exists_in",
        )
        if coquery.is_empty():
            return SQL("FALSE") if exists else SQL("TRUE")
        rel_table, rel_id1, rel_id2 = self._get_relation_columns()
        rel_alias = query.get_table_alias(alias, self.name)
        if not coquery.where_clause:
            return SQL(
                "%sEXISTS (SELECT 1 FROM %s AS %s WHERE %s = %s)",
                SQL("NOT ") if not exists else SQL.EMPTY,
                SQL.identifier(rel_table),
                SQL.identifier(rel_alias),
                SQL.identifier(rel_alias, rel_id1),
                SQL.identifier(alias, "id"),
            )
        return SQL(
            "%sEXISTS (SELECT 1 FROM %s AS %s WHERE %s = %s AND %s IN %s)",
            SQL("NOT ") if not exists else SQL.EMPTY,
            SQL.identifier(rel_table),
            SQL.identifier(rel_alias),
            SQL.identifier(rel_alias, rel_id1),
            SQL.identifier(alias, "id"),
            SQL.identifier(rel_alias, rel_id2),
            coquery.subselect(),
        )
