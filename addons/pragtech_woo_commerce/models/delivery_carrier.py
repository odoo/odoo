# -*- coding: utf-8 -*-

from woocommerce import API
from odoo import fields, models, _
from odoo.exceptions import UserError

class DeliveryCarrier(models.Model):
    _inherit = 'delivery.carrier'

    woo_id = fields.Char('WooCommerce ID')
    woo_instance_id = fields.Many2one('woo.instance', ondelete='cascade')
    is_exported = fields.Boolean('Synced In Woocommerce', default=False)

    def cron_import_shipping(self):
        woo_instance = self.env['woo.instance'].sudo().search([])
        for rec in woo_instance:
            self.import_woo_shipping_method(rec)

    def import_woo_shipping_method(self, instance_id):
        location = instance_id.url
        cons_key = instance_id.client_id
        sec_key = instance_id.client_secret
        version = 'wc/v3'

        wcapi = API(url=location, consumer_key=cons_key, consumer_secret=sec_key, version=version)

        url = "shipping_methods"
        try:
            response = wcapi.get(url)
        except Exception as error:
            raise UserError(_("Please check your connection and try again"))
        if response.status_code == 200 and response.content:
            parsed_data = response.json()
            for rec in parsed_data:
                shipping = self.env['delivery.carrier'].sudo().search([('woo_id', '=', rec.get('id'))], limit=1)
                if not shipping:
                    delivery_product = self.env['product.product'].sudo().create({
                        'name': rec.get('title'),
                        'detailed_type': 'service',
                    })
                    vals = {
                        'woo_id': rec.get('id'),
                        'is_exported': True,
                        'woo_instance_id': instance_id.id,
                        'name': rec.get('title'),
                        'carrier_description': rec.get('description'),
                        'product_id': delivery_product.id,
                    }

                    self.sudo().create(vals)
