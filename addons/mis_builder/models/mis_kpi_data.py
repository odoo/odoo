# Copyright 2017 ACSONE SA/NV
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from collections import defaultdict

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.osv import expression

ACC_SUM = "sum"
ACC_AVG = "avg"
ACC_NONE = "none"


def intersect_days(item_dt_from, item_dt_to, dt_from, dt_to):
    item_days = (item_dt_to - item_dt_from).days + 1.0
    i_dt_from = max(dt_from, item_dt_from)
    i_dt_to = min(dt_to, item_dt_to)
    i_days = (i_dt_to - i_dt_from).days + 1.0
    return i_days, item_days


class MisKpiData(models.AbstractModel):
    """Abstract class for manually entered KPI values."""

    _name = "mis.kpi.data"
    _description = "MIS Kpi Data Abtract class"

    name = fields.Char(compute="_compute_name", required=False, readonly=True)
    kpi_expression_id = fields.Many2one(
        comodel_name="mis.report.kpi.expression",
        required=True,
        ondelete="restrict",
        string="KPI",
    )
    date_from = fields.Date(required=True, string="From")
    date_to = fields.Date(required=True, string="To")
    amount = fields.Float()
    seq1 = fields.Integer(
        related="kpi_expression_id.kpi_id.sequence",
        store=True,
        readonly=True,
        string="KPI Sequence",
    )
    seq2 = fields.Integer(
        related="kpi_expression_id.subkpi_id.sequence",
        store=True,
        readonly=True,
        string="Sub-KPI Sequence",
    )

    @api.depends(
        "kpi_expression_id.subkpi_id.name",
        "kpi_expression_id.kpi_id.name",
        "date_from",
        "date_to",
    )
    def _compute_name(self):
        for rec in self:
            subkpi_name = rec.kpi_expression_id.subkpi_id.name
            if subkpi_name:
                subkpi_name = "." + subkpi_name
            else:
                subkpi_name = ""
            rec.name = "{}{}: {} - {}".format(
                rec.kpi_expression_id.kpi_id.name,
                subkpi_name,
                rec.date_from,
                rec.date_to,
            )

    @api.model
    def _intersect_days(self, item_dt_from, item_dt_to, dt_from, dt_to):
        return intersect_days(item_dt_from, item_dt_to, dt_from, dt_to)

    @api.model
    def _query_kpi_data(self, date_from, date_to, base_domain):
        """Query mis.kpi.data over a time period.

        Returns {mis.report.kpi.expression: amount}
        """
        dt_from = fields.Date.from_string(date_from)
        dt_to = fields.Date.from_string(date_to)
        # all data items within or overlapping [date_from, date_to]
        date_domain = [("date_from", "<=", date_to), ("date_to", ">=", date_from)]
        domain = expression.AND([date_domain, base_domain])
        res = defaultdict(float)
        res_avg = defaultdict(list)
        for item in self.search(domain):
            item_dt_from = fields.Date.from_string(item.date_from)
            item_dt_to = fields.Date.from_string(item.date_to)
            i_days, item_days = self._intersect_days(
                item_dt_from, item_dt_to, dt_from, dt_to
            )
            if item.kpi_expression_id.kpi_id.accumulation_method == ACC_SUM:
                # accumulate pro-rata overlap between item and reporting period
                res[item.kpi_expression_id] += item.amount * i_days / item_days
            elif item.kpi_expression_id.kpi_id.accumulation_method == ACC_AVG:
                # memorize the amount and number of days overlapping
                # the reporting period (used as weight in average)
                res_avg[item.kpi_expression_id].append((i_days, item.amount))
            else:
                raise UserError(
                    _(
                        "Unexpected accumulation method %(method)s for %(name)s.",
                        method=item.kpi_expression_id.kpi_id.accumulation_method,
                        name=item.name,
                    )
                )
        # compute weighted average for ACC_AVG
        for kpi_expression, amounts in res_avg.items():
            res[kpi_expression] = sum(d * a for d, a in amounts) / sum(
                d for d, a in amounts
            )
        return res
