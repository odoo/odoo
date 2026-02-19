# -*- coding: utf-8 -*-

from odoo.exceptions import UserError
from odoo import fields, models, _, api


class ImportPaymentGateway(models.TransientModel):
    _name = 'import.payment.gateway.wizard'
    _description = "Import payment gateway wizard"

    @api.model
    def default_get(self, fields):
        res = super(ImportPaymentGateway, self).default_get(fields)
        try:
            instance = self.env['woo.instance'].search([])[0]
        except Exception as error:
            raise UserError(_("Please create and configure WooCommerce Instance"))

        if instance:
            res['woo_instance_id'] = instance.id

        return res

    woo_instance_id = fields.Many2one('woo.instance', "Woo Instance")

    def import_payment_gateway_instance(self):
        self.env['payment.provider'].import_woo_payment_gateway(self.woo_instance_id)
        return
