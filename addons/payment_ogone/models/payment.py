# coding: utf-8
import base64
import datetime
import logging
import time
from hashlib import sha1
from pprint import pformat
from unicodedata import normalize

import requests
from lxml import etree, objectify
from werkzeug import urls, url_encode

from odoo import api, fields, models, _
from odoo.addons.payment.models.payment_acquirer import ValidationError
from odoo.addons.payment_ogone.controllers.main import OgoneController
from odoo.addons.payment_ogone.data import ogone
from odoo.tools import float_round, DEFAULT_SERVER_DATE_FORMAT
from odoo.tools.float_utils import float_compare, float_repr
from odoo.tools.safe_eval import safe_eval

_logger = logging.getLogger(__name__)


class PaymentAcquirerOgone(models.Model):
    _inherit = 'payment.acquirer'

    provider = fields.Selection(selection_add=[('ogone', 'Ogone')])
    ogone_pspid = fields.Char('PSPID', required_if_provider='ogone', groups='base.group_user')
    ogone_userid = fields.Char('API User ID', required_if_provider='ogone', groups='base.group_user')
    ogone_password = fields.Char('API User Password', required_if_provider='ogone', groups='base.group_user')
    ogone_shakey_in = fields.Char('SHA Key IN', size=32, required_if_provider='ogone', groups='base.group_user')
    ogone_shakey_out = fields.Char('SHA Key OUT', size=32, required_if_provider='ogone', groups='base.group_user')
    ogone_alias_usage = fields.Char('Alias Usage', default="Allow saving my payment data",
                                    help="If you want to use Ogone Aliases, this default "
                                    "Alias Usage will be presented to the customer as the "
                                    "reason you want to keep his payment data")

    def _get_feature_support(self):
        """Get advanced feature support by provider.

        Each provider should add its technical in the corresponding
        key for the following features:
            * fees: support payment fees computations
            * authorize: support authorizing payment (separates
                         authorization and capture)
            * tokenize: support saving payment data in a payment.tokenize
                        object
        """
        res = super(PaymentAcquirerOgone, self)._get_feature_support()
        res['tokenize'].append('ogone')
        return res

    def _get_ogone_urls(self, environment):
        """ Ogone URLS:
         - standard order: POST address for form-based """
        return {
            'ogone_standard_order_url': 'https://secure.ogone.com/ncol/%s/orderstandard_utf8.asp' % (environment,),
            'ogone_direct_order_url': 'https://secure.ogone.com/ncol/%s/orderdirect_utf8.asp' % (environment,),
            'ogone_direct_query_url': 'https://secure.ogone.com/ncol/%s/querydirect_utf8.asp' % (environment,),
            'ogone_afu_agree_url': 'https://secure.ogone.com/ncol/%s/AFU_agree.asp' % (environment,),
        }

    def _ogone_generate_shasign(self, inout, values):
        """ Generate the shasign for incoming or outgoing communications.

        :param string inout: 'in' (odoo contacting ogone) or 'out' (ogone
                             contacting odoo). In this last case only some
                             fields should be contained (see e-Commerce basic)
        :param dict values: transaction values

        :return string: shasign
        """
        assert inout in ('in', 'out')
        assert self.provider == 'ogone'
        key = getattr(self, 'ogone_shakey_' + inout)

        def filter_key(key):
            if inout == 'in':
                return True
            else:
                # SHA-OUT keys
                # source https://viveum.v-psp.com/Ncol/Viveum_e-Com-BAS_EN.pdf
                keys = [
                    'AAVADDRESS',
                    'AAVCHECK',
                    'AAVMAIL',
                    'AAVNAME',
                    'AAVPHONE',
                    'AAVZIP',
                    'ACCEPTANCE',
                    'ALIAS',
                    'AMOUNT',
                    'BIC',
                    'BIN',
                    'BRAND',
                    'CARDNO',
                    'CCCTY',
                    'CN',
                    'COMPLUS',
                    'CREATION_STATUS',
                    'CURRENCY',
                    'CVCCHECK',
                    'DCC_COMMPERCENTAGE',
                    'DCC_CONVAMOUNT',
                    'DCC_CONVCCY',
                    'DCC_EXCHRATE',
                    'DCC_EXCHRATESOURCE',
                    'DCC_EXCHRATETS',
                    'DCC_INDICATOR',
                    'DCC_MARGINPERCENTAGE',
                    'DCC_VALIDHOURS',
                    'DIGESTCARDNO',
                    'ECI',
                    'ED',
                    'ENCCARDNO',
                    'FXAMOUNT',
                    'FXCURRENCY',
                    'IBAN',
                    'IP',
                    'IPCTY',
                    'NBREMAILUSAGE',
                    'NBRIPUSAGE',
                    'NBRIPUSAGE_ALLTX',
                    'NBRUSAGE',
                    'NCERROR',
                    'NCERRORCARDNO',
                    'NCERRORCN',
                    'NCERRORCVC',
                    'NCERRORED',
                    'ORDERID',
                    'PAYID',
                    'PAYIDSUB',
                    'PM',
                    'SCO_CATEGORY',
                    'SCORING',
                    'STATUS',
                    'SUBBRAND',
                    'SUBSCRIPTION_ID',
                    'TRXDATE',
                    'VC'
                ]
                return key.upper() in keys

        items = sorted((k.upper(), v) for k, v in values.items())
        sign = ''.join('%s=%s%s' % (k, v, key) for k, v in items if v and filter_key(k))
        sign = sign.encode("utf-8")
        shasign = sha1(sign).hexdigest()
        return shasign

    def ogone_form_generate_values(self, values):
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        ogone_tx_values = dict(values)
        temp_ogone_tx_values = {
            'PSPID': self.ogone_pspid,
            'ORDERID': values['reference'],
            'AMOUNT': float_repr(float_round(values['amount'], 2) * 100, 0),
            'CURRENCY': values['currency'] and values['currency'].name or '',
            'LANGUAGE': values.get('partner_lang'),
            'CN': values.get('partner_name'),
            'EMAIL': values.get('partner_email'),
            'OWNERZIP': values.get('partner_zip'),
            'OWNERADDRESS': values.get('partner_address'),
            'OWNERTOWN': values.get('partner_city'),
            'OWNERCTY': values.get('partner_country') and values.get('partner_country').code or '',
            'OWNERTELNO': values.get('partner_phone'),
            'ACCEPTURL': urls.url_join(base_url, OgoneController._accept_url),
            'DECLINEURL': urls.url_join(base_url, OgoneController._decline_url),
            'EXCEPTIONURL': urls.url_join(base_url, OgoneController._exception_url),
            'CANCELURL': urls.url_join(base_url, OgoneController._cancel_url),
            'PARAMPLUS': 'return_url=%s' % ogone_tx_values.pop('return_url') if ogone_tx_values.get('return_url') else False,
        }
        if self.save_token in ['ask', 'always']:
            temp_ogone_tx_values.update({
                'ALIAS': 'ODOO-NEW-ALIAS-%s' % time.time(),    # something unique,
                'ALIASUSAGE': values.get('alias_usage') or self.ogone_alias_usage,
            })
        shasign = self._ogone_generate_shasign('in', temp_ogone_tx_values)
        temp_ogone_tx_values['SHASIGN'] = shasign
        ogone_tx_values.update(temp_ogone_tx_values)
        return ogone_tx_values

    def ogone_get_form_action_url(self):
        return self._get_ogone_urls(self.environment)['ogone_standard_order_url']

    def ogone_s2s_form_validate(self, data):
        error = dict()

        mandatory_fields = ["cc_number", "cc_cvc", "cc_holder_name", "cc_expiry", "cc_brand"]
        # Validation
        for field_name in mandatory_fields:
            if not data.get(field_name):
                error[field_name] = 'missing'

        return False if error else True

    def ogone_s2s_form_process(self, data):
        values = {
            'cc_number': data.get('cc_number'),
            'cc_cvc': int(data.get('cc_cvc')),
            'cc_holder_name': data.get('cc_holder_name'),
            'cc_expiry': data.get('cc_expiry'),
            'cc_brand': data.get('cc_brand'),
            'acquirer_id': int(data.get('acquirer_id')),
            'partner_id': int(data.get('partner_id'))
        }
        pm_id = self.env['payment.token'].sudo().create(values)
        return pm_id


