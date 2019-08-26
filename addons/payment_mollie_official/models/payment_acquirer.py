# -*- coding: utf-8 -*-
from mollie.api.client import Client
from odoo import models, fields, api, _
from odoo.http import request

import base64
import requests
import logging
_logger = logging.getLogger(__name__)


class PaymentAcquirer(models.Model):
    _inherit = 'payment.acquirer'

    _mollie_client = Client()

    provider = fields.Selection(selection_add=[('mollie', 'Mollie')])
    mollie_api_key_test = fields.Char(
        'Mollie Test API key', size=40, required_if_provider='mollie',
        groups='base.group_user')
    mollie_api_key_prod = fields.Char('Mollie Live API key', size=40,
                                      required_if_provider='mollie',
                                      groups='base.group_user')
    method_ids = fields.One2many('payment.acquirer.method',
                                 'acquirer_id', 'Supported methods')

    @api.model
    def _get_main_mollie_provider(self):
        return self.sudo().search([('provider', '=', 'mollie')], order="id",
                                  limit=1) or False

    def _get_mollie_api_keys(self, state):
        keys = {'prod': self.mollie_api_key_prod,
                'test': self.mollie_api_key_test
                }
        return {'mollie_api_key': keys.get(state, keys['test']), }

    @api.onchange('method_ids')
    def _onchange_method_ids(self):
        return self.update_payment_icon_ids()

    def _get_mollie_urls(self, state):
        """ Mollie URLS """
        url = {
            'prod': 'https://api.mollie.com/v2',
            'test': 'https://api.mollie.com/v2', }

        return {'mollie_form_url': url.get(state, url['test']), }

    def mollie_form_generate_values(self, values):
        self.ensure_one()
        base_url = self.env['ir.config_parameter'].sudo(
        ).get_param('web.base.url')
        mollie_api_key = self._get_mollie_api_keys(
            self.state)['mollie_api_key']
        mollie_tx_values = dict(values)
        order_id = request.session.get('sale_last_order_id')
        mollie_tx_values.update({
            'OrderName': values.get('reference'),
            'Description': values.get('reference'),
            'Amount': '%.2f' % float(values.get('amount')),
            'Currency': values['currency'] and values['currency'].name or '',
            'Key': mollie_api_key,
            'URL': self._get_mollie_urls(self.state)['mollie_form_url'],
            'BaseUrl': base_url,
            'Language': values.get('partner_lang'),
            'Name': values.get('partner_name'),
            'Email': values.get('partner_email'),
            'Zip': values.get('partner_zip'),
            'Address': values.get('partner_address'),
            'Town': values.get('partner_city'),
            'Country': values.get('partner_country') and
            values.get('partner_country').code or '',
            'Phone': values.get('partner_phone'),
            'webhookUrl': base_url,
            'OrderId': order_id,
        })
        return mollie_tx_values

    def mollie_get_form_action_url(self):
        self.ensure_one()
        return "/payment/mollie/intermediate"

    def update_payment_icon_ids(self):
        self.ensure_one()
        if self.provider != 'mollie':
            return
        icon_model = self.env['payment.icon']
        icon_ids = []
        for method in self.method_ids:
            icon = icon_model.search([
                ('acquirer_reference', 'ilike', method.acquirer_reference)],
                limit=1)
            if not icon:
                icon = icon_model.create({
                    'name': method.name,
                    'acquirer_reference': method.acquirer_reference,
                    'image': method.image_small,
                    'sequence': method.sequence,
                    'provider': self.provider,
                    'currency_ids': method.currency_ids,
                    'country_ids': method.country_ids
                })
                icon.onchange_provider_ref()
            icon_ids.append(icon.id)
            icon.write({'sequence': method.sequence,
                        'provider': self.provider})

        return self.update({'payment_icon_ids': [(6, 0, icon_ids)]})

    def update_available_mollie_methods(self):
        for acquirer in self:
            if acquirer.provider != 'mollie':
                continue
            mollie_api_key = self._get_mollie_api_keys(
                self.state)['mollie_api_key']
            acquirer.method_ids.unlink()
            try:
                self._mollie_client.set_api_key(mollie_api_key)
                methods = self._mollie_client.methods.list(resource='orders')
                method_ids = []
                if methods.get('_embedded', False):
                    i = 10
                    for method in methods.get('_embedded',
                                              {"methods": []})["methods"]:
                        image_url = method['image']['size1x']
                        image = base64.b64encode(requests.get(image_url).content)
                        values = {
                            'name': method['description'],
                            'acquirer_reference': method['id'],
                            'acquirer_id': acquirer.id,
                            'image_small': image,
                            'sequence': i,
                        }
                        method_ids.append((0, _, values))
                        i += 1
                acquirer.write({'method_ids': method_ids})
                acquirer.update_payment_icon_ids()
            except Exception as e:
                _logger.error("__Error!_get_mollie_order__ %s" % e)
        return True

    @api.model
    def _cron_update_mollie_methods(self):
        objects = self.search([('provider', '=', 'mollie')])
        return objects.update_available_mollie_methods()

    def write(self, values):
        res = super(PaymentAcquirer, self).write(values)
        if 'mollie_api_key_test' in values or 'mollie_api_key_prod' in values:
            self.update_available_mollie_methods()
        return res

