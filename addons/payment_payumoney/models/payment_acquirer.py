# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import hashlib
import urlparse

from odoo import api, fields, models, _


class PaymentAcquirerPayumoney(models.Model):
    _inherit = 'payment.acquirer'

    payumoney_merchant_key = fields.Char(string='Merchant Key', required_if_provider='payumoney')
    payumoney_merchant_salt = fields.Char(string='Merchant Salt', required_if_provider='payumoney')

    def _get_payumoney_urls(self, environment):
        """ PayUmoney URLs"""
        if environment == 'prod':
            return {'payumoney_form_url': 'https://secure.payu.in/_payment'}
        else:
            return {'payumoney_form_url': 'https://test.payu.in/_payment'}

    @api.model
    def _get_providers(self):
        providers = super(PaymentAcquirerPayumoney, self)._get_providers()
        providers.append(['payumoney', 'PayUmoney'])
        return providers

    def _payumoney_generate_sign(self, inout, values):
        """ Generate the shasign for incoming or outgoing communications.
        :param self: the self browse record. It should have a shakey in shakey out
        :param string inout: 'in' (odoo contacting payumoney) or 'out' (payumoney
                             contacting odoo).
        :param dict values: transaction values

        :return string: shasign
        """
        if inout not in ('in', 'out'):
            raise Exception("Type must be 'in' or 'out'")

        if inout == 'in':
            keys = "key|txnid|amount|productinfo|firstname|email|udf1|||||||||".split('|')
            sign = ''.join('%s|' % (values.get(k) or '') for k in keys)
            sign += self.payumoney_merchant_salt or ''
        else:
            keys = "|status||||||||||udf1|email|firstname|productinfo|amount|txnid".split('|')
            sign = ''.join('%s|' % (values.get(k) or '') for k in keys)
            sign = self.payumoney_merchant_salt + sign + self.payumoney_merchant_key

        shasign = hashlib.sha512(sign).hexdigest()
        return shasign

    @api.multi
    def payumoney_form_generate_values(self, values):
        self.ensure_one()
        base_url = self.env['ir.config_parameter'].get_param('web.base.url')
        payumoney_values = dict(values,
                                key=self.payumoney_merchant_key,
                                txnid=values['reference'],
                                amount=values['amount'],
                                productinfo=values['reference'],
                                firstname=values.get('partner_name'),
                                email=values.get('partner_email'),
                                phone=values.get('partner_phone'),
                                service_provider='payu_paisa',
                                surl='%s' % urlparse.urljoin(base_url, '/payment/payumoney/return'),
                                furl='%s' % urlparse.urljoin(base_url, '/payment/payumoney/error'),
                                curl='%s' % urlparse.urljoin(base_url, '/payment/payumoney/cancel')
                                )

        payumoney_values['udf1'] = payumoney_values.pop('return_url', '/')
        payumoney_values['hash'] = self._payumoney_generate_sign('in', payumoney_values)
        return payumoney_values

    @api.multi
    def payumoney_get_form_action_url(self):
        self.ensure_one()
        return self._get_payumoney_urls(self.environment)['payumoney_form_url']
