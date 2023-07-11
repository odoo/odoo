# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, models
from odoo.exceptions import UserError


class MrpBom(models.Model):
    _inherit = 'mrp.bom'

    def toggle_active(self):
        self.filtered(lambda bom: bom.active)._ensure_bom_is_free()
        return super().toggle_active()

    def unlink(self):
        self._ensure_bom_is_free()
        return super().unlink()

    def _ensure_bom_is_free(self):
        product_ids = []
        for bom in self:
            if bom.type != 'phantom':
                continue
            product_ids += bom.product_id.ids or bom.product_tmpl_id.product_variant_ids.ids
        if not product_ids:
            return
        lines = self.env['sale.order.line'].search([
            ('state', 'in', ('sale', 'done')),
            ('invoice_status', 'in', ('no', 'to invoice')),
            ('product_id', 'in', product_ids),
            ('move_ids.state', '!=', 'cancel'),
        ])
        if lines:
            product_names = ', '.join(lines.product_id.mapped('name'))
            raise UserError(_('As long as there are some sale order lines that must be delivered/invoiced and are '
                              'related to these bills of materials, you can not remove them.\n'
                              'The error concerns these products: %s', product_names))
