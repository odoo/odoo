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
        # retrieve all children partners and prefetch 'parent_id' on them
        all_partners = self.search([('id', 'child_of', self.ids)])
        all_partners.read(['parent_id'])

        sale_order_groups = self.env['sale.order'].read_group(
            domain=[('partner_id', 'in', all_partners.ids)],
            fields=['partner_id'], groupby=['partner_id']
        )
        for group in sale_order_groups:
            partner = self.browse(group['partner_id'][0])
            while partner:
                if partner in self:
                    partner.sale_order_count += group['partner_id_count']
                partner = partner.parent_id
