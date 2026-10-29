# -*- coding: utf-8 -*-

from woocommerce import API
from odoo import fields, models, _
from odoo.exceptions import UserError

class PaymentProvider(models.Model):
    _inherit = 'payment.provider'

    woo_id = fields.Char('WooCommerce ID')
    woo_instance_id = fields.Many2one('woo.instance', ondelete='cascade')
    is_exported = fields.Boolean('Synced In Woocommerce', default=False)

    def cron_import_payment(self):
        woo_instance = self.env['woo.instance'].sudo().search([])
        for rec in woo_instance:
            self.import_woo_payment_gateway(rec)

    def import_woo_payment_gateway(self, instance_id):
        location = instance_id.url
        cons_key = instance_id.client_id
        sec_key = instance_id.client_secret
        version = 'wc/v3'

        wcapi = API(url=location, consumer_key=cons_key, consumer_secret=sec_key, version=version)

        url = "payment_gateways"
        try:
            response = wcapi.get(url)
        except Exception as error:
            raise UserError(_("Please check your connection and try again"))

        if response.status_code == 200 and response.content:
            parsed_data = response.json()
            for rec in parsed_data:
                payment_gateway = self.sudo().search([('woo_id', '=', rec.get('id'))], limit=1)
                if not payment_gateway:
                    vals = {
                        'name': rec.get('method_title'),
                        'woo_id': rec.get('id'),
                        'is_exported': True,
                        'woo_instance_id': instance_id.id,
                        'state': 'disabled',
                    }
                    if rec.get('enabled'):
                        vals.update({'state': 'enabled'})

                    self.sudo().create(vals)
                else:
                    if rec.get('enabled'):
                        payment_gateway.sudo().write({'state': 'enabled'})
