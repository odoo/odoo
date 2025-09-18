"""
SQL generation methods for read_group operations.

Contains the _ReadGroupSQLMixin with methods that generate SQL expressions
for SELECT (aggregation), GROUP BY, HAVING, and ORDER BY clauses.
"""

import typing

from odoo.exceptions import UserError
from odoo.tools import SQL, Query

from ....constants import (
    READ_GROUP_AGGREGATE,
    READ_GROUP_ALL_TIME_GRANULARITY,
    READ_GROUP_NUMBER_GRANULARITY,
    READ_GROUP_TIME_GRANULARITY,
)
from ....parsing import parse_read_group_spec, regex_order_part_read_group
from ....primitives import SQL_OPERATORS

if typing.TYPE_CHECKING:
    from ....fields import Field

from odoo.tools import get_lang
from odoo.tools.translate import _

from ....fields.temporal import _get_all_timezones_set
from ..search import _SQL_DIR, _SQL_NULLS


class _ReadGroupSQLMixin:
    """SQL generation methods for read_group.

    Generates SQL expressions for aggregation (SELECT), grouping (GROUP BY),
    filtering (HAVING), and ordering (ORDER BY).
    """

    __slots__ = ()

    # Type hints for attributes provided by BaseModel (runtime)
    _fields: dict
    _table: str
    _name: str
    env: typing.Any
    pool: typing.Any

    def _read_group_select(self, aggregate_spec: str, query: Query) -> SQL:
        """Return <SQL expression> corresponding to the given aggregation.
        The method also checks whether the fields used in the aggregate are
        accessible for reading.
        """
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
        if func == "sum_currency":
            if field.type != "monetary":
                raise ValueError(
                    f'Aggregator "sum_currency" only works on currency field for {fname!r}'
                )

            from ....fields.temporal import Date

            CurrencyRate = self.env["res.currency.rate"]
            rate_subquery_table = SQL(
                """(SELECT DISTINCT ON (%(currency_field_sql)s) %(currency_field_sql)s, %(rate_field_sql)s
                    FROM "res_currency_rate"
                    WHERE %(company_field_sql)s IS NULL OR %(company_field_sql)s = %(company_id)s
                    ORDER BY
                        %(currency_field_sql)s,
                        %(company_field_sql)s,
                        CASE WHEN %(name_field_sql)s <= %(today)s THEN %(name_field_sql)s END DESC,
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
                today=Date.context_today(self),
            )
            currency_field_name = field.get_currency_field(self)
            alias_rate = query.make_alias(self._table, f"{currency_field_name}__rates")
            currency_field_sql = self._field_to_sql(
                self._table, currency_field_name, query
            )
            condition = SQL(
                "%s = %s",
                currency_field_sql,
                SQL.identifier(alias_rate, "currency_id"),
            )
            query.add_join("LEFT JOIN", alias_rate, rate_subquery_table, condition)

            return SQL(
                "SUM(%s / COALESCE(%s, 1.0))",
                self._field_to_sql(self._table, fname, query),
                SQL.identifier(alias_rate, "rate"),
            )

        if func not in READ_GROUP_AGGREGATE:
            raise ValueError(
                f"Invalid aggregate method {func!r} for {aggregate_spec!r}."
            )

        if func == "recordset" and not (field.relational or fname == "id"):
            raise ValueError(
                f"Aggregate method {func!r} can be only used on relational field (or id) (for {aggregate_spec!r})."
            )

        sql_field = self._field_to_sql(self._table, fname, query)
        return READ_GROUP_AGGREGATE[func](self._table, sql_field)

    def _read_group_groupby(self, alias: str, groupby_spec: str, query: Query) -> SQL:
        """Return <SQL expression> corresponding to the given groupby element.
        The method also checks whether the fields used in the groupby are
        accessible for reading.
        """
        fname, seq_fnames, granularity = parse_read_group_spec(groupby_spec)
        if fname not in self._fields:
            raise ValueError(f"Invalid field {fname!r} on model {self._name!r}")

        field = self._fields[fname]

        if field.type == "properties":
            sql_expr = self._read_group_groupby_properties(
                alias, field, seq_fnames, query
            )

        elif seq_fnames:
            if field.type != "many2one":
                raise ValueError(
                    f"Only many2one path is accepted for the {groupby_spec!r} groupby spec"
                )

            comodel = self.env[field.comodel_name]
            coquery = comodel.with_context(active_test=False)._search([])
            if self.env.su or not coquery.where_clause:
                coalias = query.make_alias(alias, fname)
            else:
                coalias = query.make_alias(alias, f"{fname}__{self.env.uid}")
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

        elif granularity and field.type not in (
            "datetime",
            "date",
            "properties",
        ):
            raise ValueError(
                f"Granularity set on a no-datetime field or property: {groupby_spec!r}"
            )

        elif field.type == "many2many":
            if field.related and not field.store:
                _model, field, alias = self._traverse_related_sql(alias, field, query)

            if not field.store:
                raise ValueError(
                    f"Group by non-stored many2many field: {groupby_spec!r}"
                )
            # special case for many2many fields: prepare a query on the comodel
            # and inject the query as an extra condition of the left join
            codomain = field.get_comodel_domain(self)
            comodel = self.env[field.comodel_name].with_context(**field.context)
            coquery = comodel._search(
                codomain, bypass_access=field.bypass_search_access
            )
            # LEFT JOIN {field.relation} AS rel_alias ON
            #     alias.id = rel_alias.{field.column1}
            #     AND rel_alias.{field.column2} IN ({coquery})
            rel_alias = query.make_alias(alias, field.name)
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
            return SQL.identifier(rel_alias, field.column2)

        else:
            sql_expr = self._field_to_sql(alias, fname, query)

        if field.type in ("datetime", "date") or (
            field.type == "properties" and granularity
        ):
            if not granularity:
                raise ValueError(
                    f"Granularity not set on a date(time) field: {groupby_spec!r}"
                )
            if granularity not in READ_GROUP_ALL_TIME_GRANULARITY:
                raise ValueError(
                    f"Granularity specification isn't correct: {granularity!r}"
                )

            if field.type == "properties":
                # For properties, _read_group_groupby_properties already
                # built a proper DATE/TIMESTAMP CASE expression.  Apply
                # date operations directly instead of going through
                # Properties.property_to_sql (which treats the argument as
                # a JSON key, not a granularity).
                definition = self.get_property_definition(f"{field.name}.{seq_fnames}")
                prop_type = definition.get("type")
                if prop_type == "datetime":
                    if tz_name := self.env.context.get("tz"):
                        if tz_name in _get_all_timezones_set():
                            sql_expr = SQL(
                                "timezone('%s', timezone('UTC', %%s))" % tz_name,
                                sql_expr,
                            )
                if granularity in READ_GROUP_NUMBER_GRANULARITY:
                    pg_granularity = READ_GROUP_NUMBER_GRANULARITY[granularity]
                    sql_expr = SQL("date_part('%s', %%s)" % pg_granularity, sql_expr)
            elif granularity in READ_GROUP_NUMBER_GRANULARITY:
                sql_expr = field.property_to_sql(
                    sql_expr, granularity, self, alias, query
                )
            elif field.type == "datetime":
                # set the timezone only
                sql_expr = field.property_to_sql(sql_expr, "tz", self, alias, query)

            if granularity == "week":
                # first_week_day: 0=Monday, 1=Tuesday, ...
                first_week_day = int(get_lang(self.env).week_start) - 1
                days_offset = first_week_day and 7 - first_week_day
                # Embed interval as SQL literal for GROUP BY consistency:
                # with server-side binding, bound params get unique $N
                # numbers, making SELECT and GROUP BY expressions differ.
                interval = f"-{days_offset} DAY"
                sql_expr = SQL(
                    "(date_trunc('week', %%s::timestamp - INTERVAL '%s') + INTERVAL '%s')"
                    % (interval, interval),
                    sql_expr,
                )
            elif granularity in READ_GROUP_TIME_GRANULARITY:
                # Embed granularity as SQL literal for GROUP BY consistency.
                sql_expr = SQL(
                    "date_trunc('%s', %%s::timestamp)" % granularity, sql_expr
                )

            # If the granularity is a part number, the result is a number (double) so no conversion is needed
            if (
                field.type == "date"
                and granularity not in READ_GROUP_NUMBER_GRANULARITY
            ):
                # If the granularity uses date_trunc, we need to convert the timestamp back to a date.
                sql_expr = SQL("%s::date", sql_expr)

        elif field.type == "boolean":
            sql_expr = SQL("COALESCE(%s, FALSE)", sql_expr)

        return sql_expr

    def _read_group_having(self, having_domain: list, query: Query) -> SQL:
        """Return <SQL expression> corresponding to the having domain."""
        if not having_domain:
            return SQL.EMPTY

        stack: list[SQL] = []
        SUPPORTED = ("in", "not in", "<", ">", "<=", ">=", "=", "!=")
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
                stack.append(SQL("%s%s%s", sql_left, SQL_OPERATORS[operator], right))
            else:
                raise ValueError(
                    f"Invalid having clause {item!r}: it should be a domain-like clause"
                )

        while len(stack) > 1:
            stack.append(SQL("(%s AND %s)", stack.pop(), stack.pop()))

        return stack[0]

    def _read_group_orderby(
        self, order: str, groupby_terms: dict[str, SQL], query: Query
    ) -> SQL:
        """Return (<SQL expression>, <SQL expression>)
        corresponding to the given order and groupby terms.

        Note: this method may change groupby_terms

        :param order: the order specification
        :param groupby_terms: the group by terms mapping ({spec: sql_expression})
        :param query: The query we are building
        """
        if order:
            traverse_many2one = True
        else:
            order = ",".join(groupby_terms)
            traverse_many2one = False

        if not order:
            return SQL.EMPTY

        orderby_terms = []

        for order_part in order.split(","):
            order_match = regex_order_part_read_group.fullmatch(order_part)
            if not order_match:
                raise ValueError(f"Invalid order {order!r} for _read_group()")
            term = order_match["term"]
            direction = (order_match["direction"] or "ASC").upper()
            nulls = (order_match["nulls"] or "").upper()

            sql_direction = _SQL_DIR.get(direction, SQL.EMPTY)
            sql_nulls = _SQL_NULLS.get(nulls, SQL.EMPTY)

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
            __, __, granularity = parse_read_group_spec(term)
            if (
                traverse_many2one
                and field
                and field.type == "many2one"
                and self.env[field.comodel_name]._order != "id"
            ):
                # Use ANY_VALUE() (PG16+) for ORDER BY columns that are
                # functionally dependent on the GROUP BY column. This avoids
                # adding comodel fields (e.g., partner.name) to GROUP BY
                # when ordering by a many2one with custom _order.
                # Disabled for GROUPING SETS: the same ORDER BY serves
                # multiple sets, and sets without the many2one field would
                # get arbitrary values from ANY_VALUE().
                if not query._grouping_sets:
                    query._any_value_orderby = True
                try:
                    sql_order = self._order_to_sql(f"{term} {direction} {nulls}", query)
                finally:
                    query._any_value_orderby = False
                if sql_order:
                    orderby_terms.append(sql_order)
                    if query._order_groupby:
                        # Fallback for overridden _order_to_sql that doesn't
                        # check _any_value_orderby (e.g., addon overrides).
                        groupby_terms[term] = SQL(", ").join(
                            [groupby_terms[term], *query._order_groupby]
                        )
                        query._order_groupby.clear()

            elif granularity == "day_of_week":
                """
                Day offset relative to the first day of week in the user lang
                formula: ((7 - first_week_day) + day_in_SQL) % 7

                               | week starts on
                           SQL | mon   sun   sat
                               |  1  |  7  |  6   <-- first_week_day (in odoo)
                          -----|-----------------
                    mon     1  |  0  |  1  |  2
                    tue     2  |  1  |  2  |  3
                    wed     3  |  2  |  3  |  4
                    thu     4  |  3  |  4  |  5
                    fri     5  |  4  |  5  |  6
                    sat     6  |  5  |  6  |  0
                    sun     0  |  6  |  0  |  1
                """
                first_week_day = int(get_lang(self.env).week_start)
                sql_expr = SQL(
                    "mod(7 - %s + %s::int, 7)",
                    first_week_day,
                    groupby_terms[term],
                )
                orderby_terms.append(
                    SQL("%s %s %s", sql_expr, sql_direction, sql_nulls)
                )
            else:
                sql_expr = groupby_terms[term]
                orderby_terms.append(
                    SQL("%s %s %s", sql_expr, sql_direction, sql_nulls)
                )

        return SQL(", ").join(orderby_terms)

    def _read_group_groupby_properties(
        self, alias: str, field: Field, property_name: str, query: Query
    ) -> SQL:
        fname = field.name
        definition = self.get_property_definition(f"{fname}.{property_name}")
        property_type = definition.get("type")
        sql_property = self._field_to_sql(alias, f"{fname}.{property_name}", query)

        # JOIN on the JSON array
        if property_type in ("tags", "many2many"):
            property_alias = query.make_alias(alias, f"{fname}_{property_name}")
            sql_property = SQL(
                """ CASE
                        WHEN jsonb_typeof(%(property)s) = 'array'
                        THEN %(property)s
                        ELSE '[]'::jsonb
                     END """,
                property=sql_property,
            )
            if property_type == "tags":
                # ignore invalid tags
                tags = [tag[0] for tag in definition.get("tags") or []]
                # `->>0 : convert "JSON string" into string
                condition = SQL(
                    "%s->>0 = ANY(%s::text[])",
                    SQL.identifier(property_alias),
                    tags,
                )
            else:
                comodel = self.env.get(definition.get("comodel"))
                if comodel is None or comodel._transient or comodel._abstract:
                    raise UserError(
                        _(
                            'You cannot use "%(property_name)s" because the linked "%(model_name)s" model doesn\'t exist or is invalid',
                            property_name=definition.get("string", property_name),
                            model_name=definition.get("comodel"),
                        )
                    )

                # check the existences of the many2many
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

        elif property_type == "selection":
            options = [option[0] for option in definition.get("selection") or ()]

            # check the existence of the option
            property_alias = query.make_alias(alias, f"{fname}_{property_name}")
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

        elif property_type == "many2one":
            comodel = self.env.get(definition.get("comodel"))
            if comodel is None or comodel._transient or comodel._abstract:
                raise UserError(
                    _(
                        'You cannot use "%(property_name)s" because the linked "%(model_name)s" model doesn\'t exist or is invalid',
                        property_name=definition.get("string", property_name),
                        model_name=definition.get("comodel"),
                    )
                )

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

        # if the key is not present in the dict, fallback to false instead of none
        return SQL("COALESCE(%s, 'false')", sql_property)
