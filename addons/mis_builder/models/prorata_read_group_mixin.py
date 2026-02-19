# Copyright 2020 ACSONE SA/NV
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.fields import Date

from .mis_kpi_data import intersect_days


class ProRataReadGroupMixin(models.AbstractModel):
    _name = "prorata.read_group.mixin"
    _description = "Adapt model with date_from/date_to for pro-rata temporis read_group"

    date_from = fields.Date(required=True)
    date_to = fields.Date(required=True)
    date = fields.Date(
        compute=lambda self: None,
        search="_search_date",
        help=(
            "Dummy field that adapts searches on date "
            "to searches on date_from/date_to."
        ),
    )

    def _search_date(self, operator, value):
        if operator in (">=", ">"):
            return [("date_to", operator, value)]
        elif operator in ("<=", "<"):
            return [("date_from", operator, value)]
        raise UserError(
            _("Unsupported operator %s for searching on date") % (operator,)
        )

    @api.model
    def _intersect_days(self, item_dt_from, item_dt_to, dt_from, dt_to):
        return intersect_days(item_dt_from, item_dt_to, dt_from, dt_to)

    @api.model
    def read_group(
        self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True
    ):
        """Override read_group to perform pro-rata temporis adjustments.

        When read_group is invoked with a domain that filters on
        a time period (date >= from and date <= to, or
        date_from <= to and date_to >= from), adjust the accumulated
        values pro-rata temporis.
        """
        date_from = None
        date_to = None
        assert isinstance(domain, list)
        for domain_item in domain:
            if isinstance(domain_item, list | tuple):
                field, op, value = domain_item
                if field == "date" and op == ">=":
                    date_from = value
                elif field == "date_to" and op == ">=":
                    date_from = value
                elif field == "date" and op == "<=":
                    date_to = value
                elif field == "date_from" and op == "<=":
                    date_to = value
        if (
            date_from is not None
            and date_to is not None
            and not any(":" in f for f in fields)
        ):
            dt_from = Date.from_string(date_from)
            dt_to = Date.from_string(date_to)
            res = {}
            sum_fields = set(fields) - set(groupby)
            read_fields = set(fields + ["date_from", "date_to"])
            for item in self.search(domain).read(read_fields):
                key = tuple(item[k] for k in groupby)
                if key not in res:
                    res[key] = {k: item[k] for k in groupby}
                    res[key].update({k: 0.0 for k in sum_fields})
                res_item = res[key]
                for sum_field in sum_fields:
                    item_dt_from = Date.from_string(item["date_from"])
                    item_dt_to = Date.from_string(item["date_to"])
                    i_days, item_days = self._intersect_days(
                        item_dt_from, item_dt_to, dt_from, dt_to
                    )
                    res_item[sum_field] += item[sum_field] * i_days / item_days
            return res.values()
        return super().read_group(
            domain,
            fields,
            groupby,
            offset=offset,
            limit=limit,
            orderby=orderby,
            lazy=lazy,
        )
