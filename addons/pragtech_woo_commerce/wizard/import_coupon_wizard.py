# -*- coding: utf-8 -*-

from odoo.exceptions import UserError
from odoo import fields, models, _, api


class ImportCoupon(models.TransientModel):
    _name = 'import.coupon.wizard'
    _description = "Import coupon wizard"

    @api.model
    def default_get(self, fields):
        res = super(ImportCoupon, self).default_get(fields)
        try:
            instance = self.env['woo.instance'].search([])[0]
        except Exception as error:
            raise UserError(_("Please create and configure WooCommerce Instance"))

        if instance:
            res['woo_instance_id'] = instance.id

        return res

    woo_instance_id = fields.Many2one('woo.instance', "Woo Instance")

    def import_coupon_instance(self):
        self.env['loyalty.program'].import_woo_coupon(self.woo_instance_id)


class ExportCoupon(models.TransientModel):
    _name = "export.coupon.wizard"
    _description = "export coupon"

    @api.model
    def default_get(self, fields):
        res = super(ExportCoupon, self).default_get(fields)
        try:
            instance = self.env['woo.instance'].search([])[0]
        except Exception as error:
            raise UserError(_("Please create and configure WooCommerce Instance"))

        if instance:
            res['woo_instance_id'] = instance.id

        return res

    woo_instance_id = fields.Many2one('woo.instance', "Woo Instance")

    def export_coupon_instance(self):
        instance_id = self.woo_instance_id
        self.env['loyalty.program'].export_selected_coupon(instance_id)
