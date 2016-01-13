# -*- coding: utf-'8' "-*-"
from hashlib import sha1
import logging
import urllib
import urlparse

from openerp.addons.payment_buckaroo.controllers.main import BuckarooController
from openerp.osv import osv, fields

_logger = logging.getLogger(__name__)


class AcquirerBuckaroo(osv.Model):
    _inherit = 'payment.acquirer'

    def _get_buckaroo_urls(self, cr, uid, environment, context=None):
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

    def _get_providers(self, cr, uid, context=None):
        providers = super(AcquirerBuckaroo, self)._get_providers(cr, uid, context=context)
        providers.append(['buckaroo', 'Buckaroo'])
        return providers

    _columns = {
        'brq_websitekey': fields.char('WebsiteKey', required_if_provider='buckaroo'),
        'brq_secretkey': fields.char('SecretKey', required_if_provider='buckaroo'),
    }

    def _buckaroo_generate_digital_sign(self, acquirer, inout, values):
        """ Generate the shasign for incoming or outgoing communications.

        :param browse acquirer: the payment.acquirer browse record. It should
                                have a shakey in shaky out
        :param string inout: 'in' (openerp contacting buckaroo) or 'out' (buckaroo
                             contacting openerp).
        :param dict values: transaction values

        :return string: shasign
        """
        assert inout in ('in', 'out')
        assert acquirer.provider == 'buckaroo'

        keys = "add_returndata Brq_amount Brq_culture Brq_currency Brq_invoicenumber Brq_return Brq_returncancel Brq_returnerror Brq_returnreject brq_test Brq_websitekey".split()

        def get_value(key):
            if values.get(key):
                return values[key]
            return ''

        values = dict(values or {})

        if inout == 'out':
            for key in values.keys():
                # case insensitive keys
                if key.upper() == 'BRQ_SIGNATURE':
                    del values[key]
                    break

            items = sorted(values.items(), key=lambda (x, y): x.lower())
            sign = ''.join('%s=%s' % (k, urllib.unquote_plus(v)) for k, v in items)
        else:
            sign = ''.join('%s=%s' % (k,get_value(k)) for k in keys)
        #Add the pre-shared secret key at the end of the signature
        sign = sign + acquirer.brq_secretkey
        if isinstance(sign, str):
            # TODO: remove me? should not be used
            sign = urlparse.parse_qsl(sign)
        shasign = sha1(sign.encode('utf-8')).hexdigest()
        return shasign


    def buckaroo_form_generate_values(self, cr, uid, id, values, context=None):
        base_url = self.pool['ir.config_parameter'].get_param(cr, uid, 'web.base.url')
        acquirer = self.browse(cr, uid, id, context=context)
        buckaroo_tx_values = dict(values)
        buckaroo_tx_values.update({
            'Brq_websitekey': acquirer.brq_websitekey,
            'Brq_amount': values['amount'],
            'Brq_currency': values['currency'] and values['currency'].name or '',
            'Brq_invoicenumber': values['reference'],
            'brq_test': False if acquirer.environment == 'prod' else True,
            'Brq_return': '%s' % urlparse.urljoin(base_url, BuckarooController._return_url),
            'Brq_returncancel': '%s' % urlparse.urljoin(base_url, BuckarooController._cancel_url),
            'Brq_returnerror': '%s' % urlparse.urljoin(base_url, BuckarooController._exception_url),
            'Brq_returnreject': '%s' % urlparse.urljoin(base_url, BuckarooController._reject_url),
            'Brq_culture': (values.get('partner_lang') or 'en_US').replace('_', '-'),
            'add_returndata': buckaroo_tx_values.pop('return_url', '') or '',
        })
        buckaroo_tx_values['Brq_signature'] = self._buckaroo_generate_digital_sign(acquirer, 'in', buckaroo_tx_values)
        return buckaroo_tx_values

    def buckaroo_get_form_action_url(self, cr, uid, id, context=None):
        acquirer = self.browse(cr, uid, id, context=context)
        return self._get_buckaroo_urls(cr, uid, acquirer.environment, context=context)['buckaroo_form_url']
