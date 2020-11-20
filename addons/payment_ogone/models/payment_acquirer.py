# coding: utf-8
import logging
import time
from hashlib import sha256
import requests
from werkzeug import urls

from odoo import api, fields, models, _
from odoo.addons.payment_ogone.controllers.main import OgoneController
from odoo.tools.float_utils import float_repr, float_round
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class PaymentAcquirer(models.Model):
    _inherit = 'payment.acquirer'

    provider = fields.Selection(selection_add=[
        ('ogone', 'Ogone')
    ], ondelete={'ogone': 'set default'})
    ogone_pspid = fields.Char('PSPID', required_if_provider='ogone', groups='base.group_user')
    ogone_userid = fields.Char('API User ID', required_if_provider='ogone', groups='base.group_user')
    ogone_password = fields.Char('API User Password', required_if_provider='ogone', groups='base.group_user')
    ogone_shakey_in = fields.Char('SHA Key IN', size=32, required_if_provider='ogone', groups='base.group_user')
    ogone_shakey_out = fields.Char('SHA Key OUT', size=32, required_if_provider='ogone', groups='base.group_user')

    def _get_validation_amount(self):
        """ Get the amount to transfer in a payment method validation operation.

        For an acquirer to support tokenization, it must override this method and return the amount
        to be transferred in a payment method validation operation.

        Note: self.ensure_one()

        :return: The validation amount
        :rtype: float
        """
        self.ensure_one()
        return 1.0



    @api.model
    def _ogone_get_urls(self):
        # arj fixme: CLEAN THESE TO ONLY KEEP THE ONE WE USE
        """ Ogone URLS:
         - standard order: POST address for form-based """
        # https://ogone.test.v-psp.com/Tokenization/HostedPage
        # https://secure.ogone.com/Tokenization/HostedPage
        environment = 'prod' if self.state == 'enabled' else 'test'
        if environment == 'prod':
            flexcheckout_url = "https://secure.ogone.com/Tokenization/HostedPage"
            direct_order_url = "https://secure.ogone.com/ncol/prod/orderdirect.asp"
            maintenance_direct_url = "https://secure.ogone.com/ncol/prod/maintenancedirect.asp"
        else:
            flexcheckout_url = "https://ogone.test.v-psp.com/Tokenization/HostedPage"
            direct_order_url = "https://ogone.test.v-psp.com/ncol/test/orderdirect.asp"
            maintenance_direct_url = "https://ogone.test.v-psp.com/ncol/test/maintenancedirect.asp"
        return {
            'ogone_direct_order_url': direct_order_url,
            # 'ogone_direct_query_url': 'https://secure.ogone.com/ncol/%s/querydirect_utf8.asp' % (environment,),
            # 'ogone_afu_agree_url': 'https://secure.ogone.com/ncol/%s/AFU_agree.asp' % (environment,),
            'ogone_flexcheckout_url': flexcheckout_url,
            'ogone_maintenance_url': maintenance_direct_url,
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
                # source https://payment-services.ingenico.com/int/en/ogone/support/guides/integration guides/e-commerce/transaction-feedback
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
                    'COLLECTOR_BIC',
                    'COLLECTOR_IBAN',
                    'COMPLUS',
                    'CREATION_STATUS',
                    'CREDITDEBIT',
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
                    'DEVICEID',
                    'DIGESTCARDNO',
                    'ECI',
                    'ED',
                    'EMAIL',
                    'ENCCARDNO',
                    'FXAMOUNT',
                    'FXCURRENCY',
                    'IP',
                    'IPCTY',
                    'MANDATEID',
                    'MOBILEMODE',
                    'NBREMAILUSAGE',
                    'NBRIPUSAGE',
                    'NBRIPUSAGE_ALLTX',
                    'NBRUSAGE',
                    'NCERROR',
                    'ORDERID',
                    'PAYID',
                    'PAYIDSUB',
                    'PAYMENT_REFERENCE',
                    'PM',
                    'SCO_CATEGORY',
                    'SCORING',
                    'SEQUENCETYPE',
                    'SIGNDATE',
                    'STATUS',
                    'SUBBRAND',
                    'SUBSCRIPTION_ID',
                    'TICKET',
                    'TRXDATE',
                    'VC',
                ]
                # Source https://epayments-support.ingenico.com/en/integration/all-sales-channels/flexcheckout/guide#flexcheckout_integration_guides_sha_out
                flexcheckout_out = ['ALIAS.ALIASID',
                                    'ALIAS.NCERROR',
                                    'ALIAS.NCERRORCARDNO',
                                    'ALIAS.NCERRORCN',
                                    'ALIAS.NCERRORCVC',
                                    'ALIAS.NCERRORED',
                                    'ALIAS.ORDERID',
                                    'ALIAS.STATUS',
                                    'ALIAS.STOREPERMANENTLY',
                                    'CARD.BIC',
                                    'CARD.BIN',
                                    'CARD.BRAND',
                                    'CARD.CARDHOLDERNAME',
                                    'CARD.CARDNUMBER',
                                    'CARD.CVC',
                                    'CARD.EXPIRYDATE'
                                    ]
                keys += flexcheckout_out
                return key.upper() in keys

        items = sorted((k.upper(), v) for k, v in values.items())
        sign = ''.join('%s=%s%s' % (k, v, key) for k, v in items if v and filter_key(k.upper()))
        sign = sign.encode("utf-8")
        shasign = sha256(sign).hexdigest()
        return shasign

    def _ogone_prepare_direct_order(self, values):
        base_url = self.get_base_url()
        ogone_tx_values = {
            'PSPID': self.ogone_pspid,
            'ORDERID': values['reference'],
            'AMOUNT': float_repr(float_round(values['amount'], 2) * 100, 0),
            'CURRENCY': values['currency_name'],
            'LANGUAGE': values.get('partner_lang'),
            'CN': values.get('partner_name'),
            'EMAIL': values.get('partner_email'),
            'OWNERZIP': values.get('partner_zip'),
            'OWNERADDRESS': values.get('partner_address'),
            'OWNERTOWN': values.get('partner_city'),
            'OWNERCTY': values.get('partner_country') and values.get('partner_country').code or '',
            'ACCEPTURL': urls.url_join(base_url, OgoneController._accept_url),
            'DECLINEURL': urls.url_join(base_url, OgoneController._decline_url),
            'EXCEPTIONURL': urls.url_join(base_url, OgoneController._exception_url),
            'CANCELURL': urls.url_join(base_url, OgoneController._cancel_url),
            'ALIAS': values.get('AliasId'),
        }
        shasign = self._ogone_generate_shasign('in', ogone_tx_values)
        ogone_tx_values['SHASIGN'] = shasign
        return ogone_tx_values

    def ogone_form_generate_values(self, values):
        base_url = self.get_base_url()
        param_plus = {
            'acquirerId': self.id,
            'partnerId': values.get('partner_id'),
            'currencyId': values.get('currency_id'),
            'orderId': values.get('order_id'),
            'amount': values.get('amount'),
            'paymentOptionId': values.get('param_plus').get('payment_option_id'),
            'referencePrefix': values.get('param_plus').get('reference_prefix'),
            'flow': values.get('param_plus').get('flow'),
            'landingRoute': values.get('param_plus').get('landing_route'),
            'initTxRoute': values.get('param_plus').get('init_tx_route'),
            'access_token': values.get('param_plus').get('access_token'),
        }
        if values.get('param_plus').get('isValidation'):
            # We avoid to display the validation key if not true because javascript will receive isValidation = "False"
            param_plus.update({'isValidation': True})
        if values.get('param_plus').get('validation_route'):
            param_plus.update({'validationRoute': True})
            param_plus.update({'isValidation': True})

        ogone_tx_values = {
            'ACCOUNT.PSPID': self.ogone_pspid,
            'ALIAS.ORDERID': values['reference'],
            'LAYOUT.LANGUAGE': values.get('partner_lang'),
            'CARD.PAYMENTMETHOD': 'CreditCard',
            'PARAMETERS.ACCEPTURL': urls.url_join(base_url, OgoneController._fleckcheckout_url),
            'PARAMETERS.EXCEPTIONURL': urls.url_join(base_url, OgoneController._fleckcheckout_url),
            # arj fixme: remove arj from the alias
            'ALIAS.ALIASID': 'ARJ-ODOO-NEW-ALIAS-%s' % time.time(),  # something unique,
            'PARAMPLUS': urls.url_encode(param_plus),
        }
        shasign = self._ogone_generate_shasign('in', ogone_tx_values)
        ogone_tx_values['SHASIGNATURE.SHASIGN'] = shasign
        ogone_tx_values.update(ogone_tx_values)
        return ogone_tx_values

    def ogone_get_form_action_url(self):
        self.ensure_one()
        environment = 'prod' if self.state == 'enabled' else 'test'
        return self._get_ogone_urls(environment)['ogone_flexcheckout_url']

    @api.model
    def _ogone_setup_iframe(self, data):
        ogone_values = self.ogone_form_generate_values(data)
        url_parameters = urls.url_encode(ogone_values)
        base_url = self._ogone_get_urls()['ogone_flexcheckout_url']
        full_checkout_url = base_url + '?' + url_parameters
        return full_checkout_url

    @api.model
    def _ogone_clean_data_keys(self):
        return {}