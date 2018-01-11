# -*- coding: utf-8 -*-

import hashlib
import hmac
import time
import urlparse
from lxml import objectify

import openerp
from openerp.addons.payment.models.payment_acquirer import ValidationError
from openerp.addons.payment.tests.common import PaymentAcquirerCommon
from openerp.addons.payment_authorize.controllers.main import AuthorizeController
from openerp.tools import mute_logger


@openerp.tests.common.at_install(True)
@openerp.tests.common.post_install(True)
class AuthorizeCommon(PaymentAcquirerCommon):

    def setUp(self):
        super(AuthorizeCommon, self).setUp()
        self.base_url = self.env['ir.config_parameter'].get_param('web.base.url')
        # authorize only support USD in test environment
        self.currency_usd = self.env['res.currency'].search([('name', '=', 'USD')], limit=1)[0]
        # get the authorize account
        model, self.authorize_id = self.env['ir.model.data'].get_object_reference('payment_authorize', 'payment_acquirer_authorize')


@openerp.tests.common.at_install(True)
@openerp.tests.common.post_install(True)
class AuthorizeForm(AuthorizeCommon):

    def _authorize_generate_hashing(self, values):
        data = '^'.join([
            values['x_login'],
            values['x_fp_sequence'],
            values['x_fp_timestamp'],
            values['x_amount'],
        ]) + '^'
        return hmac.new(str(values['x_trans_key']), data, hashlib.md5).hexdigest()

    def test_10_Authorize_form_render(self):
        authorize = self.env['payment.acquirer'].browse(self.authorize_id)
        self.assertEqual(authorize.environment, 'test', 'test without test environment')

        # ----------------------------------------
        # Test: button direct rendering
        # ----------------------------------------
        form_values = {
            'x_login': authorize.authorize_login,
            'x_trans_key': authorize.authorize_transaction_key,
            'x_amount': '320.0',
            'x_show_form': 'PAYMENT_FORM',
            'x_type': 'AUTH_CAPTURE',
            'x_method': 'CC',
            'x_fp_sequence': '%s%s' % (authorize.id, int(time.time())),
            'x_version': '3.1',
            'x_relay_response': 'TRUE',
            'x_fp_timestamp': str(int(time.time())),
            'x_relay_url': '%s' % urlparse.urljoin(self.base_url, AuthorizeController._return_url),
            'x_cancel_url': '%s' % urlparse.urljoin(self.base_url, AuthorizeController._cancel_url),
            'return_url': None,
            'x_currency_code': 'USD',
            'x_invoice_num': 'SO004',
            'x_first_name': 'Norbert',
            'x_last_name': 'Buyer',
            'x_address': 'Huge Street 2/543',
            'x_city': 'Sin City',
            'x_zip': '1000',
            'x_country': 'Belgium',
            'x_phone': '0032 12 34 56 78',
            'x_email': 'norbert.buyer@example.com',
            'x_state': None,
        }

        form_values['x_fp_hash'] = self._authorize_generate_hashing(form_values)
        # render the button
        cr, uid, context = self.env.cr, self.env.uid, {}
        res = self.payment_acquirer.render(
            cr, uid, self.authorize_id, 'SO004', 320.0, self.currency_usd.id,
            partner_id=None, partner_values=self.buyer_values, context=context)
        # check form result
        tree = objectify.fromstring(res)
        self.assertEqual(tree.get('action'), 'https://test.authorize.net/gateway/transact.dll', 'Authorize: wrong form POST url')
        for form_input in tree.input:
            # Generated and received 'x_fp_hash' are always different so skeep it.
            if form_input.get('name') in ['submit', 'x_fp_hash']:
                continue
            self.assertEqual(
                form_input.get('value'),
                form_values[form_input.get('name')],
                'Authorize: wrong value for input %s: received %s instead of %s' % (form_input.get('name'), form_input.get('value'), form_values[form_input.get('name')])
            )

    @mute_logger('openerp.addons.payment_authorize.models.authorize', 'ValidationError')
    def test_20_authorize_form_management(self):
        cr, uid, context = self.env.cr, self.env.uid, {}
        # be sure not to do stupid thing
        authorize = self.env['payment.acquirer'].browse(self.authorize_id)
        self.assertEqual(authorize.environment, 'test', 'test without test environment')

        # typical data posted by authorize after client has successfully paid
        authorize_post_data = {
            'return_url': u'/shop/payment/validate',
            'x_MD5_Hash': u'7934485E1C105940BE854208D10FAB4F',
            'x_account_number': u'XXXX0027',
            'x_address': u'Huge Street 2/543',
            'x_amount': u'320.00',
            'x_auth_code': u'E4W7IU',
            'x_avs_code': u'Y',
            'x_card_type': u'Visa',
            'x_cavv_response': u'2',
            'x_city': u'Sun City',
            'x_company': u'',
            'x_country': u'Belgium',
            'x_cust_id': u'',
            'x_cvv2_resp_code': u'',
            'x_description': u'',
            'x_duty': u'0.00',
            'x_email': u'norbert.buyer@exampl',
            'x_fax': u'',
            'x_first_name': u'Norbert',
            'x_freight': u'0.00',
            'x_invoice_num': u'SO004',
            'x_last_name': u'Buyer',
            'x_method': u'CC',
            'x_phone': u'0032 12 34 56 78',
            'x_po_num': u'',
            'x_response_code': u'1',
            'x_response_reason_code': u'1',
            'x_response_reason_text': u'This transaction has been approved.',
            'x_ship_to_address': u'Huge Street 2/543',
            'x_ship_to_city': u'Sun City',
            'x_ship_to_company': u'',
            'x_ship_to_country': u'Belgium',
            'x_ship_to_first_name': u'Norbert',
            'x_ship_to_last_name': u'Buyer',
            'x_ship_to_state': u'',
            'x_ship_to_zip': u'1000',
            'x_state': u'',
            'x_tax': u'0.00',
            'x_tax_exempt': u'FALSE',
            'x_test_request': u'false',
            'x_trans_id': u'2217460311',
            'x_type': u'auth_capture',
            'x_zip': u'1000'
        }

        # should raise error about unknown tx
        with self.assertRaises(ValidationError):
            self.payment_transaction.form_feedback(cr, uid, authorize_post_data, 'authorize', context=context)

        tx = self.env['payment.transaction'].create({
            'amount': 320.0,
            'acquirer_id': self.authorize_id,
            'currency_id': self.currency_usd.id,
            'reference': 'SO004',
            'partner_name': 'Norbert Buyer',
            'partner_country_id': self.country_france_id})
        # validate it
        self.payment_transaction.form_feedback(cr, uid, authorize_post_data, 'authorize', context=context)
        # check state
        self.assertEqual(tx.state, 'done', 'Authorize: validation did not put tx into done state')
        self.assertEqual(tx.authorize_txnid, authorize_post_data.get('x_trans_id'), 'Authorize: validation did not update tx payid')

        # reset tx
        tx.write({'state': 'draft', 'date_validate': False, 'authorize_txnid': False})

        # simulate an error
        authorize_post_data['x_response_code'] = u'3'
        self.payment_transaction.form_feedback(cr, uid, authorize_post_data, 'authorize', context=context)
        # check state
        self.assertEqual(tx.state, 'error', 'Authorize: erroneous validation did not put tx into error state')
