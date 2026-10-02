# -*- coding: utf-8 -*-

from odoo.exceptions import UserError
from odoo import models, api, _, fields


class WooProductVarInstanceExp(models.Model):
    _name = 'woo.product.variant.instance.exp'
    _description = 'Product Variant Export Instance'

    woo_instance_id = fields.Many2one('woo.instance')

    def product_variant_instance_selected_for_exp(self):
        instance_id = self.woo_instance_id
        self.env['product.product'].export_selected_product_variant(instance_id)

    @api.model
    def default_get(self, fields):
        res = super(WooProductVarInstanceExp, self).default_get(fields)
        try:
            instance = self.env['woo.instance'].search([])[0]
        except Exception as error:
            raise UserError(_("Please create and configure WooCommerce Instance"))

        if instance:
            res['woo_instance_id'] = instance.id

        return res
