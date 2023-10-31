# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class PosConfig(models.Model):
    _inherit = 'pos.config'

    iface_discount = fields.Boolean(string='Order Discounts', help='Allow the cashier to give discounts on the whole order.')
    discount_pc = fields.Float(string='Discount Percentage', help='The default discount percentage when clicking on the Discount button', default=10.0)
    discount_product_id = fields.Many2one('product.product', string='Discount Product',
        domain="[('sale_ok', '=', True)]", help='The product used to apply the discount on the ticket.')

    @api.model
    def _default_discount_value_on_module_install(self):
        configs = self.env['pos.config'].search([])
        open_configs = (
            self.env['pos.session']
            .search(['|', ('state', '!=', 'closed'), ('rescue', '=', True)])
            .mapped('config_id')
        )
        # Do not modify configs where an opened session exists.
        product = self.env.ref("point_of_sale.product_product_consumable", raise_if_not_found=False)
        for conf in (configs - open_configs):
            conf.discount_product_id = product if conf.module_pos_discount and product and (not product.company_id or product.company_id == conf.company_id) else False

    def open_ui(self):
        for config in self:
            if not self.current_session_id and config.module_pos_discount and not config.discount_product_id:
                raise UserError(_('A discount product is needed to use the Global Discount feature. Go to Point of Sale > Configuration > Settings to set it.'))
        return super().open_ui()

    def _get_special_products_ids(self):
        res = super()._get_special_products_ids()
        res += self.env['pos.config'].search([]).mapped('discount_product_id').ids
        return res
