# -*- coding: utf-'8' "-*-"

try:
    import simplejson as json
except ImportError:
    import json
import logging
from hashlib import sha256
import urlparse
import unicodedata

from openerp.addons.payment.models.payment_acquirer import ValidationError
from openerp.addons.payment_sips.controllers.main import SipsController
from openerp.osv import osv, fields
from openerp.tools.float_utils import float_compare
from openerp import SUPERUSER_ID

_logger = logging.getLogger(__name__)


UNORMALIZE_CHARS = {
    u'Š': u'S', u'š': u's', u'Đ': u'Dj', u'đ': u'dj', u'Ž': u'Z', u'ž': u'z',
    u'Č': u'C', u'č': u'c', u'Ć': u'C', u'ć': u'c', u'À': u'A', u'Á': u'A', u'Â': u'A', u'Ã': u'A',
    u'Ä': u'A', u'Å': u'A', u'Æ': u'A', u'Ç': u'C', u'È': u'E', u'É': u'E', u'Ê': u'E', u'Ë': u'E',
    u'Ì': u'I', u'Í': u'I', u'Î': u'I', u'Ï': u'I', u'Ñ': u'N', u'Ò': u'O', u'Ó': u'O', u'Ô': u'O',
    u'Õ': u'O', u'Ö': u'O', u'Ø': u'O', u'Ù': u'U', u'Ú': u'U', u'Û': u'U', u'Ü': u'U', u'Ý': u'Y',
    u'Þ': u'B', u'ß': u'Ss', u'à': u'a', u'á': u'a', u'â': u'a', u'ã': u'a', u'ä': u'a', u'å': u'a',
    u'æ': u'a', u'ç': u'c', u'è': u'e', u'é': u'e', u'ê': u'e', u'ë': u'e', u'ì': u'i', u'í': u'i',
    u'î': u'i', u'ï': u'i', u'ð': u'o', u'ñ': u'n', u'ò': u'o', u'ó': u'o', u'ô': u'o', u'õ': u'o',
    u'ö': u'o', u'ø': u'o', u'ù': u'u', u'ú': u'u', u'û': u'u', u'ý': u'y', u'ý': u'y', u'þ': u'b',
    u'ÿ': u'y', u'Ŕ': u'R', u'ŕ': u'r', u"`": u"'", u"´": u"'", u"„": u",", u"`": u"'",
    u"´": u"'", u"“": u"\"", u"”": u"\"", u"´": u"'", u"&acirc;€™": u"'", u"{": u"",
    u"~": u"", u"–": u"-", u"’": u"'", u">": u" ", u"<": u" "
}


def unormalize(text):
    if not text:
        return text

    for inv_char, valid_char in UNORMALIZE_CHARS.items():
        text = text.replace(inv_char, valid_char)
    text = unicodedata.normalize('NFKD', text)
    return text


class AcquirerSips(osv.Model):
    _inherit = 'payment.acquirer'

    def _get_sips_urls(self, cr, uid, environment, context=None):
        """ Paypal URLS """
        if environment == 'prod':
            return {
                'sips_form_url': 'https://payment-webinit.sips-atos.com/paymentInit',
            }
        else:
            return {
                'sips_form_url': 'https://payment-webinit.simu.sips-atos.com/paymentInit',
            }

    def _get_providers(self, cr, uid, context=None):
        providers = super(AcquirerSips, self)._get_providers(cr, uid, context=context)
        providers.append(['sips', 'Sips'])
        return providers

    _columns = {
        'sips_merchant_id': fields.char('API User Password', required_if_provider='sips'),
        'sips_secret': fields.char('Secret', size=64, required_if_provider='sips'),
    }

    _defaults = {
    }

    def _sips_generate_shasign(self, acquirer, values):
        """ Generate the shasign for incoming or outgoing communications.

        :param browse acquirer: the payment.acquirer browse record. It should
                                have a shakey in shaky out
        :param dict values: transaction values

        :return string: shasign
        """
        assert acquirer.provider == 'sips'
        data = values['Data']

        key = u'002001000000001_KEY1'
        if acquirer.environment == 'prod':
            key = getattr(acquirer, 'sips_secret')

        shasign = sha256(data + key)
        return shasign.hexdigest()

    def sips_form_generate_values(
            self, cr, uid, id, partner_values, tx_values, context=None):
        base_url = self.pool['ir.config_parameter'].get_param(
            cr, SUPERUSER_ID, 'web.base.url')
        acquirer = self.browse(cr, uid, id, context=context)

        currency_code = '978'
        amount = int(tx_values.get('amount') * 100)
        if acquirer.environment == 'prod':
            merchant_id = getattr(acquirer, 'sips_merchant_id')
            key_version = '2'
        else:
            merchant_id = '002001000000001'
            key_version = '1'

        sips_tx_values = dict(tx_values)
        sips_tx_values.update({
            'Data': u'amount=%s|' % amount +
                    u'currencyCode=%s|' % currency_code +
                    u'merchantId=%s|' % merchant_id +
                    u'normalReturnUrl=%s|' % urlparse.urljoin(base_url, SipsController._return_url) +
                    u'transactionReference=%s|' % tx_values['reference'] +
                    u'keyVersion=%s' % key_version,
            'InterfaceVersion': 'HP_2.3',
        })

        returnContext = {}
        if sips_tx_values.get('return_url'):
            returnContext[u'return_url'] = u'%s' % sips_tx_values.pop('return_url')
        returnContext[u'reference'] = u'%s' % sips_tx_values['reference']
        sips_tx_values['Data'] += u'|returnContext=%s' % (json.dumps(returnContext))

        shasign = self._sips_generate_shasign(acquirer, sips_tx_values)
        sips_tx_values['Seal'] = shasign
        return partner_values, sips_tx_values

    def sips_get_form_action_url(self, cr, uid, id, context=None):
        acquirer = self.browse(cr, uid, id, context=context)
        return self._get_sips_urls(cr, uid, acquirer.environment, context=context)['sips_form_url']


