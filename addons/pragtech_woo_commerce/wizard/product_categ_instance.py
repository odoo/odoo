# -*- coding: utf-8 -*-

from odoo import models, api, _, fields
from odoo.exceptions import UserError


class WooProductCategInstanceExp(models.Model):
    _name = 'woo.product.categ.instance.exp'
    _description = 'Product Category Export Instance'

    woo_instance_id = fields.Many2one('woo.instance')

    def product_categ_instance_for_exp(self):
        instance_id = self.woo_instance_id
        self.env['product.category'].export_selected_category(instance_id)

    @api.model
    def default_get(self, fields):
        res = super(WooProductCategInstanceExp, self).default_get(fields)
        try:
            instance = self.env['woo.instance'].search([])[0]
        except Exception as error:
            raise UserError(_("Please create and configure WooCommerce Instance"))

        if instance:
            res['woo_instance_id'] = instance.id

        return res


class WooProductCategInstanceImp(models.Model):
    _name = 'woo.product.categ.instance.imp'
    _description = 'Product Category Import Instance'

    woo_instance_id = fields.Many2one('woo.instance')

    def product_categ_instance_for_imp(self):
        instance_id = self.woo_instance_id
        self.env['product.category'].import_product_category(instance_id)

    @api.model
    def default_get(self, fields):
        res = super(WooProductCategInstanceImp, self).default_get(fields)
        try:
            instance = self.env['woo.instance'].search([])[0]
        except Exception as error:
            raise UserError(_("Please create and configure WooCommerce Instance"))

        if instance:
            res['woo_instance_id'] = instance.id

        return res
