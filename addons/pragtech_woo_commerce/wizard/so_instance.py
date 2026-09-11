# -*- coding: utf-8 -*-

from odoo.exceptions import UserError
from odoo import models, api, _, fields


class SaleOrderInstance(models.Model):
    _name = 'sale.order.instance.exp'
    _description = 'Sales Order Export'

    woo_instance_id = fields.Many2one('woo.instance')

    def sale_order_instance_for_exp(self):
        instance_id = self.woo_instance_id
        self.env['sale.order'].export_selected_so(instance_id)

    @api.model
    def default_get(self, fields):
        res = super(SaleOrderInstance, self).default_get(fields)
        try:
            instance = self.env['woo.instance'].search([])[0]
        except Exception as error:
            raise UserError(_("Please create and configure WooCommerce Instance"))

        if instance:
            res['woo_instance_id'] = instance.id

        return res


class SaleOrderInstanceImp(models.Model):
    _name = 'sale.order.instance.imp'
    _description = 'Sles Order Import'

    woo_instance_id = fields.Many2one('woo.instance')

    def sale_order_instance_for_imp(self):
        instance_id = self.woo_instance_id
        self.env['sale.order'].import_sale_order(instance_id)

    @api.model
    def default_get(self, fields):
        res = super(SaleOrderInstanceImp, self).default_get(fields)
        try:
            instance = self.env['woo.instance'].search([])[0]
        except Exception as error:
            raise UserError(_("Please create and configure WooCommerce Instance"))

        if instance:
            res['woo_instance_id'] = instance.id

        return res
