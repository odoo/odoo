# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api

from odoo.addons.sale_timesheet.models.hr_timesheet import TIMESHEET_INVOICE_TYPES


class TimesheetsAnalysisReport(models.Model):
    _inherit = "timesheets.analysis.report"

    order_id = fields.Many2one("sale.order", string="Sales Order", readonly=True)
    so_line = fields.Many2one("sale.order.line", string="Sales Order Item", readonly=True)
    timesheet_invoice_type = fields.Selection(TIMESHEET_INVOICE_TYPES, string="Billable Type", readonly=True)
    timesheet_invoice_id = fields.Many2one("account.move", string="Invoice", readonly=True, help="Invoice created from the timesheet")
    timesheet_revenues = fields.Monetary("Timesheet Revenues", currency_field="currency_id", readonly=True, help="Number of hours spent multiplied by the unit price per hour/day.")
    margin = fields.Monetary("Margin", currency_field="currency_id", readonly=True, help="Timesheets revenues minus the costs")
    billable_time = fields.Float("Billable Time", readonly=True, help="Number of hours/days linked to a SOL.")
    non_billable_time = fields.Float("Non-billable Time", readonly=True, help="Number of hours/days not linked to a SOL.")

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
            A.order_id AS order_id,
            A.so_line AS so_line,
            A.timesheet_invoice_type AS timesheet_invoice_type,
            A.timesheet_invoice_id AS timesheet_invoice_id,
            CASE
                WHEN A.order_id IS NULL OR T.service_type in ('manual', 'milestones')
                THEN 0
                WHEN T.invoice_policy = 'order' AND SOL.qty_delivered != 0
                THEN (SOL.price_subtotal / SOL.qty_delivered) * (A.unit_amount / sol_product_uom.factor * a_product_uom.factor)
                ELSE A.unit_amount * SOL.price_unit / sol_product_uom.factor * a_product_uom.factor
            END AS timesheet_revenues,
            CASE WHEN A.order_id IS NULL THEN 0 ELSE A.unit_amount END AS billable_time
        """

    @api.model
    def _from(self):
        return super()._from() + """
            LEFT JOIN sale_order_line SOL ON A.so_line = SOL.id
            LEFT JOIN uom_uom sol_product_uom ON sol_product_uom.id = SOL.product_uom_id
            INNER JOIN uom_uom a_product_uom ON a_product_uom.id = A.product_uom_id
            LEFT JOIN product_product P ON P.id = SOL.product_id
            LEFT JOIN product_template T ON T.id = P.product_tmpl_id
        """
