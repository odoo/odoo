# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models
from odoo.fields import Domain


class UomUom(models.Model):
    _inherit = 'uom.uom'

    def _domain_product_uoms(self):
        domain = []
        if self.env.context.get("product_id"):
            domain.append(Domain('product_id', '=', self.env.context['product_id']))
        if self.env.context.get("product_ids"):
            domain.append(Domain('product_id', 'in', self.env.context['product_ids']))
        return Domain.OR(domain) if domain else Domain.TRUE

    product_uom_ids = fields.One2many('product.uom', 'uom_id', string='Barcodes', domain=_domain_product_uoms)

    def action_open_packaging_barcodes(self):
        self.ensure_one()
        domain = Domain('uom_id', '=', self.id)
        if product_ids := self.env.context.get('product_ids'):
            domain = Domain.AND([domain, Domain('product_id', 'in', product_ids)])
        action = self.env['ir.actions.act_window']._for_xml_id('product.product_uom_action_view_list')
        action['domain'] = domain
        action['context'] = {
            **self.env.context,
            'default_uom_id': self.id,
        }
        return action
