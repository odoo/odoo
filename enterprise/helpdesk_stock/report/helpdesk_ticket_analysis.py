# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class HelpdeskTicketReport(models.Model):
    _inherit = 'helpdesk.ticket.report.analysis'

    product_id = fields.Many2one('product.product', string='Product', readonly=True)

    def _select(self):
        select_str = super()._select()
        select_str += ", T.product_id as product_id"
        return select_str
