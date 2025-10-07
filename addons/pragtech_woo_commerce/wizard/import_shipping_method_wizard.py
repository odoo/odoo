# -*- coding: utf-8 -*-

from odoo.exceptions import UserError
from odoo import fields, models, _, api


class ImportShippingMethod(models.TransientModel):
    _name = 'import.shipping.method.wizard'
    _description = "Import Shipping method wizard"

    @api.model
    def default_get(self, fields):
        res = super(ImportShippingMethod, self).default_get(fields)
        try:
            instance = self.env['woo.instance'].search([])[0]
        except Exception as error:
            raise UserError(_("Please create and configure WooCommerce Instance"))

        if instance:
            res['woo_instance_id'] = instance.id

        return res

    woo_instance_id = fields.Many2one('woo.instance', "Woo Instance")

    def import_shipping_method_instance(self):
        self.env['delivery.carrier'].import_woo_shipping_method(self.woo_instance_id)
