# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models

class HelpdeskTicket(models.Model):
    _inherit = 'helpdesk.ticket'

    sale_order_id = fields.Many2one('sale.order', string='Ref. Sales Order',
        domain="""[
            '|', (not commercial_partner_id, '=', 1), ('partner_id', 'child_of', commercial_partner_id or []),
            ('company_id', '=', company_id)]""",
        groups="sales_team.group_sale_salesman,account.group_account_invoice")

    def copy(self, default=None):
        if not self.env.user.has_group('sales_team.group_sale_salesman') and not self.env.user.has_group('account.group_account_invoice'):
            if default is None:
                default = {'sale_order_id': False}
            else:
                default.update({'sale_order_id': False})
        return super(HelpdeskTicket, self).copy(default=default)
