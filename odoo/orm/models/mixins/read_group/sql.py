import typing

from odoo.exceptions import AccessError, UserError
from odoo.libs.debug_log import DebugLog
from odoo.tools import SQL, Query, get_lang, ormcache
from odoo.tools.translate import _

from .... import decorators as api
from ....constants import (
    READ_GROUP_AGGREGATE,
    READ_GROUP_ALL_TIME_GRANULARITY,
    READ_GROUP_NUMBER_GRANULARITY,
    READ_GROUP_THROUGH_RECORDS,
    READ_GROUP_TIME_GRANULARITY,
    SQL_ORDER_DIR,
    SQL_ORDER_NULLS,
)
from ....fields.temporal import Date
from ....parsing import parse_read_group_spec, regex_order_part_read_group
from ....primitives import SQL_OPERATORS
from .._model_stubs import _ModelStubs

if typing.TYPE_CHECKING:
    from ...._typing import BaseModel
    from ....fields import Field

_debug = DebugLog(__name__)


class _ReadGroupSQLMixin(_ModelStubs):
    __slots__ = ()

    def _read_group_select_sum_currency(self, field, fname: str, query: Query) -> SQL:
        if not field.is_monetary:
            raise ValueError(
                f'Aggregator "sum_currency" only works on currency field for {fname!r}'
            )

        CurrencyRate = self.env["res.currency.rate"]
        rate_subquery_table = SQL(
            """(SELECT DISTINCT ON (%(currency_field_sql)s) %(currency_field_sql)s, %(rate_field_sql)s
                FROM "res_currency_rate"
                WHERE %(company_field_sql)s IS NULL OR %(company_field_sql)s = %(company_id)s
                ORDER BY
                    %(currency_field_sql)s,
                    %(company_field_sql)s,
                    CASE WHEN %(name_field_sql)s <= %(today)s THEN %(name_field_sql)s END DESC NULLS LAST,
                    CASE WHEN %(name_field_sql)s > %(today)s THEN %(name_field_sql)s END ASC)
            """,
            currency_field_sql=CurrencyRate._field_to_sql(
                CurrencyRate._table, "currency_id"
            ),
            rate_field_sql=CurrencyRate._field_to_sql(CurrencyRate._table, "rate"),
            company_field_sql=CurrencyRate._field_to_sql(
                CurrencyRate._table, "company_id"
            ),
            company_id=self.env.company.root_id.id,
            name_field_sql=CurrencyRate._field_to_sql(CurrencyRate._table, "name"),
            today=Date.context_today(typing.cast("BaseModel", self)),
        )
        currency_field_name = field.get_currency_field(self)
        assert currency_field_name is not None
        alias_rate = query.get_table_alias(self._table, f"{currency_field_name}__rates")
        currency_field_sql = self._field_to_sql(self._table, currency_field_name, query)
        condition = SQL(
            "%s = %s",
            currency_field_sql,
            SQL.identifier(alias_rate, "currency_id"),
        )
        query.add_join("LEFT JOIN", alias_rate, rate_subquery_table, condition)
        _debug.logic(
            "read_group.sum_currency_join",
            model=self._name,
            field=fname,
            currency_field=currency_field_name,
            company=self.env.company.root_id.id,
        )

        return SQL(
            "SUM(%s / COALESCE(%s, 1.0))",
            self._field_to_sql(self._table, fname, query),
            SQL.identifier(alias_rate, "rate"),
        )

    def _aggregates_through_records(self, field, func: str) -> bool:
        return (
            not field.store
            and not field.related
            and bool(field.compute)
            and func in READ_GROUP_THROUGH_RECORDS
        )

    def _read_group_select(self, aggregate_spec: str, query: Query) -> SQL:
        if aggregate_spec == "__count":
            return SQL("COUNT(*)")

        fname, property_name, func = parse_read_group_spec(aggregate_spec)

        if property_name:
            raise ValueError(
                f"Invalid {aggregate_spec!r}, this dot notation is not supported"
            )

        if fname not in self._fields:
            raise ValueError(
                f"Invalid field {fname!r} on model {self._name!r} for {aggregate_spec!r}."
            )
        if not func:
            raise ValueError(f"Aggregate method is mandatory for {fname!r}")

        field = self._fields[fname]
        self._check_field_access(field, "read")
        if self._aggregates_through_records(field, func):
            _debug.logic(
                "read_group.select.through_records",
                model=self._name,
                aggregate=aggregate_spec,
            )
            return READ_GROUP_AGGREGATE["recordset"](
                self._table, SQL.identifier(self._table, "id")
            )
        if func == "sum_currency":
            return self._read_group_select_sum_currency(field, fname, query)

        if func not in READ_GROUP_AGGREGATE:
            raise ValueError(
                f"Invalid aggregate method {func!r} for {aggregate_spec!r}."
            )

        if func == "recordset" and not (field.relational or fname == "id"):
            raise ValueError(
                f"Aggregate method {func!r} can be only used on relational field (or id) (for {aggregate_spec!r})."
            )

        sql_field = self._field_to_sql(self._table, fname, query)
        if field.is_boolean:
            # a never-written boolean is NULL in the column and False to the
            # ORM; BOOL_AND, COUNT and ARRAY_AGG would skip or leak the NULL
            sql_field = SQL("COALESCE(%s, FALSE)", sql_field)
        return READ_GROUP_AGGREGATE[func](self._table, sql_field)

    @api.model
    @ormcache("field_name", "self.env.su", "self.env.user._get_group_ids()")
    def _is_field_groupable(self, field_name: str) -> bool:
        field = self._fields[field_name]
        groupby = field_name if not field.is_temporal else f"{field_name}:month"
        try:
            query = self._as_query(ordered=False)
            self._read_group_groupby(self._table, groupby, query)
            groupable = True
        except ValueError, AccessError, NotImplementedError:
            groupable = False
        _debug.perf.count(
            "read_group.field_groupable_probed",
            model=self._name,
            field=field_name,
            groupable=groupable,
            su=self.env.su,
        )
        return groupable

    def _read_group_groupby_many2one_path(
        self,
        alias: str,
        fname: str,
        field,
        seq_fnames: str,
        granularity,
        groupby_spec: str,
        query: Query,
    ) -> SQL:
        if not field.is_many2one:
            raise ValueError(
                f"Only many2one path is accepted for the {groupby_spec!r} groupby spec"
            )

        comodel = self.env[field.comodel_name]
        coquery = comodel.with_context(active_test=False)._search([])
        if self.env.su or not coquery.where_clause:
            coalias = query.get_table_alias(alias, fname)
        else:
            coalias = query.get_table_alias(alias, f"{fname}__{self.env.uid}")
        condition = SQL(
            "%s = %s",
            self._field_to_sql(alias, fname, query),
            SQL.identifier(coalias, "id"),
        )
        if coquery.where_clause:
            subselect_arg = SQL("%s.*", SQL.identifier(comodel._table))
            query.add_join(
                "LEFT JOIN",
                coalias,
                coquery.subselect(subselect_arg),
                condition,
            )
        else:
            query.add_join("LEFT JOIN", coalias, comodel._table, condition)
        return comodel._read_group_groupby(
            coalias,
            f"{seq_fnames}:{granularity}" if granularity else seq_fnames,
            query,
        )

    def _read_group_groupby_many2many(
        self, alias: str, field, groupby_spec: str, query: Query
    ) -> SQL:
        if field.related and not field.store:
            access_model, field, alias = self._traverse_related_sql(alias, field, query)
        else:
            access_model = self

        access_model._check_field_access(field, "read")

        if not field.store:
            raise ValueError(f"Group by non-stored many2many field: {groupby_spec!r}")
        assert (
            field.relation is not None
            and field.column1 is not None
            and field.column2 is not None
        )
        codomain = field.get_comodel_domain(self)
        comodel = self.env[field.comodel_name].with_context(**field.context)
        coquery = comodel._search(codomain, bypass_access=field.bypass_search_access)
        rel_alias = query.get_table_alias(alias, field.name)
        condition = SQL(
            "%s = %s",
            SQL.identifier(alias, "id"),
            SQL.identifier(rel_alias, field.column1),
        )
        if coquery.where_clause:
            condition = SQL(
                "%s AND %s IN %s",
                condition,
                SQL.identifier(rel_alias, field.column2),
                coquery.subselect(),
            )
        query.add_join("LEFT JOIN", rel_alias, field.relation, condition)
        _debug.logic(
            "read_group.m2m_join",
            model=self._name,
            field=field.name,
            relation=field.relation,
            comodel_filtered=bool(coquery.where_clause),
            bypass_access=field.bypass_search_access,
        )
        return SQL.identifier(rel_alias, field.column2)

    def _read_group_groupby(self, alias: str, groupby_spec: str, query: Query) -> SQL:
        fname, seq_fnames, granularity = parse_read_group_spec(groupby_spec)
        if fname not in self._fields:
            raise ValueError(f"Invalid field {fname!r} on model {self._name!r}")

        field = self._fields[fname]
        self._check_field_access(field, "read")
        if field.group_by_field:
            return self._read_group_groupby(
                alias, field.group_by_field + groupby_spec[len(fname) :], query
            )
        if field.group_by_sql and not seq_fnames and not granularity:
            _debug.logic(
                "read_group.groupby",
                model=self._name,
                groupby=groupby_spec,
                field_type=field.type,
                shape="sql_hook",
                hook=field.group_by_sql,
            )
            return getattr(self, field.group_by_sql)(field, alias, query)

        _debug.logic(
            "read_group.groupby",
            model=self._name,
            groupby=groupby_spec,
            field_type=field.type,
            shape="properties"
            if field.is_properties
            else "many2one_path"
            if seq_fnames
            else "many2many"
            if field.is_many2many
            else "temporal"
            if field.is_temporal
            else "column",
            granularity=granularity or None,
        )
        if field.is_properties:
            sql_expr = self._read_group_groupby_properties(
                alias, field, seq_fnames or "", query
            )

        elif seq_fnames:
            return self._read_group_groupby_many2one_path(
                alias, fname, field, seq_fnames, granularity, groupby_spec, query
            )

        elif granularity and not (field.is_temporal or field.is_properties):
            raise ValueError(
                f"Granularity set on a no-datetime field or property: {groupby_spec!r}"
            )

        elif field.is_many2many:
            return self._read_group_groupby_many2many(alias, field, groupby_spec, query)

        else:
            sql_expr = self._field_to_sql(alias, fname, query)

        if field.is_temporal or (field.is_properties and granularity):
            sql_expr = self._read_group_groupby_temporal(
                sql_expr,
                field,
                granularity or "",
                seq_fnames or "",
                groupby_spec,
                alias,
                query,
            )
        elif field.is_boolean:
            sql_expr = SQL("COALESCE(%s, FALSE)", sql_expr)
        elif field.is_text:
            sql_expr = SQL("NULLIF(%s, '')", sql_expr)

        return sql_expr.inlined(self.env.cr)

    def _read_group_groupby_temporal(
        self,
        sql_expr: SQL,
        field: Field,
        granularity: str,
        seq_fnames: str,
        groupby_spec: str,
        alias: str,
        query: Query,
    ) -> SQL:
        if not granularity:
            raise ValueError(
                f"Granularity not set on a date(time) field: {groupby_spec!r}"
            )
        if granularity not in READ_GROUP_ALL_TIME_GRANULARITY:
            raise ValueError(
                f"Granularity specification isn't correct: {granularity!r}"
            )

        prop_type = None
        if field.is_properties:
            definition = self.get_property_definition(f"{field.name}.{seq_fnames}")
            prop_type = definition.get("type")
            if prop_type == "datetime":
                if tz_name := self.env.context.get("tz"):
                    if tz_name in self.env.backend.timezone_names(self.env):
                        sql_expr = SQL(
                            "timezone(%s, timezone('UTC', %s))",
                            SQL.literal(tz_name),
                            sql_expr,
                        )
            if granularity in READ_GROUP_NUMBER_GRANULARITY:
                sql_expr = SQL(
                    "date_part(%s, %s)",
                    SQL.literal(READ_GROUP_NUMBER_GRANULARITY[granularity]),
                    sql_expr,
                )
        elif granularity in READ_GROUP_NUMBER_GRANULARITY:
            sql_expr = field.property_to_sql(sql_expr, granularity, self, alias, query)
        elif field.is_datetime:
            sql_expr = field.property_to_sql(sql_expr, "tz", self, alias, query)

        if granularity == "week":
            first_week_day = int(get_lang(self.env).week_start) - 1
            days_offset = first_week_day and 7 - first_week_day
            interval = SQL.literal(f"-{days_offset} DAY")
            sql_expr = SQL(
                "(date_trunc('week', %s::timestamp - INTERVAL %s) + INTERVAL %s)",
                sql_expr,
                interval,
                interval,
            )
        elif granularity in READ_GROUP_TIME_GRANULARITY:
            sql_expr = SQL(
                "date_trunc(%s, %s::timestamp)",
                SQL.literal(granularity),
                sql_expr,
            )

        is_date = field.is_date or (field.is_properties and prop_type == "date")
        if is_date and granularity not in READ_GROUP_NUMBER_GRANULARITY:
            # a date property groups by a date, as a Date column does; the
            # in-memory backend answers the same
            sql_expr = SQL("%s::date", sql_expr)

        _debug.logic(
            "read_group.groupby_temporal",
            model=self._name,
            groupby=groupby_spec,
            granularity=granularity,
            tz=self.env.context.get("tz") if field.is_datetime else None,
            week_start=int(get_lang(self.env).week_start)
            if granularity == "week"
            else None,
        )
        return sql_expr

    def _read_group_having(self, having_domain: list, query: Query) -> SQL:
        if not having_domain:
            return SQL.EMPTY

        stack: list[SQL] = []
        SUPPORTED = ("in", "not in", "<", ">", "<=", ">=", "=", "!=")
        try:
            for item in reversed(having_domain):
                if item == "!":
                    stack.append(SQL("(NOT %s)", stack.pop()))
                elif item == "&":
                    stack.append(SQL("(%s AND %s)", stack.pop(), stack.pop()))
                elif item == "|":
                    stack.append(SQL("(%s OR %s)", stack.pop(), stack.pop()))
                elif isinstance(item, (list, tuple)) and len(item) == 3:
                    left, operator, right = item
                    if operator not in SUPPORTED:
                        raise ValueError(
                            f"Invalid having clause {item!r}: supported comparators are {SUPPORTED}"
                        )
                    sql_left = self._read_group_select(left, query)
                    if operator in ("in", "not in"):
                        if isinstance(right, (list, set, frozenset)):
                            right = tuple(right)
                        if isinstance(right, tuple) and not right:
                            stack.append(
                                SQL("TRUE") if operator == "not in" else SQL("FALSE")
                            )
                            continue
                    stack.append(
                        SQL("%s%s%s", sql_left, SQL_OPERATORS[operator], right)
                    )
                else:
                    raise ValueError(
                        f"Invalid having clause {item!r}: it should be a domain-like clause"
                    )

            while len(stack) > 1:
                stack.append(SQL("(%s AND %s)", stack.pop(), stack.pop()))
            return stack[0]
        except IndexError:
            raise ValueError(f"Invalid having clause {having_domain!r}") from None

    def _read_group_orderby_many2one(
        self,
        term: str,
        direction: str,
        nulls: str,
        groupby_terms: dict[str, SQL],
        orderby_terms: list,
        query: Query,
        order_field: str | None = None,
    ) -> None:
        query._any_value_orderby = True
        query._collect_order_groupby = True
        try:
            sql_order = self._order_to_sql(
                f"{order_field or term} {direction} {nulls}", query
            )
        finally:
            query._any_value_orderby = False
            query._collect_order_groupby = False
        if sql_order:
            orderby_terms.append(sql_order)
            if query._order_groupby:
                groupby_terms[term] = SQL(", ").join(
                    [groupby_terms[term], *query._order_groupby]
                )
                query._order_groupby.clear()

    def _read_group_orderby_day_of_week(
        self, term: str, groupby_terms: dict[str, SQL], sql_direction, sql_nulls
    ) -> SQL:
        first_week_day = int(get_lang(self.env).week_start)
        sql_expr = SQL(
            "mod(7 - %s + %s::int, 7)",
            first_week_day,
            groupby_terms[term],
        )
        return SQL("%s %s %s", sql_expr, sql_direction, sql_nulls)

    def _read_group_orderby(
        self, order: str | None, groupby_terms: dict[str, SQL], query: Query
    ) -> SQL:
        if order:
            traverse_many2one = True
        else:
            order = ",".join(groupby_terms)
            traverse_many2one = False

        if not order:
            return SQL.EMPTY

        _debug.logic(
            "read_group.orderby",
            model=self._name,
            order=order,
            from_groupby=not traverse_many2one,
            groupby_terms=len(groupby_terms),
        )
        orderby_terms = []

        for order_part in order.split(","):
            order_match = regex_order_part_read_group.fullmatch(order_part)
            if not order_match:
                raise ValueError(f"Invalid order {order!r} for _read_group()")
            term = order_match["term"]
            direction = (order_match["direction"] or "ASC").upper()
            nulls = (order_match["nulls"] or "").upper()

            sql_direction = SQL_ORDER_DIR.get(direction, SQL.EMPTY)
            sql_nulls = SQL_ORDER_NULLS.get(nulls, SQL.EMPTY)

            if term not in groupby_terms:
                try:
                    sql_expr = self._read_group_select(term, query)
                except ValueError as e:
                    raise ValueError(
                        f"Order term {order_part!r} is not a valid aggregate nor valid groupby"
                    ) from e
                orderby_terms.append(
                    SQL("%s %s %s", sql_expr, sql_direction, sql_nulls)
                )
                continue

            field = self._fields.get(term)
            if field and field.group_by_field:
                field = self._fields[field.group_by_field]
            spec_granularity = parse_read_group_spec(term)[2]
            if (
                traverse_many2one
                and field
                and field.is_many2one
                and self.env[field.comodel_name]._order != "id"
            ):
                self._read_group_orderby_many2one(
                    term,
                    direction,
                    nulls,
                    groupby_terms,
                    orderby_terms,
                    query,
                    order_field=field.name,
                )

            elif spec_granularity == "day_of_week":
                orderby_terms.append(
                    self._read_group_orderby_day_of_week(
                        term, groupby_terms, sql_direction, sql_nulls
                    )
                )
            else:
                sql_expr = groupby_terms[term]
                orderby_terms.append(
                    SQL("%s %s %s", sql_expr, sql_direction, sql_nulls)
                )

        return SQL(", ").join(orderby_terms)

    def _get_property_comodel(self, definition: dict, property_name: str):
        comodel = self.env.get(definition.get("comodel"))
        if comodel is None or comodel._transient or comodel._abstract:
            raise UserError(
                _(
                    'You cannot use "%(property_name)s" because the linked "%(model_name)s" model doesn\'t exist or is invalid',
                    property_name=definition.get("string", property_name),
                    model_name=definition.get("comodel"),
                )
            )
        return comodel

    def _read_group_property_collection(
        self,
        alias: str,
        fname: str,
        property_name: str,
        definition: dict,
        property_type: str,
        sql_property: SQL,
        query: Query,
    ) -> SQL:
        property_alias = query.get_table_alias(alias, f"{fname}_{property_name}")
        sql_property = SQL(
            """ CASE
                    WHEN jsonb_typeof(%(property)s) = 'array'
                    THEN %(property)s
                    ELSE '[]'::jsonb
                 END """,
            property=sql_property,
        )
        if property_type == "tags":
            tags = [tag[0] for tag in definition.get("tags") or []]
            condition = SQL(
                "%s->>0 = ANY(%s::text[])",
                SQL.identifier(property_alias),
                tags,
            )
        else:
            comodel = self._get_property_comodel(definition, property_name)

            condition = SQL(
                "%s::int IN (SELECT id FROM %s)",
                SQL.identifier(property_alias),
                SQL.identifier(comodel._table),
            )

        query.add_join(
            "LEFT JOIN",
            property_alias,
            SQL("jsonb_array_elements(%s)", sql_property),
            condition,
        )

        return SQL.identifier(property_alias)

    def _read_group_property_selection(
        self,
        alias: str,
        fname: str,
        property_name: str,
        definition: dict,
        sql_property: SQL,
        query: Query,
    ) -> SQL:
        options = [option[0] for option in definition.get("selection") or ()]

        property_alias = query.get_table_alias(alias, f"{fname}_{property_name}")
        query.add_join(
            "LEFT JOIN",
            property_alias,
            SQL(
                "(SELECT unnest(%s::text[]) %s)",
                options,
                SQL.identifier(property_alias),
            ),
            SQL("%s->>0 = %s", sql_property, SQL.identifier(property_alias)),
        )

        return SQL.identifier(property_alias)

    def _read_group_groupby_properties(
        self, alias: str, field: Field, property_name: str, query: Query
    ) -> SQL:
        fname = field.name
        definition = self.get_property_definition(f"{fname}.{property_name}")
        property_type = definition.get("type")
        sql_property = self._field_to_sql(alias, f"{fname}.{property_name}", query)
        _debug.logic(
            "read_group.property_groupby",
            model=self._name,
            field=fname,
            property=property_name,
            type=property_type,
        )

        if property_type in ("tags", "many2many"):
            return self._read_group_property_collection(
                alias,
                fname,
                property_name,
                definition,
                property_type,
                sql_property,
                query,
            )

        if property_type == "selection":
            return self._read_group_property_selection(
                alias, fname, property_name, definition, sql_property, query
            )

        if property_type == "many2one":
            comodel = self._get_property_comodel(definition, property_name)

            return SQL(
                """ CASE
                        WHEN jsonb_typeof(%(property)s) = 'number'
                         AND (%(property)s)::int IN (SELECT id FROM %(table)s)
                        THEN %(property)s
                        ELSE NULL
                     END """,
                property=sql_property,
                table=SQL.identifier(comodel._table),
            )

        elif property_type == "date":
            return SQL(
                """ CASE
                        WHEN jsonb_typeof(%(property)s) = 'string'
                        THEN (%(property)s->>0)::DATE
                        ELSE NULL
                     END """,
                property=sql_property,
            )

        elif property_type == "datetime":
            return SQL(
                """ CASE
                        WHEN jsonb_typeof(%(property)s) = 'string'
                        THEN to_timestamp(%(property)s->>0, 'YYYY-MM-DD HH24:MI:SS')
                        ELSE NULL
                     END """,
                property=sql_property,
            )

        elif property_type == "html":
            raise UserError(_("Grouping by HTML properties is not supported."))

        return SQL("COALESCE(%s, 'false')", sql_property)
