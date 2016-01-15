# -*- coding: utf-'8' "-*-"
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from hashlib import sha1
import logging
import urllib
import urlparse

from odoo import api, fields, models
from odoo.addons.payment_buckaroo.controllers.main import BuckarooController

_logger = logging.getLogger(__name__)


class PaymentAcquirer(models.Model):
    _inherit = 'payment.acquirer'

    brq_websitekey = fields.Char(string='WebsiteKey', required_if_provider='buckaroo')
    brq_secretkey = fields.Char(string='SecretKey', required_if_provider='buckaroo')

    def _get_buckaroo_urls(self, environment):
        """ Buckaroo URLs
        """
        if environment == 'prod':
            return {
                'buckaroo_form_url': 'https://checkout.buckaroo.nl/html/',
            }
        else:
            return {
                'buckaroo_form_url': 'https://testcheckout.buckaroo.nl/html/',
            }

    @api.model
    def _get_providers(self):
        providers = super(PaymentAcquirer, self)._get_providers()
        providers.append(['buckaroo', 'Buckaroo'])
        return providers

    def _buckaroo_generate_digital_sign(self, inout, values):
        """ Generate the shasign for incoming or outgoing communications.

        :param string inout: 'in' (odoo contacting buckaroo) or 'out' (buckaroo
                             contacting odoo).
        :param dict values: transaction values

        :return string: shasign
        """
        assert inout in ('in', 'out')
        assert self.provider == 'buckaroo'

        keys = "add_returndata Brq_amount Brq_culture Brq_currency Brq_invoicenumber Brq_return Brq_returncancel Brq_returnerror Brq_returnreject brq_test Brq_websitekey".split()

        def get_value(key):
            return values.get(key) or ''

        if inout == 'out':
            for key in values:
                # case insensitive keys
                if key.upper() == 'BRQ_SIGNATURE':
                    del values[key]
                    break

            items = sorted(values.items(), key=lambda (x, y): x.lower())
            sign = ''.join('%s=%s' % (k, urllib.unquote_plus(v)) for k, v in items)
        else:
            sign = ''.join('%s=%s' % (k,get_value(k)) for k in keys)
        #Add the pre-shared secret key at the end of the signature
        sign = sign + self.brq_secretkey
        if isinstance(sign, str):
            # TODO: remove me? should not be used
            sign = urlparse.parse_qsl(sign)
        shasign = sha1(sign.encode('utf-8')).hexdigest()
        return shasign

    @api.multi
    def buckaroo_form_generate_values(self, values):
        self.ensure_one()
        base_url = self.env['ir.config_parameter'].get_param('web.base.url')
        buckaroo_tx_values = dict(values, Brq_websitekey = self.brq_websitekey,
            Brq_amount = values['amount'],
            Brq_currency = values['currency'] and values['currency'].name or '',
            Brq_invoicenumber = values['reference'],
            brq_test = self.environment != 'prod',
            Brq_return = urlparse.urljoin(base_url, BuckarooController._return_url),
            Brq_returncancel = urlparse.urljoin(base_url, BuckarooController._cancel_url),
            Brq_returnerror = urlparse.urljoin(base_url, BuckarooController._exception_url),
            Brq_returnreject = urlparse.urljoin(base_url, BuckarooController._reject_url),
            Brq_culture = (values.get('partner_lang') or 'en_US').replace('_', '-'))
        buckaroo_tx_values['add_returndata'] = buckaroo_tx_values.pop('return_url', '')

        buckaroo_tx_values['Brq_signature'] = self._buckaroo_generate_digital_sign('in', buckaroo_tx_values)
        return buckaroo_tx_values

    @api.multi
    def buckaroo_get_form_action_url(self):
        return self._get_buckaroo_urls(self.environment)['buckaroo_form_url']
