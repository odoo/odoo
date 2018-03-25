# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models
from odoo.addons.base.res.res_partner import WARNING_MESSAGE, WARNING_HELP


class ResPartner(models.Model):
    _inherit = 'res.partner'

    sale_order_count = fields.Integer(compute='_compute_sale_order_count', string='# of Sales Order')
    sale_order_ids = fields.One2many('sale.order', 'partner_id', 'Sales Order')
    sale_warn = fields.Selection(WARNING_MESSAGE, 'Sales Order', default='no-message', help=WARNING_HELP, required=True)
    sale_warn_msg = fields.Text('Message for Sales Order')

    def _compute_sale_order_count(self):
        for partner in self:
            partner.sale_order_count = len(partner.sale_order_ids) + (len(partner.mapped('child_ids.sale_order_ids')) if partner.is_company else 0)
