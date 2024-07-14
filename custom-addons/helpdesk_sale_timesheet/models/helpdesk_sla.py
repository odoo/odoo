# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models

class HelpdeskSLA(models.Model):
    _inherit = 'helpdesk.sla'

    sale_line_ids = fields.Many2many(
        'sale.order.line', string="Sales Order Items",
        domain="[('is_service', '=', True)]")
