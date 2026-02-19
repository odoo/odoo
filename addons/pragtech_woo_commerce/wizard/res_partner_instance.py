# -*- coding: utf-8 -*-

from odoo.exceptions import UserError
from odoo import models, api, _, fields


class ResPartnerInstance(models.Model):
    _name = 'res.partner.instance.exp'
    _description = 'Customer Export'

    woo_instance_id = fields.Many2one('woo.instance')

    def customer_instance_for_exp(self):
        instance_id = self.woo_instance_id
        self.env['res.partner'].export_selected_customer(instance_id)

    @api.model
    def default_get(self, fields):
        res = super(ResPartnerInstance, self).default_get(fields)
        try:
            instance = self.env['woo.instance'].search([])[0]
        except Exception as error:
            raise UserError(_("Please create and configure WooCommerce Instance"))

        if instance:
            res['woo_instance_id'] = instance.id

        return res


class ResPartnerInstanceImp(models.Model):
    _name = 'res.partner.instance.imp'
    _description = 'Customer Import'

    woo_instance_id = fields.Many2one('woo.instance')

    def customer_instance_for_imp(self):
        instance_id = self.woo_instance_id
        self.env['res.partner'].import_customer(instance_id)

    @api.model
    def default_get(self, fields):
        res = super(ResPartnerInstanceImp, self).default_get(fields)
        try:
            instance = self.env['woo.instance'].search([])[0]
        except Exception as error:
            raise UserError(_("Please create and configure WooCommerce Instance"))

        if instance:
            res['woo_instance_id'] = instance.id

        return res
