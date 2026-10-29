# -*- coding: utf-8 -*-

from odoo.exceptions import UserError
from odoo import models, api, _, fields


class ProductAttrValueInstance(models.Model):
    _name = 'product.attr.value.instance.exp'
    _description = 'Product Attribute Value Export'

    woo_instance_id = fields.Many2one('woo.instance')

    def product_attr_value_instance_for_exp(self):
        instance_id = self.woo_instance_id
        self.env['product.attribute.value'].export_selected_attribute_terms(instance_id)

    @api.model
    def default_get(self, fields):
        res = super(ProductAttrValueInstance, self).default_get(fields)
        try:
            instance = self.env['woo.instance'].search([])[0]
        except Exception as error:
            raise UserError(_("Please create and configure WooCommerce Instance"))

        if instance:
            res['woo_instance_id'] = instance.id

        return res


class ProductAttrValueInstanceImp(models.Model):
    _name = 'product.attr.value.instance.imp'
    _description = 'Product Attribute Value Import'

    woo_instance_id = fields.Many2one('woo.instance')

    def product_attr_value_instance_for_imp(self):
        instance_id = self.woo_instance_id
        self.env['product.attribute.value'].import_product_attribute_term(instance_id)

    @api.model
    def default_get(self, fields):
        res = super(ProductAttrValueInstanceImp, self).default_get(fields)
        try:
            instance = self.env['woo.instance'].search([])[0]
        except Exception as error:
            raise UserError(_("Please create and configure WooCommerce Instance"))

        if instance:
            res['woo_instance_id'] = instance.id

        return res
