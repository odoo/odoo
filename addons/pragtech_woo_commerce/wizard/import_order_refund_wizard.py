# -*- coding: utf-8 -*-

from odoo.exceptions import UserError
from odoo import fields, models, _, api


class ImportRefund(models.TransientModel):
    _name = 'import.refund.wizard'
    _description = "Import Refund wizard"

    @api.model
    def default_get(self, fields):
        res = super(ImportRefund, self).default_get(fields)
        try:
            instance = self.env['woo.instance'].search([])[0]
        except Exception as error:
            raise UserError(_("Please create and configure WooCommerce Instance"))

        if instance:
            res['woo_instance_id'] = instance.id

        return res

    woo_instance_id = fields.Many2one('woo.instance', "Woo Instance")
    order_id = fields.Many2one('sale.order', string="Order")

    def import_refund_instance(self):
        self.env['account.move'].import_woo_refund(self.woo_instance_id, self.order_id)
        return
