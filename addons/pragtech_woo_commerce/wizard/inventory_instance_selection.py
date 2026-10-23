# -*- coding: utf-8 -*-

from odoo.exceptions import UserError
from odoo import models, api, _, fields


class WooInventoryInstanceImp(models.Model):
    _name = 'woo.inventory.instance.imp'
    _description = 'Inventory Import Instance'

    woo_instance_id = fields.Many2one('woo.instance')

    def import_woo_inventory(self):
        self.env['product.template'].import_inventory(self.woo_instance_id)

    @api.model
    def default_get(self, fields):
        res = super(WooInventoryInstanceImp, self).default_get(fields)
        try:
            instance = self.env['woo.instance'].search([])[0]
        except Exception as error:
            raise UserError(_("Please create and configure WooCommerce Instance"))

        if instance:
            res['woo_instance_id'] = instance.id

        return res
