# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api
from odoo.addons.sale_timesheet.models.account import TIMESHEET_INVOICE_TYPES

class TimesheetsAnalysisReport(models.Model):

    _inherit = "timesheets.analysis.report"
    _auto = False

    so_line = fields.Many2one("sale.order.line", string="SO line", readonly=True)
    timesheet_invoice_type = fields.Selection(TIMESHEET_INVOICE_TYPES, string="Billable Type", readonly=True)
    timesheet_revenues = fields.Float("Timesheet Revenues", readonly=True, help="Number of hours spent multiplied by the unit price per hour/day.")
    margin = fields.Float("Margin", readonly=True, help="Timesheets revenues minus the costs")

    billable_time = fields.Float("Billable Time", readonly=True, help="Number of hours/days linked to a SOL.")
    non_billable_time = fields.Float("Non Billable Time", readonly=True, help="Number of hours/days not linked to a SOL.")

    @property
    def _table_query(self):
        return """
            SELECT A.*,
                (timesheet_revenues + A.amount) AS margin,
                (A.unit_amount - billable_time) AS non_billable_time
            FROM (
                %s %s %s
            ) A
        """ % (self._select(), self._from(), self._where())

    @api.model
    def _select(self):
        return super()._select() + """,
            A.so_line AS so_line,
            A.timesheet_invoice_type AS timesheet_invoice_type,
            (-1 * A.unit_amount * A.amount) AS timesheet_revenues,
            CASE WHEN order_id IS NULL THEN 0 ELSE unit_amount END AS billable_time
        """
