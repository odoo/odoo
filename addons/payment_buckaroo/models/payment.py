# coding: utf-8
from hashlib import sha1
import logging
import urllib
import urlparse

from odoo import api, fields, models, _
from odoo.addons.payment.models.payment_acquirer import ValidationError
from odoo.addons.payment_buckaroo.controllers.main import BuckarooController
from odoo.tools.float_utils import float_compare

_logger = logging.getLogger(__name__)


def normalize_keys_upper(data):
    """Set all keys of a dictionnary to uppercase

    Buckaroo parameters names are case insensitive
    convert everything to upper case to be able to easily detected the presence
    of a parameter by checking the uppercase key only
    """
    return dict((key.upper(), val) for key, val in data.items())


class AcquirerBuckaroo(models.Model):
    _inherit = 'payment.acquirer'

    provider = fields.Selection(selection_add=[('buckaroo', 'Buckaroo')])
    brq_websitekey = fields.Char('WebsiteKey', required_if_provider='buckaroo', groups='base.group_user')
    brq_secretkey = fields.Char('SecretKey', required_if_provider='buckaroo', groups='base.group_user')

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

    def _buckaroo_generate_digital_sign(self, inout, values):
        """ Generate the shasign for incoming or outgoing communications.

        :param browse acquirer: the payment.acquirer browse record. It should
                                have a shakey in shaky out
        :param string inout: 'in' (odoo contacting buckaroo) or 'out' (buckaroo
                             contacting odoo).
        :param dict values: transaction values

        :return string: shasign
        """
        assert inout in ('in', 'out')
        assert self.provider == 'buckaroo'

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

            items = sorted(values.items(), key=lambda pair: pair[0].lower())
            sign = ''.join('%s=%s' % (k, urllib.unquote_plus(v)) for k, v in items)
        else:
            sign = ''.join('%s=%s' % (k, get_value(k)) for k in keys)
        # Add the pre-shared secret key at the end of the signature
        sign = sign + self.brq_secretkey
        if isinstance(sign, str):
            # TODO: remove me? should not be used
            sign = urlparse.parse_qsl(sign)
        shasign = sha1(sign.encode('utf-8')).hexdigest()
        return shasign

    @api.multi
    def buckaroo_form_generate_values(self, values):
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        buckaroo_tx_values = dict(values)
        buckaroo_tx_values.update({
            'Brq_websitekey': self.brq_websitekey,
            'Brq_amount': values['amount'],
            'Brq_currency': values['currency'] and values['currency'].name or '',
            'Brq_invoicenumber': values['reference'],
            'brq_test': False if self.environment == 'prod' else True,
            'Brq_return': '%s' % urlparse.urljoin(base_url, BuckarooController._return_url),
            'Brq_returncancel': '%s' % urlparse.urljoin(base_url, BuckarooController._cancel_url),
            'Brq_returnerror': '%s' % urlparse.urljoin(base_url, BuckarooController._exception_url),
            'Brq_returnreject': '%s' % urlparse.urljoin(base_url, BuckarooController._reject_url),
            'Brq_culture': (values.get('partner_lang') or 'en_US').replace('_', '-'),
            'add_returndata': buckaroo_tx_values.pop('return_url', '') or '',
        })
        buckaroo_tx_values['Brq_signature'] = self._buckaroo_generate_digital_sign('in', buckaroo_tx_values)
        return buckaroo_tx_values

    @api.multi
    def buckaroo_get_form_action_url(self):
        return self._get_buckaroo_urls(self.environment)['buckaroo_form_url']


class TxBuckaroo(models.Model):
    _inherit = 'payment.transaction'

    # buckaroo status
    _buckaroo_valid_tx_status = [190]
    _buckaroo_pending_tx_status = [790, 791, 792, 793]
    _buckaroo_cancel_tx_status = [890, 891]
    _buckaroo_error_tx_status = [490, 491, 492]
    _buckaroo_reject_tx_status = [690]

    # --------------------------------------------------
    # FORM RELATED METHODS
    # --------------------------------------------------

    @api.model
    def _buckaroo_form_get_tx_from_data(self, data):
        """ Given a data dict coming from buckaroo, verify it and find the related
        transaction record. """
        origin_data = dict(data)
        data = normalize_keys_upper(data)
        reference, pay_id, shasign = data.get('BRQ_INVOICENUMBER'), data.get('BRQ_PAYMENT'), data.get('BRQ_SIGNATURE')
        if not reference or not pay_id or not shasign:
            error_msg = _('Buckaroo: received data with missing reference (%s) or pay_id (%s) or shasign (%s)') % (reference, pay_id, shasign)
            _logger.info(error_msg)
            raise ValidationError(error_msg)

        tx = self.search([('reference', '=', reference)])
        if not tx or len(tx) > 1:
            error_msg = _('Buckaroo: received data for reference %s') % (reference)
            if not tx:
                error_msg += _('; no order found')
            else:
                error_msg += _('; multiple order found')
            _logger.info(error_msg)
            raise ValidationError(error_msg)

        # verify shasign
        shasign_check = tx.acquirer_id._buckaroo_generate_digital_sign('out', origin_data)
        if shasign_check.upper() != shasign.upper():
            error_msg = _('Buckaroo: invalid shasign, received %s, computed %s, for data %s') % (shasign, shasign_check, data)
            _logger.info(error_msg)
            raise ValidationError(error_msg)

        return tx

    def _buckaroo_form_get_invalid_parameters(self, data):
        invalid_parameters = []
        data = normalize_keys_upper(data)
        if self.acquirer_reference and data.get('BRQ_TRANSACTIONS') != self.acquirer_reference:
            invalid_parameters.append(('Transaction Id', data.get('BRQ_TRANSACTIONS'), self.acquirer_reference))
        # check what is buyed
        if float_compare(float(data.get('BRQ_AMOUNT', '0.0')), self.amount, 2) != 0:
            invalid_parameters.append(('Amount', data.get('BRQ_AMOUNT'), '%.2f' % self.amount))
        if data.get('BRQ_CURRENCY') != self.currency_id.name:
            invalid_parameters.append(('Currency', data.get('BRQ_CURRENCY'), self.currency_id.name))

        return invalid_parameters

    def _buckaroo_form_validate(self, data):
        data = normalize_keys_upper(data)
        status_code = int(data.get('BRQ_STATUSCODE', '0'))
        if status_code in self._buckaroo_valid_tx_status:
            self.write({
                'state': 'done',
                'acquirer_reference': data.get('BRQ_TRANSACTIONS'),
            })
            return True
        elif status_code in self._buckaroo_pending_tx_status:
            self.write({
                'state': 'pending',
                'acquirer_reference': data.get('BRQ_TRANSACTIONS'),
            })
            return True
        elif status_code in self._buckaroo_cancel_tx_status:
            self.write({
                'state': 'cancel',
                'acquirer_reference': data.get('BRQ_TRANSACTIONS'),
            })
            return True
        else:
            error = 'Buckaroo: feedback error'
            _logger.info(error)
            self.write({
                'state': 'error',
                'state_message': error,
                'acquirer_reference': data.get('BRQ_TRANSACTIONS'),
            })
            return False