class PaymentTxOgone(models.Model):
    _inherit = 'payment.transaction'
    # ogone status
    _ogone_valid_tx_status = [5, 9]
    _ogone_wait_tx_status = [41, 50, 51, 52, 55, 56, 91, 92, 99]
    _ogone_pending_tx_status = [46]   # 3DS HTML response
    _ogone_cancel_tx_status = [1]

    # --------------------------------------------------
    # FORM RELATED METHODS
    # --------------------------------------------------

    @api.model
    def _ogone_form_get_tx_from_data(self, data):
        """ Given a data dict coming from ogone, verify it and find the related
        transaction record. Create a payment token if an alias is returned."""
        reference, pay_id, shasign, alias = data.get('orderID'), data.get('PAYID'), data.get('SHASIGN'), data.get('ALIAS')
        if not reference or not pay_id or not shasign:
            error_msg = _('Ogone: received data with missing reference (%s) or pay_id (%s) or shasign (%s)') % (reference, pay_id, shasign)
            _logger.info(error_msg)
            raise ValidationError(error_msg)

        # find tx -> @TDENOTE use paytid ?
        tx = self.search([('reference', '=', reference)])
        if not tx or len(tx) > 1:
            error_msg = _('Ogone: received data for reference %s') % (reference)
            if not tx:
                error_msg += _('; no order found')
            else:
                error_msg += _('; multiple order found')
            _logger.info(error_msg)
            raise ValidationError(error_msg)

        # verify shasign
        shasign_check = tx.acquirer_id._ogone_generate_shasign('out', data)
        if shasign_check.upper() != shasign.upper():
            error_msg = _('Ogone: invalid shasign, received %s, computed %s, for data %s') % (shasign, shasign_check, data)
            _logger.info(error_msg)
            raise ValidationError(error_msg)

        if not tx.acquirer_reference:
            tx.acquirer_reference = pay_id

        # alias was created on ogone server, store it
        if alias and tx.type == 'form_save':
            Token = self.env['payment.token']
            domain = [('acquirer_ref', '=', alias)]
            cardholder = data.get('CN')
            if not Token.search_count(domain):
                _logger.info('Ogone: saving alias %s for partner %s' % (data.get('CARDNO'), tx.partner_id))
                ref = Token.create({'name': data.get('CARDNO') + (' - ' + cardholder if cardholder else ''),
                                    'partner_id': tx.partner_id.id,
                                    'acquirer_id': tx.acquirer_id.id,
                                    'acquirer_ref': alias})
                tx.write({'payment_token_id': ref.id})

        return tx

    def _ogone_form_get_invalid_parameters(self, data):
        invalid_parameters = []

        # TODO: txn_id: should be false at draft, set afterwards, and verified with txn details
        if self.acquirer_reference and data.get('PAYID') != self.acquirer_reference:
            invalid_parameters.append(('PAYID', data.get('PAYID'), self.acquirer_reference))
        # check what is bought
        if float_compare(float(data.get('amount', '0.0')), self.amount, 2) != 0:
            invalid_parameters.append(('amount', data.get('amount'), '%.2f' % self.amount))
        if data.get('currency') != self.currency_id.name:
            invalid_parameters.append(('currency', data.get('currency'), self.currency_id.name))

        return invalid_parameters

    def _ogone_form_validate(self, data):
        if self.state in ['done', 'refunded']:
            _logger.info('Ogone: trying to validate an already validated tx (ref %s)', self.reference)
            return True

        status = int(data.get('STATUS', '0'))
        if status in self._ogone_valid_tx_status:
            vals = {
                'state': 'done',
                'date_validate': datetime.datetime.strptime(data['TRXDATE'], '%m/%d/%y').strftime(DEFAULT_SERVER_DATE_FORMAT),
                'acquirer_reference': data['PAYID'],
            }
            if data.get('ALIAS') and self.partner_id and \
               (self.type == 'form_save' or self.acquirer_id.save_token == 'always')\
               and not self.payment_token_id:
                pm = self.env['payment.token'].create({
                    'partner_id': self.partner_id.id,
                    'acquirer_id': self.acquirer_id.id,
                    'acquirer_ref': data.get('ALIAS'),
                    'name': '%s - %s' % (data.get('CARDNO'), data.get('CN'))
                })
                vals.update(payment_token_id=pm.id)
            self.write(vals)
            if self.payment_token_id:
                self.payment_token_id.verified = True
            self.execute_callback()
            # if this transaction is a validation one, then we refund the money we just withdrawn
            if self.type == 'validation':
                self.s2s_do_refund()

            return True
        elif status in self._ogone_cancel_tx_status:
            self.write({
                'state': 'cancel',
                'acquirer_reference': data.get('PAYID'),
            })
        elif status in self._ogone_pending_tx_status or status in self._ogone_wait_tx_status:
            self.write({
                'state': 'pending',
                'acquirer_reference': data.get('PAYID'),
            })
        else:
            error = 'Ogone: feedback error: %(error_str)s\n\n%(error_code)s: %(error_msg)s' % {
                'error_str': data.get('NCERRORPLUS'),
                'error_code': data.get('NCERROR'),
                'error_msg': ogone.OGONE_ERROR_MAP.get(data.get('NCERROR')),
            }
            _logger.info(error)
            self.write({
                'state': 'error',
                'state_message': error,
                'acquirer_reference': data.get('PAYID'),
            })
            return False

    # --------------------------------------------------
    # S2S RELATED METHODS
    # --------------------------------------------------
    def ogone_s2s_do_transaction(self, **kwargs):
        # TODO: create tx with s2s type
        account = self.acquirer_id
        reference = self.reference or "ODOO-%s-%s" % (datetime.datetime.now().strftime('%y%m%d_%H%M%S'), self.partner_id.id)

        param_plus = {
            'return_url': kwargs.get('return_url', False)
        }

        data = {
            'PSPID': account.ogone_pspid,
            'USERID': account.ogone_userid,
            'PSWD': account.ogone_password,
            'ORDERID': reference,
            'AMOUNT': int(self.amount * 100),
            'CURRENCY': self.currency_id.name,
            'OPERATION': 'SAL',
            'ECI': 2,   # Recurring (from MOTO)
            'ALIAS': self.payment_token_id.acquirer_ref,
            'RTIMEOUT': 30,
            'PARAMPLUS' : url_encode(param_plus)
        }

        if kwargs.get('3d_secure'):
            data.update({
                'FLAG3D': 'Y',
                'LANGUAGE': self.partner_id.lang or 'en_US',
            })

            for url in 'accept decline exception'.split():
                key = '{0}_url'.format(url)
                val = kwargs.pop(key, None)
                if val:
                    key = '{0}URL'.format(url).upper()
                    data[key] = val

        data['SHASIGN'] = self.acquirer_id._ogone_generate_shasign('in', data)

        direct_order_url = 'https://secure.ogone.com/ncol/%s/orderdirect.asp' % (self.acquirer_id.environment)

        _logger.debug("Ogone data %s", pformat(data))
        result = requests.post(direct_order_url, data=data).content
        _logger.debug('Ogone response = %s', result)

        try:
            tree = objectify.fromstring(result)
        except etree.XMLSyntaxError:
            # invalid response from ogone
            _logger.exception('Invalid xml response from ogone')
            raise

        return self._ogone_s2s_validate_tree(tree)

    def ogone_s2s_do_refund(self, **kwargs):

        # we refund only if this transaction hasn't been already refunded and was paid.
        if self.state != 'done':
            return False

        self.state = 'refunding'
        account = self.acquirer_id
        reference = self.reference or "ODOO-%s-%s" % (datetime.datetime.now().strftime('%y%m%d_%H%M%S'), self.partner_id.id)

        data = {
            'PSPID': account.ogone_pspid,
            'USERID': account.ogone_userid,
            'PSWD': account.ogone_password,
            'ORDERID': reference,
            'AMOUNT': int(self.amount * 100),
            'CURRENCY': self.currency_id.name,
            'OPERATION': 'RFD',
            'ECI': 2,   # Recurring (from MOTO)
            'ALIAS': self.payment_token_id.acquirer_ref,
            'RTIMEOUT': 30,
        }

        direct_order_url = 'https://secure.ogone.com/ncol/%s/orderdirect.asp' % (self.acquirer_id.environment)

        _logger.debug("Ogone data %s", pformat(data))
        result = requests.post(direct_order_url, data=data).content
        _logger.debug('Ogone response = %s', result)

        try:
            tree = objectify.fromstring(result)
        except etree.XMLSyntaxError:
            # invalid response from ogone
            _logger.exception('Invalid xml response from ogone')
            raise

        return self._ogone_s2s_validate_tree(tree)

    def _ogone_s2s_validate(self):
        tree = self._ogone_s2s_get_tx_status()
        return self._ogone_s2s_validate_tree(tree)

    def _ogone_s2s_validate_tree(self, tree, tries=2):
        if self.state not in ('draft', 'pending', 'refunding'):
            _logger.info('Ogone: trying to validate an already validated tx (ref %s)', self.reference)
            return True

        status = int(tree.get('STATUS') or 0)
        if status in self._ogone_valid_tx_status:
            new_state = 'refunded' if self.state == 'refunding' else 'done'
            self.write({
                'state': new_state,
                'date_validate': datetime.date.today().strftime(DEFAULT_SERVER_DATE_FORMAT),
                'acquirer_reference': tree.get('PAYID'),
            })
            if tree.get('ALIAS') and self.partner_id and \
               (self.type == 'form_save' or self.acquirer_id.save_token == 'always')\
               and not self.payment_token_id:
                pm = self.env['payment.token'].create({
                    'partner_id': self.partner_id.id,
                    'acquirer_id': self.acquirer_id.id,
                    'acquirer_ref': tree.get('ALIAS'),
                    'name': tree.get('CARDNO'),
                })
                self.write({'payment_token_id': pm.id})
            if self.payment_token_id:
                self.payment_token_id.verified = True
            self.execute_callback()
            return True
        elif status in self._ogone_cancel_tx_status:
            self.write({
                'state': 'cancel',
                'acquirer_reference': tree.get('PAYID'),
            })
        elif status in self._ogone_pending_tx_status:
            new_state = 'refunding' if self.state == 'refunding' else 'pending'
            self.write({
                'state': new_state,
                'acquirer_reference': tree.get('PAYID'),
                'html_3ds': base64.b64decode(tree.HTML_ANSWER.decode('ascii')),
            })
        elif status in self._ogone_wait_tx_status and tries > 0:
            time.sleep(0.5)
            self.write({'acquirer_reference': tree.get('PAYID')})
            tree = self._ogone_s2s_get_tx_status()
            return self._ogone_s2s_validate_tree(tree, tries - 1)
        else:
            error = 'Ogone: feedback error: %(error_str)s\n\n%(error_code)s: %(error_msg)s' % {
                'error_str': tree.get('NCERRORPLUS'),
                'error_code': tree.get('NCERROR'),
                'error_msg': ogone.OGONE_ERROR_MAP.get(tree.get('NCERROR')),
            }
            _logger.info(error)
            self.write({
                'state': 'error',
                'state_message': error,
                'acquirer_reference': tree.get('PAYID'),
            })
            return False

    def _ogone_s2s_get_tx_status(self):
        account = self.acquirer_id
        #reference = tx.reference or "ODOO-%s-%s" % (datetime.datetime.now().strftime('%Y%m%d_%H%M%S'), tx.partner_id.id)

        data = {
            'PAYID': self.acquirer_reference,
            'PSPID': account.ogone_pspid,
            'USERID': account.ogone_userid,
            'PSWD': account.ogone_password,
        }

        query_direct_url = 'https://secure.ogone.com/ncol/%s/querydirect.asp' % (self.acquirer_id.environment)

        _logger.debug("Ogone data %s", pformat(data))
        result = requests.post(query_direct_url, data=data).content
        _logger.debug('Ogone response = %s', result)

        try:
            tree = objectify.fromstring(result)
        except etree.XMLSyntaxError:
            # invalid response from ogone
            _logger.exception('Invalid xml response from ogone')
            raise

        return tree


