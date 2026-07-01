# -*- coding: utf-8 -*-

from odoo.exceptions import UserError
from odoo import models, api, _, fields


class WooProductAttrInstanceExp(models.Model):
    _name = 'woo.product.attr.instance.exp'
    _description = 'Product Attribute Export Instance'

    woo_instance_id = fields.Many2one('woo.instance')

    def product_attr_instance_for_exp(self):
        instance_id = self.woo_instance_id
        for i in range(2):
            self.env['product.attribute'].export_selected_attribute(instance_id)

    @api.model
    def default_get(self, fields):
        res = super(WooProductAttrInstanceExp, self).default_get(fields)
        try:
            instance = self.env['woo.instance'].search([])[0]
        except Exception as error:
            raise UserError(_("Please create and configure WooCommerce Instance"))

        if instance:
            res['woo_instance_id'] = instance.id

        return res


class WooProductAttrInstanceImp(models.Model):
    _name = 'woo.product.attr.instance.imp'
    _description = 'Product Attribute Import Instance'

    woo_instance_id = fields.Many2one('woo.instance')

    def product_attr_instance_for_imp(self):
        instance_id = self.woo_instance_id
        self.env['product.attribute'].import_product_attribute(instance_id)

    @api.model
    def default_get(self, fields):
        res = super(WooProductAttrInstanceImp, self).default_get(fields)
        try:
            instance = self.env['woo.instance'].search([])[0]
        except Exception as error:
            raise UserError(_("Please create and configure WooCommerce Instance"))

        if instance:
            res['woo_instance_id'] = instance.id

        return res
