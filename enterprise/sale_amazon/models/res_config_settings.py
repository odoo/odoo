# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    def action_view_default_amazon_products(self):
        default_product = self.env.ref('sale_amazon.default_product', raise_if_not_found=False) \
                          or self.env['product.product']._restore_data_product(
                              'Amazon Sales', 'consu', 'default_product')
        shipping_product = self.env.ref('sale_amazon.shipping_product', raise_if_not_found=False) \
                           or self.env['product.product']._restore_data_product(
                              'Amazon Sales', 'consu', 'shipping_product')
        return {
            'type': 'ir.actions.act_window',
            'name': _('Default Products'),
            'res_model': 'product.product',
            'view_mode': 'kanban,list,form',
            'domain': [('id', 'in', (default_product + shipping_product).ids)],
            'context': {'create': False, 'delete': False, 'active_test': False},
        }
