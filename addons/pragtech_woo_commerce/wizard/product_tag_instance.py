# -*- coding: utf-8 -*-

from odoo.exceptions import UserError
from odoo import models, api, _, fields


class ProductTagInstance(models.Model):
    _name = 'product.tag.instance.exp'
    _description = 'Product Tag Export'

    woo_instance_id = fields.Many2one('woo.instance')

    def product_tag_instance_for_exp(self):
        instance_id = self.woo_instance_id
        self.env['product.tag.woo'].export_selected_product_tag(instance_id)

    @api.model
    def default_get(self, fields):
        res = super(ProductTagInstance, self).default_get(fields)
        try:
            instance = self.env['woo.instance'].search([])[0]
        except Exception as error:
            raise UserError(_("Please create and configure WooCommerce Instance"))

        if instance:
            res['woo_instance_id'] = instance.id

        return res


class ProductTagInstanceImp(models.Model):
    _name = 'product.tag.instance.imp'
    _description = 'Product Tag Import'

    woo_instance_id = fields.Many2one('woo.instance')

    def product_tag_instance_for_imp(self):
        instance_id = self.woo_instance_id
        self.env['product.tag.woo'].import_product_tag(instance_id)

    @api.model
    def default_get(self, fields):
        res = super(ProductTagInstanceImp, self).default_get(fields)
        try:
            instance = self.env['woo.instance'].search([])[0]
        except Exception as error:
            raise UserError(_("Please create and configure WooCommerce Instance"))

        if instance:
            res['woo_instance_id'] = instance.id

        return res