class PaymentToken(models.Model):
    _inherit = 'payment.token'

    def ogone_create(self, values):
        if values.get('cc_number'):
            # create a alias via batch
            values['cc_number'] = values['cc_number'].replace(' ', '')
            acquirer = self.env['payment.acquirer'].browse(values['acquirer_id'])
            alias = 'ODOO-NEW-ALIAS-%s' % time.time()

            expiry = str(values['cc_expiry'][:2]) + str(values['cc_expiry'][-2:])
            line = 'ADDALIAS;%(alias)s;%(cc_holder_name)s;%(cc_number)s;%(expiry)s;%(cc_brand)s;%(pspid)s'
            line = line % dict(values, alias=alias, expiry=expiry, pspid=acquirer.ogone_pspid)

            data = {
                'FILE_REFERENCE': alias,
                'TRANSACTION_CODE': 'MTR',
                'OPERATION': 'SAL',
                'NB_PAYMENTS': 1,   # even if we do not actually have any payment, ogone want it to not be 0
                'FILE': normalize('NFKD', line).encode('ascii','ignore'),  # Ogone Batch must be ASCII only
                'REPLY_TYPE': 'XML',
                'PSPID': acquirer.ogone_pspid,
                'USERID': acquirer.ogone_userid,
                'PSWD': acquirer.ogone_password,
                'PROCESS_MODE': 'CHECKANDPROCESS',
            }

            url = 'https://secure.ogone.com/ncol/%s/AFU_agree.asp' % (acquirer.environment,)
            result = requests.post(url, data=data).content

            try:
                tree = objectify.fromstring(result)
            except etree.XMLSyntaxError:
                _logger.exception('Invalid xml response from ogone')
                return None

            error_code = error_str = None
            if hasattr(tree, 'PARAMS_ERROR'):
                error_code = tree.NCERROR.text
                error_str = 'PARAMS ERROR: %s' % (tree.PARAMS_ERROR.text or '',)
            else:
                node = tree.FORMAT_CHECK
                error_node = getattr(node, 'FORMAT_CHECK_ERROR', None)
                if error_node is not None:
                    error_code = error_node.NCERROR.text
                    error_str = 'CHECK ERROR: %s' % (error_node.ERROR.text or '',)

            if error_code:
                error_msg = tree.get(error_code)
                error = '%s\n\n%s: %s' % (error_str, error_code, error_msg)
                _logger.error(error)
                raise Exception(error)

            return {
                'acquirer_ref': alias,
                'name': 'XXXXXXXXXXXX%s - %s' % (values['cc_number'][-4:], values['cc_holder_name'])
            }
        return {}