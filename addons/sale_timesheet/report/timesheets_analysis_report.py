# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api

class TimesheetsAnalysisReport(models.Model):

    _inherit = "timesheets.analysis.report"
    _auto = False

    so_line = fields.Many2one("sale.order.line", string="SO line", readonly=True)
    timesheet_invoice_type = fields.Selection([
        ("billable_time", "Billed on Timesheets"),
        ("billable_fixed", "Billed at a Fixed price"),
        ("non_billable", "Non Billable Tasks"),
        ("timesheet_revenues", "Timesheet Revenues"),
        ("service_revenues", "Service Revenues"),
        ("other_revenues", "Other Revenues"),
        ("other_costs", "Other Costs")], string="Billable Type",
            readonly=True)
    timesheet_revenues = fields.Float("Timesheet Revenues", readonly=True, help="Number of hours spent multiplied by the unit price per hour/day.")
    margin = fields.Float("Margin", readonly=True, help="Timesheets revenues minus the costs")

    billable_time = fields.Float("Billable Time", readonly=True, help="Number of hours/days linked to a SOL.")
    non_billable_time = fields.Float("Non Billable Time", readonly=True, help="Number of hours/days not linked to a SOL.")
    billable_time_percentage = fields.Float("Billable Time %", readonly=True, help="Sum of hours/days linked to a SOL vs the total number of hours/days spent.", group_operator="avg")
    non_billable_time_percentage = fields.Float("Non Billable Time %", readonly=True, help="Sum of hours/days not linked to a SOL vs the total number of hours/days spent.", group_operator="avg")

    @api.model
    def _select(self):
        return super()._select() + """,
            A.so_line AS so_line,
            A.timesheet_invoice_type AS timesheet_invoice_type,
            (timesheet_revenues - A.amount) AS margin,
            timesheet_revenues, billable_time, billable_time_percentage,
            (A.unit_amount - billable_time) AS non_billable_time,
            (100 - billable_time_percentage) AS non_billable_time_percentage
        """

    def _from(self):
        return """
            FROM
            (
                """ + super()._select() + """,
                    so_line, timesheet_invoice_type,
                    (-1 * A.unit_amount * A.amount) AS timesheet_revenues,
                    CASE WHEN order_id IS NULL THEN 0 ELSE unit_amount END AS billable_time,
                    CASE WHEN order_id IS NULL THEN 0 ELSE unit_amount END AS billable_time_percentage
                FROM account_analytic_line A
            ) A
        """
