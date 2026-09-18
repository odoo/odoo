import annotationlib
import inspect
import itertools
import typing
from collections import defaultdict

from odoo.libs.debug_log import DebugLog
from odoo.tools import SQL, Query, unique

from .... import decorators as api
from ...._typing import DomainType
from ....constants import READ_GROUP_AGGREGATE
from ....domain import Domain
from ....helpers import get_tuple_itemgetter
from ....parsing import parse_read_group_spec, regex_field_agg
from .fill import _ReadGroupFillMixin
from .format import _ReadGroupFormatMixin
from .sql import _ReadGroupSQLMixin

if typing.TYPE_CHECKING:
    from collections.abc import Sequence

_debug = DebugLog(__name__)


class ReadGroupMixin(_ReadGroupSQLMixin, _ReadGroupFormatMixin, _ReadGroupFillMixin):
    __slots__ = ()

    _ROW_SAFE_AGGREGATE_SUFFIXES = (
        ":max",
        ":min",
        ":bool_and",
        ":bool_or",
        ":array_agg_distinct",
        ":recordset",
        ":count_distinct",
    )

    @classmethod
    def _read_group_is_dedup_required(cls, aggregates: Sequence[str]) -> bool:
        return any(
            not aggregate.endswith(cls._ROW_SAFE_AGGREGATE_SUFFIXES)
            for aggregate in aggregates
            if aggregate != "__count"
        )

    @staticmethod
    def _read_grouping_sets_m2m_batches(
        grouping_sets: Sequence[Sequence[str]], many2many_groupby_specs: list[str]
    ) -> list[tuple[list[int], list[Sequence[str]]]]:
        m2m_combinations = (
            groupby
            for i in range(len(many2many_groupby_specs), -1, -1)
            for groupby in itertools.combinations(many2many_groupby_specs, i)
        )

        grouping_sets_to_process = dict(enumerate(grouping_sets))
        batched_calls = []

        for m2m_comb in m2m_combinations:
            if not grouping_sets_to_process:
                break
            sub_grouping_sets = []
            sub_result_indexes = []
            for i, groupby in list(grouping_sets_to_process.items()):
                if all(m2m in groupby for m2m in m2m_comb):
                    sub_grouping_sets.append(groupby)
                    sub_result_indexes.append(i)
                    grouping_sets_to_process.pop(i)

            if sub_grouping_sets:
                batched_calls.append((sub_result_indexes, sub_grouping_sets))

        if grouping_sets_to_process:
            raise RuntimeError(
                f"M2M decomposition lost grouping sets: "
                f"{list(grouping_sets_to_process.values())}"
            )
        return batched_calls

    def _read_grouping_sets_split_m2m(
        self,
        domain: DomainType,
        grouping_sets: Sequence[Sequence[str]],
        aggregates: Sequence[str],
        order: str | None,
        all_groupby_specs: tuple[str, ...],
        many2many_groupby_specs: list[str],
        result: list[list[tuple]],
    ) -> bool:
        batched_calls = self._read_grouping_sets_m2m_batches(
            grouping_sets, many2many_groupby_specs
        )
        if len(batched_calls) <= 1:
            return False

        _debug.pipeline(
            "read_group.m2m_split",
            model=self._name,
            sets=len(grouping_sets),
            many2many=len(many2many_groupby_specs),
            batches=len(batched_calls),
        )
        for indexes, sub_grouping_sets in batched_calls:
            sub_order_parts = []
            all_sub_groupby = {
                spec for groupby in sub_grouping_sets for spec in groupby
            }
            for order_part in (order or "").split(","):
                order_part = order_part.strip()
                if not any(
                    order_part == spec or order_part.startswith(f"{spec} ")
                    for spec in all_groupby_specs
                    if spec not in all_sub_groupby
                ):
                    sub_order_parts.append(order_part)

            sub_results = self._read_grouping_sets(
                domain,
                sub_grouping_sets,
                aggregates=aggregates,
                order=",".join(sub_order_parts),
            )
            for index, subresult in zip(indexes, sub_results, strict=True):
                result[index] = subresult
        return True

    @staticmethod
    def _read_group_count_distinct(
        aggregates: Sequence[str], order: str | None
    ) -> tuple[tuple[str, ...], str | None]:
        aggregates = tuple(
            aggregate if aggregate != "__count" else "id:count_distinct"
            for aggregate in aggregates
        )
        if order:
            parts = []
            for part in order.split(","):
                part = part.strip()
                if part == "__count" or part.startswith("__count "):
                    part = "id:count_distinct" + part[len("__count") :]
                parts.append(part)
            order = ", ".join(parts)
        return aggregates, order

    def _read_grouping_sets_query(
        self,
        query,
        grouping_sets: Sequence[Sequence[str]],
        all_groupby_specs: tuple[str, ...],
        aggregates: Sequence[str],
        order: str | None,
    ) -> tuple[dict[str, SQL], list[SQL]]:
        groupby_terms: dict[str, SQL] = {
            spec: self._read_group_groupby(self._table, spec, query)
            for spec in all_groupby_specs
        }
        aggregates_terms: list[SQL] = [
            self._read_group_select(spec, query) for spec in aggregates
        ]
        if groupby_terms:
            grouping_select_sql = SQL(
                "GROUPING(%s)", SQL(", ").join(unique(groupby_terms.values()))
            )
        else:
            grouping_select_sql = SQL("0")

        query.order = self._read_group_orderby(order, groupby_terms, query)
        # one GROUPING SETS entry per distinct set of terms: a set given twice,
        # in the same or another order, would be grouped twice by PostgreSQL
        # and both results would carry the rows twice
        grouping_sets_sql = {
            frozenset(
                groupby_terms[groupby_spec] for groupby_spec in grouping_set
            ): SQL(
                "(%s)",
                SQL(", ").join(
                    groupby_terms[groupby_spec] for groupby_spec in grouping_set
                ),
            )
            for grouping_set in reversed(grouping_sets)
        }
        query.groupby = SQL(
            "GROUPING SETS (%s)", SQL(", ").join(reversed(grouping_sets_sql.values()))
        )
        return groupby_terms, [
            grouping_select_sql,
            *groupby_terms.values(),
            *aggregates_terms,
        ]

    @api.model
    def _read_grouping_sets(
        self,
        domain: DomainType,
        grouping_sets: Sequence[Sequence[str]],
        aggregates: Sequence[str] = (),
        order: str | None = None,
    ) -> list[list[tuple]]:
        if not grouping_sets:
            msg = "The 'grouping_sets' parameter cannot be empty."
            raise ValueError(msg)

        query = self._search(domain)
        result: list[list[tuple]] = [[] for __ in grouping_sets]
        if query.is_empty():
            _debug.logic(
                "read_group.grouping_sets_empty_query",
                model=self._name,
                sets=len(grouping_sets),
            )
            self._check_read_group_spec_access(
                itertools.chain.from_iterable(grouping_sets), aggregates, query
            )
            return result

        all_groupby_specs = tuple(
            unique(spec for groupby in grouping_sets for spec in groupby)
        )

        many2many_groupby_specs: list[str] = []
        if len(grouping_sets) > 1:
            many2many_groupby_specs.extend(
                spec
                for spec in all_groupby_specs
                if self._can_groupby_spec_duplicate_rows(self, spec)
            )

        _debug.logic(
            "read_group.grouping_sets",
            model=self._name,
            sets=len(grouping_sets),
            groupby=len(all_groupby_specs),
            aggregates=len(aggregates),
            many2many=len(many2many_groupby_specs),
            dedup=bool(many2many_groupby_specs)
            and self._read_group_is_dedup_required(aggregates),
        )
        if many2many_groupby_specs and self._read_group_is_dedup_required(aggregates):
            if self._read_grouping_sets_split_m2m(
                domain,
                grouping_sets,
                aggregates,
                order,
                all_groupby_specs,
                many2many_groupby_specs,
                result,
            ):
                return result

        elif many2many_groupby_specs and "__count" in aggregates:
            _debug.logic("read_group.count_distinct_rewrite", model=self._name)
            aggregates, order = self._read_group_count_distinct(aggregates, order)

        groupby_terms, select_args = self._read_grouping_sets_query(
            query, grouping_sets, all_groupby_specs, aggregates, order
        )

        row_values = self.env.backend.read_grouping_sets_rows(
            self,
            query.select(*select_args),
            domain=domain,
            query=query,
            grouping_sets=grouping_sets,
            groupby_terms=groupby_terms,
            aggregates=aggregates,
            order=order,
        )
        _debug.perf.count(
            "read_group.grouping_sets_rows",
            model=self._name,
            sets=len(grouping_sets),
            groupby=len(all_groupby_specs),
            aggregates=len(aggregates),
            rows=len(row_values),
        )
        if not row_values:
            return result

        return self._read_grouping_sets_dispatch_rows(
            row_values,
            grouping_sets,
            all_groupby_specs,
            aggregates,
            groupby_terms,
            result,
        )

    def _can_groupby_spec_duplicate_rows(self, model, spec) -> bool:
        fname, property_name, __ = parse_read_group_spec(spec)
        field = model._fields[fname]
        if field.group_by_field:
            return self._can_groupby_spec_duplicate_rows(
                model, field.group_by_field + spec[len(fname) :]
            )
        if field.group_by_sql:
            # one expression per row of the model's own table
            return False
        if field.is_properties:
            if not property_name:
                raise ValueError(
                    f"Field {fname!r} on model {model._name!r} is a properties "
                    f"field; group by one of its properties "
                    f"({fname}.<property>), not by the field itself"
                )
            definition = model.get_property_definition(f"{fname}.{property_name}")
            property_type = definition.get("type")
            return property_type in ("tags", "many2many")

        if property_name:
            if not field.is_many2one:
                raise TypeError(
                    f"Field {fname!r} on {model._name!r}: dotted groupby spec "
                    f"only supported for many2one, got {field.type!r}"
                )
            return model._can_groupby_spec_duplicate_rows(
                model.env[field.comodel_name], property_name
            )

        return field.is_many2many

    def _read_grouping_sets_dispatch_rows(
        self,
        row_values: list[tuple],
        grouping_sets: Sequence[Sequence[str]],
        all_groupby_specs: Sequence[str],
        aggregates: Sequence[str],
        groupby_terms: dict[str, SQL],
        result: list[list[tuple]],
    ) -> list[list[tuple]]:
        aggregates_indexes = tuple(
            range(len(all_groupby_specs), len(all_groupby_specs) + len(aggregates))
        )

        mask_sql_mapping = {
            sql_groupby: 1 << i
            for i, sql_groupby in enumerate(
                reversed(list(unique(groupby_terms.values())))
            )
        }

        # every set sharing a mask receives the same rows, each through its
        # own extractor: two sets naming the same terms in another order
        # answer the same groups with their own column order
        dispatch_by_mask: defaultdict[int, list[tuple]] = defaultdict(list)
        for result_index, groupby in enumerate(grouping_sets):
            sql_terms = {groupby_terms[groupby_spec] for groupby_spec in groupby}
            groupby_mask = sum(
                mask
                for sql_term, mask in mask_sql_mapping.items()
                if sql_term not in sql_terms
            )
            dispatch_by_mask[groupby_mask].append(
                (
                    result[result_index].append,
                    get_tuple_itemgetter(
                        list(
                            itertools.chain(
                                (
                                    all_groupby_specs.index(groupby_spec)
                                    for groupby_spec in groupby
                                ),
                                aggregates_indexes,
                            )
                        )
                    ),
                )
            )

        aggregates_start_index = len(all_groupby_specs) + 1
        columns: list = list(zip(*row_values, strict=False))
        dispatch_info = map(dispatch_by_mask.__getitem__, columns[0])
        columns = [
            *map(
                self._read_group_postprocess_groupby,
                all_groupby_specs,
                columns[1:aggregates_start_index],
                strict=False,
            ),
            *map(
                self._read_group_postprocess_aggregate,
                aggregates,
                columns[aggregates_start_index:],
                strict=False,
            ),
        ]

        for targets, *row in zip(dispatch_info, *columns, strict=True):
            for append_method, extractor in targets:
                append_method(extractor(row))

        duplicated_sets = sum(len(targets) - 1 for targets in dispatch_by_mask.values())
        _debug.pipeline(
            "read_group.grouping_sets.dispatched",
            model=self._name,
            rows=len(row_values),
            grouping_sets=len(grouping_sets),
            distinct_masks=len(dispatch_by_mask),
            duplicated_sets=duplicated_sets,
        )
        return result

    @api.model
    def _read_group(
        self,
        domain: DomainType,
        groupby: Sequence[str] = (),
        aggregates: Sequence[str] = (),
        having: DomainType | None = None,
        offset: int = 0,
        limit: int | None = None,
        order: str | None = None,
    ) -> list[tuple]:
        query = self._search(domain)
        if query.is_empty():
            _debug.logic(
                "read_group.empty_query",
                model=self._name,
                groupby=len(groupby),
                having=bool(having),
            )
            self._check_read_group_spec_access(groupby, aggregates, query)
            if not groupby:
                if having:
                    # the aggregate row over no record, kept or dropped by the
                    # having clause as SQL decides it
                    empty_query = Query(self.env, self._table, self._table_sql)
                    empty_query.add_where(SQL("FALSE"))
                    empty_query.having = self._read_group_having(
                        list(having), empty_query
                    )
                    empty_rows = self.env.backend.read_group_rows(
                        self,
                        empty_query.select(SQL("COUNT(*)")),
                        domain=domain,
                        query=empty_query,
                        groupby=(),
                        aggregates=aggregates,
                        having=having,
                        order=None,
                        limit=None,
                        offset=0,
                    )
                    if not empty_rows:
                        return []
                return [
                    tuple(
                        self._read_group_empty_value(spec)
                        for spec in itertools.chain(groupby, aggregates)
                    )
                ]
            return []

        if groupby:
            query.limit = limit
            query.offset = offset

        groupby_terms: dict[str, SQL] = {
            spec: self._read_group_groupby(self._table, spec, query) for spec in groupby
        }
        aggregates_terms: list[SQL] = [
            self._read_group_select(spec, query) for spec in aggregates
        ]
        select_args = [
            *[groupby_terms[spec] for spec in groupby],
            *aggregates_terms,
        ]
        if groupby_terms:
            query.order = self._read_group_orderby(order, groupby_terms, query)
            query.groupby = SQL(", ").join(groupby_terms.values())
        if having:
            query.having = self._read_group_having(list(having), query)

        row_values = self.env.backend.read_group_rows(
            self,
            query.select(*select_args),
            domain=domain,
            query=query,
            groupby=groupby,
            aggregates=aggregates,
            having=having,
            order=order,
            limit=limit,
            offset=offset,
        )
        _debug.perf.count(
            "read_group.rows",
            model=self._name,
            groupby=len(groupby),
            aggregates=len(aggregates),
            rows=len(row_values),
            limit=limit,
            offset=offset,
        )

        if not row_values:
            return []

        column_iterator: typing.Iterator[list] = zip(*row_values, strict=False)  # type: ignore[assignment]

        column_result = []
        for spec in groupby:
            column = self._read_group_postprocess_groupby(spec, next(column_iterator))
            column_result.append(column)
        for spec in aggregates:
            column = self._read_group_postprocess_aggregate(spec, next(column_iterator))
            column_result.append(column)
        if next(column_iterator, None) is not None:
            raise RuntimeError(
                f"Read group returned more columns than expected for "
                f"groupby={groupby} aggregates={aggregates}"
            )

        return list(zip(*column_result, strict=False))

    @api.model
    def _check_read_group_spec_access(self, groupby, aggregates, query) -> None:
        for spec in groupby:
            model = self
            sub_spec = spec
            while True:
                fname, seq_fnames, granularity = parse_read_group_spec(sub_spec)
                if fname not in model._fields:
                    model._read_group_groupby(model._table, sub_spec, query)
                    break
                field = model._fields[fname]
                if seq_fnames and not field.is_properties:
                    if not field.is_many2one:
                        raise ValueError(
                            f"Only many2one path is accepted for the {spec!r} groupby spec"
                        )
                    model._check_spec_field_read_access(field)
                    model = model.env[field.comodel_name]
                    sub_spec = (
                        f"{seq_fnames}:{granularity}" if granularity else seq_fnames
                    )
                    continue
                model._check_spec_field_read_access(field)
                break

        for spec in aggregates:
            if spec == "__count":
                continue
            fname, property_name, func = parse_read_group_spec(spec)
            if property_name:
                raise ValueError(
                    f"Invalid {spec!r}, this dot notation is not supported"
                )
            if fname not in self._fields:
                raise ValueError(
                    f"Invalid field {fname!r} on model {self._name!r} for {spec!r}."
                )
            if not func:
                raise ValueError(f"Aggregate method is mandatory for {fname!r}")
            if func != "sum_currency" and func not in READ_GROUP_AGGREGATE:
                raise ValueError(f"Invalid aggregate method {func!r} for {spec!r}.")
            self._check_spec_field_read_access(self._fields[fname])

    def _check_spec_field_read_access(self, field) -> None:
        if field.related and not field.store:
            if not (self.env.su or field.compute_sudo or field.inherited):
                raise ValueError(
                    f"Cannot convert {field} to SQL because it is not a sudoed"
                    " related or inherited field"
                )
            _debug.logic(
                "read_group.spec_access.related_traversed",
                model=self._name,
                field=field.name,
                related=field.related,
                sudo=bool(self.env.su or field.compute_sudo),
            )
            model = self.sudo(self.env.su or field.compute_sudo)
            *path_fnames, last_fname = field.related.split(".")
            for path_fname in path_fnames:
                path_field = model._fields[path_fname]
                model._check_field_access(path_field, "read")
                model = model.env[path_field.comodel_name]
            model._check_spec_field_read_access(model._fields[last_fname])
            return
        self._check_field_access(field, "read")

    def _read_group_annotate_groupby(
        self, lazy_groupby: Sequence[str]
    ) -> dict[str, str]:
        annotated_groupby = {}
        for group_spec in lazy_groupby:
            field_name, property_name, granularity = parse_read_group_spec(group_spec)
            if field_name not in self._fields:
                raise ValueError(
                    f"Invalid field {field_name!r} on model {self._name!r}"
                )
            field = self._fields[field_name]
            if property_name and not field.is_properties:
                raise ValueError(
                    f"Property name {property_name!r} has to be used on a property field."
                )
            if field.is_temporal:
                annotated_groupby[group_spec] = f"{field_name}:{granularity or 'month'}"
            else:
                annotated_groupby[group_spec] = group_spec
        return annotated_groupby

    def _read_group_annotate_aggregates(
        self,
        fields: Sequence[str],
        lazy_groupby: Sequence[str],
        lazy: bool,
        annotated_groupby: dict[str, str],
    ) -> dict[str, str]:
        annotated_aggregates = {
            (
                f"{lazy_groupby[0].split(':')[0]}_count"
                if lazy and len(lazy_groupby) == 1
                else "__count"
            ): "__count",
        }
        for field_spec in fields:
            if field_spec == "__count":
                continue
            match = regex_field_agg.match(field_spec)
            if not match:
                raise ValueError(f"Invalid field specification {field_spec!r}.")
            name, func, fname = match.groups()

            if fname:
                annotated_aggregates[name] = f"{fname}:{func}"
                continue
            if func:
                annotated_aggregates[name] = f"{name}:{func}"
                continue

            if name not in self._fields:
                raise ValueError(f"Invalid field {name!r} on model {self._name!r}")
            field = self._fields[name]
            if (
                field.base_field.store
                and field.base_field.column_type
                and field.aggregator
                and field_spec not in annotated_groupby
            ):
                annotated_aggregates[name] = f"{name}:{field.aggregator}"
        return annotated_aggregates

    @staticmethod
    def _read_group_annotate_orderby(
        orderby, annotated_groupby: dict[str, str], annotated_aggregates: dict[str, str]
    ) -> str:
        if not orderby:
            return ",".join(annotated_groupby.values())
        new_terms = []
        for order_term in orderby.split(","):
            order_term = order_term.strip()
            for key_name, annotated in itertools.chain(
                reversed(annotated_groupby.items()),
                annotated_aggregates.items(),
            ):
                key_name = key_name.split(":")[0]
                if order_term.startswith(f"{key_name} ") or key_name == order_term:
                    order_term = annotated + order_term[len(key_name) :]
                    break
            new_terms.append(order_term)
        return ",".join(new_terms)

    def _read_group_apply_fill_temporal(
        self,
        rows_dict: list[dict],
        lazy_groupby: Sequence[str],
        annotated_aggregates: dict[str, str],
    ) -> list[dict]:
        fill_temporal = self.env.context.get("fill_temporal")
        if not lazy_groupby or not (
            (rows_dict and fill_temporal) or isinstance(fill_temporal, dict)
        ):
            return rows_dict
        _debug.logic(
            "read_group.fill_temporal",
            model=self._name,
            rows=len(rows_dict),
            groupby=len(lazy_groupby),
            options=isinstance(fill_temporal, dict),
        )
        if not isinstance(fill_temporal, dict):
            fill_temporal = {}
        else:
            known_keys = {
                name
                for name, param in inspect.signature(
                    self._read_group_fill_temporal,
                    annotation_format=annotationlib.Format.FORWARDREF,
                ).parameters.items()
                if param.default is not inspect.Parameter.empty
            }
            fill_temporal = {
                key: value for key, value in fill_temporal.items() if key in known_keys
            }
        return self._read_group_fill_temporal(
            rows_dict,
            lazy_groupby,
            annotated_aggregates,
            **fill_temporal,
        )

    @api.model
    @api.readonly
    @api.deprecated(
        "Since 19.0, read_group is deprecated. Please use _read_group in the backend code or formatted_read_group for a complete formatted result"
    )
    def read_group(
        self,
        domain,
        fields,
        groupby,
        offset=0,
        limit=None,
        orderby=False,
        lazy=True,
    ):
        groupby = [groupby] if isinstance(groupby, str) else groupby
        lazy_groupby = groupby[:1] if lazy else groupby

        annotated_groupby = self._read_group_annotate_groupby(lazy_groupby)
        annotated_aggregates = self._read_group_annotate_aggregates(
            fields, lazy_groupby, lazy, annotated_groupby
        )
        orderby = self._read_group_annotate_orderby(
            orderby, annotated_groupby, annotated_aggregates
        )

        domain = Domain(domain)
        rows = self._read_group(
            domain,
            list(annotated_groupby.values()),
            list(annotated_aggregates.values()),
            offset=offset,
            limit=limit,
            order=orderby,
        )
        rows_dict = [
            dict(
                zip(
                    itertools.chain(annotated_groupby, annotated_aggregates),
                    row,
                    strict=False,
                )
            )
            for row in rows
        ]

        rows_dict = self._read_group_apply_fill_temporal(
            rows_dict, lazy_groupby, annotated_aggregates
        )
        _debug.pipeline(
            "read_group.legacy",
            model=self._name,
            groupby=len(groupby),
            lazy=lazy,
            aggregates=len(annotated_aggregates),
            rows=len(rows_dict),
            limit=limit,
        )

        if lazy_groupby and lazy:
            rows_dict = self._read_group_expand_results(
                domain,
                lazy_groupby[0],
                annotated_aggregates,
                rows_dict,
                read_group_order=orderby,
            )

        for row in rows_dict:
            row["__domain"] = domain
            if len(lazy_groupby) < len(groupby):
                row["__context"] = {"group_by": groupby[len(lazy_groupby) :]}

        self._read_group_format_result(rows_dict, lazy_groupby)

        return rows_dict
