# -*- coding: utf-8 -*-

from odoo.exceptions import UserError
from odoo import models, _, api, fields


class WooProductInstanceExp(models.Model):
    _name = 'woo.product.instance.exp'
    _description = 'Product Export Instance'

    woo_instance_id = fields.Many2one('woo.instance')

    def product_instance_selected_for_exp(self):
        self.env['product.template'].export_selected_product(self.woo_instance_id)

    @api.model
    def default_get(self, fields):
        res = super(WooProductInstanceExp, self).default_get(fields)
        try:
            instance = self.env['woo.instance'].search([])[0]
        except Exception as error:
            raise UserError(_("Please create and configure WooCommerce Instance"))

        if instance:
            res['woo_instance_id'] = instance.id

        return res


class WooProductInstanceImp(models.Model):
    _name = 'woo.product.instance.imp'
    _description = 'Product Import Instance'

    woo_instance_id = fields.Many2one('woo.instance')

    def product_instance_selected_for_imp(self):
        self.env['product.template'].import_product(self.woo_instance_id)

    @api.model
    def default_get(self, fields):
        res = super(WooProductInstanceImp, self).default_get(fields)
        try:
            instance = self.env['woo.instance'].search([])[0]
        except Exception as error:
            raise UserError(_("Please create and configure WooCommerce Instance"))

        if instance:
            res['woo_instance_id'] = instance.id

        return res
