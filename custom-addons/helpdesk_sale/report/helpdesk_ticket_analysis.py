# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class HelpdeskTicketReport(models.Model):
    _inherit = 'helpdesk.ticket.report.analysis'

    sale_order_id = fields.Many2one('sale.order', string='Ref. Sales Order', readonly=True, groups="sales_team.group_sale_salesman,account.group_account_invoice")

    def _select(self):
        select_str = super()._select()
        select_str += ", T.sale_order_id as sale_order_id"
        return select_str