class TxSips(osv.Model):
    _inherit = 'payment.transaction'

    # sips status
    _sips_valid_tx_status = ['00']
    _sips_wait_tx_status = ['90', '99']
    _sips_refused_tx_status = ['05', '14', '34', '54', '75', '97']
    _sips_error_tx_status = ['03', '12', '24', '25', '30', '40', '51', '63', '94']
    _sips_pending_tx_status = ['60']
    _sips_cancel_tx_status = ['17']

    # --------------------------------------------------
    # FORM RELATED METHODS
    # --------------------------------------------------

    def _sips_data_to_object(self, data):
        res = {}
        for element in data.split('|'):
            element_split = element.split('=')
            res[element_split[0]] = element_split[1]
        return res

    def _sips_form_get_tx_from_data(self, cr, uid, data, context=None):
        """ Given a data dict coming from sips, verify it and find the related
        transaction record. """

        data = self._sips_data_to_object(data.get('Data'))
        reference = data.get('transactionReference')

        if not reference:
            custom = json.loads(data.pop('returnContext', False) or '{}')
            reference = custom.get('reference')

        tx_ids = self.pool['payment.transaction'].search(cr, uid, [
            ('reference', '=', reference)], context=context)
        if not tx_ids or len(tx_ids) > 1:
            error_msg = 'Sips: received data for reference %s' % reference
            if not tx_ids:
                error_msg += '; no order found'
            else:
                error_msg += '; multiple order found'
            _logger.error(error_msg)
            raise ValidationError(error_msg)
        return self.browse(cr, uid, tx_ids[0], context=context)

    def _sips_form_get_invalid_parameters(self, cr, uid, tx, data, context=None):
        invalid_parameters = []

        data = self._sips_data_to_object(data.get('Data'))

        # TODO: txn_id: shoudl be false at draft, set afterwards, and verified with txn details
        if tx.acquirer_reference and data.get('transactionReference') != tx.acquirer_reference:
            invalid_parameters.append(('transactionReference', data.get('transactionReference'), tx.acquirer_reference))
        # check what is buyed
        if float_compare(float(data.get('amount', '0.0')) / 100, tx.amount, 2) != 0:
            print float(data.get('amount', '0.0'))
            invalid_parameters.append(('amount', data.get('amount'), '%.2f' % tx.amount))
        if tx.partner_reference and data.get('customerId') != tx.partner_reference:
            invalid_parameters.append(('customerId', data.get('customerId'), tx.partner_reference))

        return invalid_parameters

    def _sips_form_validate(self, cr, uid, tx, data, context=None):
        data = self._sips_data_to_object(data.get('Data'))

        status = data.get('responseCode')
        data = {
            'acquirer_reference': data.get('transactionReference'),
            'partner_reference': data.get('customerId')
        }
        if status in self._sips_valid_tx_status:
            msg = 'Payment for tx ref: %s, got response [%s], set as done.' % \
                  (tx.reference, status)
            _logger.info(msg)
            data.update(state='done', state_message=msg)
        elif status in self._sips_error_tx_status:
            error = 'Payment for tx ref: %s, got response [%s], set as ' \
                    'error.' % (tx.reference, status)
            _logger.info(error)
            data.update(state='error', state_message=error)
        elif status in self._sips_wait_tx_status:
            error = 'Received wait status for payment ref: %s, got response ' \
                    '[%s], set as error.' % (tx.reference, status)
            _logger.info(error)
            data.update(state='error', state_message=error)
        elif status in self._sips_refused_tx_status:
            error = 'Received refused status for payment ref: %s, got response' \
                    ' [%s], set as error.' % (tx.reference, status)
            _logger.info(error)
            data.update(state='error', state_message=error)
        elif status in self._sips_pending_tx_status:
            _logger.info('Payment ref: %s, got response [%s] set as pending.'
                         % (tx.reference, status))
            data.update(state='pending')
        elif status in self._sips_cancel_tx_status:
            error = 'Received notification for payment ref: %s, got response ' \
                    '[%s], set as cancel.' % (tx.reference, status)
            _logger.info(error)
            data.update(state='cancel', state_message=error)
        else:
            error = 'Received unrecognized status for payment ref: %s, got ' \
                    'response [%s], set as error.' % (tx.reference, status)
            _logger.info(error)
            data.update(state='error', state_message=error)
        data.update(date_validate=data.get('transactionDateTime',
                                           fields.datetime.now()))
        tx.write(data)
        return tx.id


