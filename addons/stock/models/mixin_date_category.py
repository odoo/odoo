from datetime import UTC, timedelta

from odoo import api, fields, models
from odoo.fields import Domain
from odoo.tools import SQL
from odoo.tools.translate import LazyTranslate

from ..tools import debug_log as dbg

_lt = LazyTranslate(__name__)


class MixinDateCategory(models.AbstractModel):
    _name = "mixin.date.category"
    _description = "Relative Day Category"

    DATE_CATEGORIES = (
        ("before", "yesterday", _lt("Before"), "past"),
        ("yesterday", "today", _lt("Yesterday"), "past"),
        ("today", "day_1", _lt("Today"), "present"),
        ("day_1", "day_2", _lt("Tomorrow"), "future"),
        ("day_2", "day_3", _lt("The day after tomorrow"), "future"),
        ("after", None, _lt("After"), "future"),
    )

    _date_category_field = None

    date_category = fields.Selection(
        selection="_selection_date_category",
        search="_search_date_category",
        store=False,
        readonly=True,
    )

    def _search_date_category(self, operator, value):
        if operator != "in":
            return NotImplemented
        if not self._date_category_field:
            raise NotImplementedError(
                f"{self._name} inherits mixin.date.category without setting "
                f"_date_category_field, so there is no column to bucket."
            )
        return Domain.OR(
            domain
            for item in value
            if (
                domain := self.get_domain_date_category(self._date_category_field, item)
            )
        )

    @api.model
    def _get_date_category_boundaries(self):
        start_today = fields.Datetime.context_timestamp(
            self.env.user,
            fields.Datetime.now(),
        ).replace(hour=0, minute=0, second=0, microsecond=0)
        return {
            "yesterday": start_today + timedelta(days=-1),
            "today": start_today,
            "day_1": start_today + timedelta(days=1),
            "day_2": start_today + timedelta(days=2),
            "day_3": start_today + timedelta(days=3),
        }

    @api.model
    def _selection_date_category(self):
        return [
            (key, self.env._(label))  # pylint: disable=gettext-variable
            for key, _upper, label, _kind in self.DATE_CATEGORIES
        ]

    @api.model
    def _get_date_category_boundaries_naive(self):
        return {
            key: value.astimezone(UTC).replace(tzinfo=None)
            for key, value in self._get_date_category_boundaries().items()
        }

    @api.model
    def get_date_category(self, value):
        if not value:
            return ""
        if value.tzinfo is None:
            value = value.replace(tzinfo=UTC)
        else:
            value = value.astimezone(UTC)
        bound = self._get_date_category_boundaries()
        for key, upper, _label, _kind in self.DATE_CATEGORIES:
            if upper is None or value < bound[upper]:
                return key
        return ""

    @api.model
    def get_domain_date_category(self, field_name, date_category):
        bound = self._get_date_category_boundaries_naive()
        lower = None
        for key, upper, _label, _kind in self.DATE_CATEGORIES:
            if key == date_category:
                conditions = []
                if lower is not None:
                    conditions.append((field_name, ">=", bound[lower]))
                if upper is not None:
                    conditions.append((field_name, "<", bound[upper]))
                return conditions
            lower = upper
        return None

    @api.model
    def _get_date_category_sql(self, date_sql):
        bound = self._get_date_category_boundaries_naive()
        arms = [
            SQL(
                "WHEN %(date_value)s < %(limit)s THEN %(category)s",
                date_value=date_sql,
                limit=bound[upper],
                category=key,
            )
            for key, upper, _label, _kind in self.DATE_CATEGORIES
            if upper is not None
        ]
        final = self.DATE_CATEGORIES[-1][0]
        return SQL("CASE %s ELSE %s END", SQL(" ").join(arms), final)

    def _get_date_category_counts(self, model_name, date_field, group_field, domain):
        model = self.env[model_name]
        model.browse().check_access("read")
        query = model._search(
            Domain(domain)
            & Domain(group_field, "in", self.ids)
            & Domain(date_field, "!=", False),
        )
        counts_by_record = {record_id: {} for record_id in self.ids}
        if query.is_empty():
            return counts_by_record
        group_sql = model._field_to_sql(model._table, group_field, query)
        date_sql = model._field_to_sql(model._table, date_field, query)
        query.groupby = SQL("1, 2")
        rows = self.env.execute_query(
            query.select(
                group_sql, self._get_date_category_sql(date_sql), SQL("COUNT(*)")
            )
        )
        for record_id, date_category, count in rows:
            counts_by_record[record_id][date_category] = count
        dbg.performance.debug(
            "_get_date_category_counts(%s.%s by %s): %d records, %d rows",
            model_name,
            date_field,
            group_field,
            len(self),
            len(rows),
        )
        return counts_by_record
