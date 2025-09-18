"""
Core read_group mixin — main entry points.

Contains ReadGroupMixin with the primary public methods: _read_group,
_read_grouping_sets, _read_group_empty_value, and the deprecated read_group.

SQL generation, post-processing, and fill logic are in separate sub-mixins
(sql.py, format.py, fill.py) that ReadGroupMixin inherits from.
"""

import itertools
from collections import defaultdict
from collections.abc import Sequence
from operator import itemgetter

from odoo.tools import SQL, unique

from .... import decorators as api
from ...._typing import DomainType, ModelType
from ....constants import READ_GROUP_TIME_GRANULARITY
from ....domain import Domain
from ....parsing import parse_read_group_spec, regex_field_agg
from .fill import _ReadGroupFillMixin
from .format import _ReadGroupFormatMixin
from .sql import _ReadGroupSQLMixin


def _itemgetter_tuple(items):
    """Create an itemgetter that always returns a tuple.

    Fixes itemgetter inconsistency of not returning a tuple if len(items) == 1.
    """
    if len(items) == 0:
        return lambda a: ()
    if len(items) == 1:
        return lambda gettable: (gettable[items[0]],)
    return itemgetter(*items)


class ReadGroupMixin(_ReadGroupSQLMixin, _ReadGroupFormatMixin, _ReadGroupFillMixin):
    """Mixin providing read_group operations functionality.

    This mixin is inherited by BaseModel and provides methods for grouping
    and aggregating records. SQL generation, formatting, and fill logic are
    in dedicated sub-mixins for maintainability.
    """

    __slots__ = ()

    @api.model
    def _read_grouping_sets(
        self,
        domain: DomainType,
        grouping_sets: Sequence[Sequence[str]],
        aggregates: Sequence[str] = (),
        order: str | None = None,
    ) -> list[list[tuple]]:
        """Performs multiple aggregations with different groupings in a single query if possible.

        This method uses SQL `GROUPING SETS` as a more advanced and efficient
        alternative to calling :meth:`~._read_group` multiple times with different
        `groupby` parameters. It allows you to get different levels of aggregated
        data in one database round-trip.
        Note that for many2many multiple SQL might be needed because of the deduplicated rows.

        :param domain: :ref:`A search domain <reference/orm/domains>` to filter records before grouping
        :param grouping_sets: A list of `groupby` specifications. Each inner list
                              is a set of fields to group by and is equivalent to the
                              `groupby` parameter of the :meth:`~._read_group` method.
                              For example: `[['partner_id'], ['partner_id', 'state']]`.
        :param aggregates: list of aggregates specification.
                Each element is `'field:agg'` (aggregate field with aggregation function `'agg'`).
                The possible aggregation functions are the ones provided by
                `PostgreSQL <https://www.postgresql.org/docs/current/static/functions-aggregate.html>`_,
                `'count_distinct'` with the expected meaning and `'recordset'` to act like `'array_agg'`
                converted into a recordset.
        :param order: optional ``order by`` specification, for
                overriding the natural sort ordering of the groups,
                see also :meth:`~.search`.
        :return: A list of lists of tuples. The outer list's structure mirrors the
                 input `grouping_sets`. Each inner list contains the results for one
                 grouping specification. Each tuple within an inner list contains the
                 values for the grouped fields, followed by the aggregate values,
                 in the order they were specified.

                 For example, given:
                 - `grouping_sets=[['foo'], ['foo', 'bar']]`
                 - `aggregates=['baz:sum']`

                 The returned structure would be:
                  ::

                    [
                        # Results for ['foo']
                        [(foo1_val, baz_sum_1), (foo2_val, baz_sum_2), ...],
                        # Results for ['foo', 'bar']
                        [(foo1_val, bar1_val, baz_sum_3), (foo2_val, bar2_val, baz_sum_4), ...],
                    ]

        :raise AccessError: if user is not allowed to access requested information
        """
        if not grouping_sets:
            raise ValueError("The 'grouping_sets' parameter cannot be empty.")

        query = self._search(domain)
        result = [[] for __ in grouping_sets]
        if query.is_empty():
            return result

        # grouping_sets: [(a, b), (a), ()]
        # all_groupby_specs: (a, b)
        all_groupby_specs = tuple(
            unique(spec for groupby in grouping_sets for spec in groupby)
        )

        # --- Many2many Special Handling ---
        many2many_groupby_specs = []
        if (
            len(grouping_sets) > 1
        ):  # many2many logic only applies if we have multiple groupings

            def might_duplicate_rows(model, spec) -> bool:
                fname, property_name, __ = parse_read_group_spec(spec)
                field = model._fields[fname]
                if field.type == "properties":
                    definition = self.get_property_definition(
                        f"{fname}.{property_name}"
                    )
                    property_type = definition.get("type")
                    return property_type in ("tags", "many2many")

                if property_name:
                    assert field.type == "many2one"
                    return might_duplicate_rows(
                        self.env[field.comodel_name], property_name
                    )

                return field.type == "many2many"

            many2many_groupby_specs.extend(spec for spec in all_groupby_specs if might_duplicate_rows(self, spec))

        if (
            many2many_groupby_specs
            and
            # If aggregates are sensitive to row duplication (like sum, avg), we must isolate M2M groupings.
            any(
                not aggregate.endswith(
                    (
                        ":max",
                        ":min",
                        ":bool_and",
                        ":bool_or",
                        ":array_agg_distinct",
                        ":recordset",
                        ":count_distinct",
                    ),
                )
                for aggregate in aggregates
                if aggregate != "__count"
            )
        ):
            # The following logic is a recursive decomposition strategy. It's complex
            # but necessary to prevent M2M joins from corrupting aggregates in other grouping sets.
            # We find all combinations of M2M fields and create a sub-call for grouping sets
            # that share that exact combination of M2M fields.

            # ['A', 'B', 'C'] => [('A', 'B', 'C'), ('A', 'B'), ('A', 'C'), ('B', 'C'), ('A',), ('B',), ('C',), ()]
            m2m_combinaisons = (
                groupby
                for i in range(len(many2many_groupby_specs), -1, -1)
                for groupby in itertools.combinations(many2many_groupby_specs, i)
            )

            grouping_sets_to_process = dict(enumerate(grouping_sets))
            batched_calls = []  # [([groupby, ...], [index_result, ...])]

            for m2m_comb in m2m_combinaisons:
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

            assert not grouping_sets_to_process
            # If the problem was decomposed, make recursive calls and assemble results.
            if len(batched_calls) > 1:
                for indexes, sub_grouping_sets in batched_calls:

                    sub_order_parts = []
                    all_sub_groupby = {
                        spec for groupby in sub_grouping_sets for spec in groupby
                    }
                    for order_part in (order or "").split(","):
                        order_part = order_part.strip()
                        if not any(
                            order_part.startswith(spec)
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
                    for index, subresult in zip(indexes, sub_results, strict=False):
                        result[index] = subresult
                return result

        elif many2many_groupby_specs and "__count" in aggregates:
            # Efficiently handle '__count' with M2M fields by using a distinct count on 'id'
            # without making another _read_grouping_sets (this is the very common case).
            aggregates = tuple(
                aggregate if aggregate != "__count" else "id:count_distinct"
                for aggregate in aggregates
            )
            if order:
                order = order.replace("__count", "id:count_distinct")

        # --- SQL Query Construction ---
        groupby_terms: dict[str, SQL] = {
            spec: self._read_group_groupby(self._table, spec, query)
            for spec in all_groupby_specs
        }
        aggregates_terms: list[SQL] = [
            self._read_group_select(spec, query) for spec in aggregates
        ]
        if groupby_terms:
            # grouping_select_sql: GROUPING(a, b)
            grouping_select_sql = SQL(
                "GROUPING(%s)", SQL(", ").join(unique(groupby_terms.values()))
            )
        else:
            # GROUPING() is invalid SQL, so we use the 0 as literal
            grouping_select_sql = SQL("0")

        select_args = [
            grouping_select_sql,
            *groupby_terms.values(),
            *aggregates_terms,
        ]

        # _read_group_orderby may change groupby_terms then it is necessary to be call before
        query._grouping_sets = True
        query.order = self._read_group_orderby(order, groupby_terms, query)
        # GROUPING SET ((a, b), (a), ())
        grouping_sets_sql = [
            SQL(
                "(%s)",
                SQL(", ").join(
                    groupby_terms[groupby_spec] for groupby_spec in grouping_set
                ),
            )
            for grouping_set in grouping_sets
        ]
        query.groupby = SQL(
            "GROUPING SETS (%s)", SQL(", ").join(unique(grouping_sets_sql))
        )

        # This handles the case where `order` adds columns that must also be in `GROUP BY`.
        # Rebuild the grouping sets to include these extra terms.

        # row_values: [(GROUPING(...), a1, b1, aggregates...), (GROUPING(...), a2, b2, aggregates...), ...]
        row_values = self.env.execute_query(query.select(*select_args))

        if not row_values:  # shortcut
            return result

        # --- Result Post-Processing ---
        # This is the core of the result dispatching logic. It uses the integer
        # returned by GROUPING() as a key to map each result row to the correct
        # grouping set defined by the user.
        aggregates_indexes = tuple(
            range(len(all_groupby_specs), len(all_groupby_specs) + len(aggregates))
        )

        # Map each possible GROUPING() bitmask to its corresponding result list and value extractor.
        # {GROUPING(...): (append_method, extractor_method)}
        mask_grouping_mapping = {}

        # Create a mapping from each unique SQL GROUP BY term to its bitmask value.
        # The terms are reversed to match the PostgreSQL logic where the bitmask was
        # calculated from right to left (LSB first).
        # See PostgreSQL Doc: https://www.postgresql.org/docs/17/functions-aggregate.html#Grouping-Operations
        mask_sql_mapping = {
            sql_groupby: 1 << i
            for i, sql_groupby in enumerate(unique(reversed(groupby_terms.values())))
        }

        mask_grouping_result_indexes = defaultdict(
            list
        )  # To manage "duplicated" groupby
        for result_index, groupby in enumerate(grouping_sets):
            # E.g. GROUPING SET ((a, b), (a), ())
            # GROUPING(a, b): a and b included = 0, a included = 1, b included = 2, none included = 3
            sql_terms = {groupby_terms[groupby_spec] for groupby_spec in groupby}
            groupby_mask = sum(
                mask
                for sql_term, mask in mask_sql_mapping.items()
                # each bit is 0 if the corresponding expression is included in the grouping criteria
                # of the grouping set generating the current result row, and 1 if it is not included.
                if sql_term not in sql_terms
            )

            mask_grouping_result_indexes[groupby_mask].append(result_index)
            if groupby_mask not in mask_grouping_mapping:
                mask_grouping_mapping[groupby_mask] = (
                    result[result_index].append,
                    _itemgetter_tuple(
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

        aggregates_start_index = len(all_groupby_specs) + 1
        # Transpose rows to columns for efficient, column-wise post-processing.
        columns = list(zip(*row_values, strict=False))
        # The first column is the grouping mask
        dispatch_info = map(mask_grouping_mapping.__getitem__, columns[0])
        # Post-process values column by column
        columns = [
            *map(
                self._read_group_postprocess_groupby,
                all_groupby_specs,
                columns[1:aggregates_start_index], strict=False,
            ),
            *map(
                self._read_group_postprocess_aggregate,
                aggregates,
                columns[aggregates_start_index:], strict=False,
            ),
        ]

        # result: [
        #   [(a1, b1, <aggregates>), (a2, b2, <aggregates>), ...],
        #   [(a1, <aggregates>), (a2, <aggregates>), ...],
        #   [(<aggregates>)],
        # ]
        for (append_method, extractor), *row in zip(
            dispatch_info, *columns, strict=True
        ):
            append_method(extractor(row))

        # Manage groupbys targetting the same column(s), then having the same results
        for duplicate_groups_indexes in mask_grouping_result_indexes.values():
            if len(duplicate_groups_indexes) < 2:
                continue
            # The first index's result is the source for all others in this group
            source_result_group = result[duplicate_groups_indexes[0]]
            for duplicate_group_index in duplicate_groups_indexes[1:]:
                result[duplicate_group_index] = source_result_group[:]

        return result

    @api.model
    def _read_group(
        self,
        domain: DomainType,
        groupby: Sequence[str] = (),
        aggregates: Sequence[str] = (),
        having: DomainType = (),
        offset: int = 0,
        limit: int | None = None,
        order: str | None = None,
    ) -> list[tuple]:
        """Get fields aggregations specified by ``aggregates`` grouped by the given ``groupby``
        fields where record are filtered by the ``domain``.

        :param domain: :ref:`A search domain <reference/orm/domains>`. Use an empty
                list to match all records.
        :param groupby: list of groupby descriptions by which the records will be grouped.
                A groupby description is either a field (then it will be grouped by that field)
                or a string `'field:granularity'`. Right now, the only supported granularities
                are `'day'`, `'week'`, `'month'`, `'quarter'` or `'year'`, and they only make sense for
                date/datetime fields.
                Additionally integer date parts are also supported:
                `'year_number'`, `'quarter_number'`, `'month_number'`, `'iso_week_number'`, `'day_of_year'`, `'day_of_month'`,
                'day_of_week', 'hour_number', 'minute_number' and 'second_number'.
        :param aggregates: list of aggregates specification.
                Each element is `'field:agg'` (aggregate field with aggregation function `'agg'`).
                The possible aggregation functions are the ones provided by
                `PostgreSQL <https://www.postgresql.org/docs/current/static/functions-aggregate.html>`_,
                `'count_distinct'` with the expected meaning and `'recordset'` to act like `'array_agg'`
                converted into a recordset.
        :param having: A domain where the valid "fields" are the aggregates.
        :param offset: optional number of groups to skip
        :param limit: optional max number of groups to return
        :param order: optional ``order by`` specification, for
                overriding the natural sort ordering of the groups,
                see also :meth:`~.search`.
        :return: list of tuples containing in the order the groups values and aggregates values (flatten):
                `[(groupby_1_value, ... , aggregate_1_value_aggregate, ...), ...]`.
                If group is related field, the value of it will be a recordset (with a correct prefetch set).

        :raise AccessError: if user is not allowed to access requested information
        """
        self.browse().check_access("read")

        query = self._search(domain)
        if query.is_empty():
            if not groupby:
                # when there is no group, postgresql always return a row
                return [
                    tuple(
                        self._read_group_empty_value(spec)
                        for spec in itertools.chain(groupby, aggregates)
                    )
                ]
            return []

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
            query.having = self._read_group_having(list(having), query)

        # row_values: [(a1, b1, c1), (a2, b2, c2), ...]
        row_values = self.env.execute_query(query.select(*select_args))

        if not row_values:
            return row_values

        # post-process values column by column
        column_iterator = zip(*row_values, strict=False)

        # column_result: [(a1, a2, ...), (b1, b2, ...), (c1, c2, ...)]
        column_result = []
        for spec in groupby:
            column = self._read_group_postprocess_groupby(spec, next(column_iterator))
            column_result.append(column)
        for spec in aggregates:
            column = self._read_group_postprocess_aggregate(spec, next(column_iterator))
            column_result.append(column)
        assert next(column_iterator, None) is None

        # return [(a1, b1, c1), (a2, b2, c2), ...]
        return list(zip(*column_result, strict=False))

    @api.model
    def _read_group_empty_value(self, spec):
        """Return the empty value corresponding to the given groupby spec or aggregate spec."""
        if spec == "__count":
            return 0
        fname, chain_fnames, func = parse_read_group_spec(
            spec
        )  # func is either None, granularity or an aggregate
        if func in ("count", "count_distinct"):
            return 0
        if func in ("array_agg", "array_agg_distinct"):
            return []
        field = self._fields[fname]
        if (not func or func == "recordset") and (field.relational or fname == "id"):
            if chain_fnames and field.type == "many2one":
                groupby_seq = f"{chain_fnames}:{func}" if func else chain_fnames
                model = self.env[field.comodel_name]
                return model._read_group_empty_value(groupby_seq)
            return (
                self.env[field.comodel_name]
                if field.relational
                else self.env[self._name]
            )
        return False

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
        """Deprecated - Get the list of records in list view grouped by the given ``groupby`` fields.

        :param list domain: :ref:`A search domain <reference/orm/domains>`. Use an empty
                     list to match all records.
        :param list fields: list of fields present in the list view specified on the object.
                Each element is either 'field' (field name, using the default aggregation),
                or 'field:agg' (aggregate field with aggregation function 'agg'),
                or 'name:agg(field)' (aggregate field with 'agg' and return it as 'name').
                The possible aggregation functions are the ones provided by
                `PostgreSQL <https://www.postgresql.org/docs/current/static/functions-aggregate.html>`_
                and 'count_distinct', with the expected meaning.
        :param list groupby: list of groupby descriptions by which the records will be grouped.
                A groupby description is either a field (then it will be grouped by that field).
                For the dates an datetime fields, you can specify a granularity using the syntax 'field:granularity'.
                The supported granularities are 'hour', 'day', 'week', 'month', 'quarter' or 'year';
                Read_group also supports integer date parts:
                'year_number', 'quarter_number', 'month_number' 'iso_week_number', 'day_of_year', 'day_of_month',
                'day_of_week', 'hour_number', 'minute_number' and 'second_number'.
        :param int offset: optional number of groups to skip
        :param int limit: optional max number of groups to return
        :param str orderby: optional ``order by`` specification, for
                             overriding the natural sort ordering of the
                             groups, see also :meth:`~.search`
                             (supported only for many2one fields currently)
        :param bool lazy: if true, the results are only grouped by the first groupby and the
                remaining groupbys are put in the __context key.  If false, all the groupbys are
                done in one call.
        :return: list of dictionaries(one dictionary for each record) containing:

                    * the values of fields grouped by the fields in ``groupby`` argument
                    * __domain: list of tuples specifying the search criteria
                    * __context: dictionary with argument like ``groupby``
                    * __range: (date/datetime only) dictionary with field_name:granularity as keys
                        mapping to a dictionary with keys: "from" (inclusive) and "to" (exclusive)
                        mapping to a string representation of the temporal bounds of the group
        :rtype: [{'field_name_1': value, ...}, ...]
        :raise AccessError: if user is not allowed to access requested information
        """
        groupby = [groupby] if isinstance(groupby, str) else groupby
        lazy_groupby = groupby[:1] if lazy else groupby

        # Compatibility layer with _read_group, it should be remove in the second part of the refactoring
        # - Modify `groupby` default value 'month' into specific groupby specification
        # - Modify `fields` into aggregates specification of _read_group
        # - Modify the order to be compatible with the _read_group specification
        groupby = [groupby] if isinstance(groupby, str) else groupby
        lazy_groupby = groupby[:1] if lazy else groupby

        annotated_groupby = (
            {}
        )  # Key as the name in the result, value as the explicit groupby specification
        for group_spec in lazy_groupby:
            field_name, property_name, granularity = parse_read_group_spec(group_spec)
            if field_name not in self._fields:
                raise ValueError(
                    f"Invalid field {field_name!r} on model {self._name!r}"
                )
            field = self._fields[field_name]
            if property_name and field.type != "properties":
                raise ValueError(
                    f"Property name {property_name!r} has to be used on a property field."
                )
            if field.type in ("date", "datetime"):
                annotated_groupby[group_spec] = f"{field_name}:{granularity or 'month'}"
            else:
                annotated_groupby[group_spec] = group_spec

        annotated_aggregates = {  # Key as the name in the result, value as the explicit aggregate specification
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

            if fname:  # Manage this kind of specification : "field_min:min(field)"
                annotated_aggregates[name] = f"{fname}:{func}"
                continue
            if func:  # Manage this kind of specification : "field:min"
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

        if orderby:
            new_terms = []
            for order_term in orderby.split(","):
                order_term = order_term.strip()
                for key_name, annotated in itertools.chain(
                    reversed(annotated_groupby.items()),
                    annotated_aggregates.items(),
                ):
                    key_name = key_name.split(":")[0]
                    if order_term.startswith(f"{key_name} ") or key_name == order_term:
                        order_term = order_term.replace(key_name, annotated)
                        break
                new_terms.append(order_term)
            orderby = ",".join(new_terms)
        else:
            orderby = ",".join(annotated_groupby.values())

        domain = Domain(domain)
        rows = self._read_group(
            domain,
            annotated_groupby.values(),
            annotated_aggregates.values(),
            offset=offset,
            limit=limit,
            order=orderby,
        )
        rows_dict = [
            dict(
                zip(
                    itertools.chain(annotated_groupby, annotated_aggregates),
                    row, strict=False,
                )
            )
            for row in rows
        ]

        fill_temporal = self.env.context.get("fill_temporal")
        if (lazy_groupby and (rows_dict and fill_temporal)) or isinstance(
            fill_temporal, dict
        ):
            # fill_temporal = {} is equivalent to fill_temporal = True
            # if fill_temporal is a dictionary and there is no data, there is a chance that we
            # want to display empty columns anyway, so we should apply the fill_temporal logic
            if not isinstance(fill_temporal, dict):
                fill_temporal = {}
            # fill_temporal adds empty groups to fill date gaps — this may
            # produce more rows than ``limit``.  In practice, fill_temporal
            # is used by chart views which never set a limit.
            rows_dict = self._read_group_fill_temporal(
                rows_dict,
                lazy_groupby,
                annotated_aggregates,
                **fill_temporal,
            )

        if lazy_groupby and lazy:
            # Right now, read_group only fill results in lazy mode (by default).
            # If you need to have the empty groups in 'eager' mode, then the
            # method _read_group_fill_results need to be completely reimplemented
            # in a sane way
            # fill_results adds empty groups for missing groupby values — this
            # may produce more rows than ``limit``.  Same as fill_temporal:
            # fill views (kanban, chart) don't use limits.
            rows_dict = self._read_group_fill_results(
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
