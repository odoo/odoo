# -*- coding: utf-8 -*-

import time
from werkzeug import urls
from lxml import objectify

import odoo
from odoo.addons.payment.models.payment_acquirer import ValidationError
from odoo.addons.payment.tests.common import PaymentAcquirerCommon
from odoo.addons.payment_authorize.controllers.main import AuthorizeController
from odoo.tools import mute_logger


@odoo.tests.tagged('post_install', '-at_install')
class AuthorizeCommon(PaymentAcquirerCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        super().setUpClass(chart_template_ref=chart_template_ref)
        # authorize only support USD in test environment
        cls.currency_usd = cls.env['res.currency'].search([('name', '=', 'USD')], limit=1)[0]
        # get the authorize account
        cls.authorize = cls.env.ref('payment.payment_acquirer_authorize')
        cls.authorize.write({
            'authorize_login': 'dummy',
            'authorize_transaction_key': 'dummy',
            'authorize_signature_key': '00000000',
            'state': 'test',
        })
        # Be sure to be in 'capture' mode
        # self.authorize.auto_confirm = 'confirm_so'


@odoo.tests.tagged('post_install', '-at_install', '-standard', 'external')
class AuthorizeForm(AuthorizeCommon):

    def test_10_Authorize_form_render(self):
        self.assertEqual(self.authorize.state, 'test', 'test without test environment')

        # ----------------------------------------
        # Test: button direct rendering
        # ----------------------------------------
        base_url = self.env['ir.config_parameter'].get_param('web.base.url')
        form_values = {
            'x_login': self.authorize.authorize_login,
            'x_amount': '56.16',
            'x_show_form': 'PAYMENT_FORM',
            'x_type': 'AUTH_CAPTURE',
            'x_method': 'CC',
            'x_fp_sequence': '%s%s' % (self.authorize.id, int(time.time())),
            'x_version': '3.1',
            'x_relay_response': 'TRUE',
            'x_fp_timestamp': str(int(time.time())),
            'x_relay_url': urls.url_join(base_url, AuthorizeController._return_url),
            'x_cancel_url': urls.url_join(base_url, AuthorizeController._cancel_url),
            'return_url': None,
            'x_currency_code': 'USD',
            'x_invoice_num': 'SO004',
            'x_first_name': 'Norbert',
            'x_last_name': 'Buyer',
            'x_company': 'Big Company',
            'x_address': 'Huge Street 2/543',
            'x_city': 'Sin City',
            'x_zip': '1000',
            'x_country': 'Belgium',
            'x_phone': '0032 12 34 56 78',
            'x_email': 'norbert.buyer@example.com',
            'x_state': None,
            'x_ship_to_first_name': 'Norbert',
            'x_ship_to_last_name': 'Buyer',
            'x_ship_to_address': 'Huge Street 2/543',
            'x_ship_to_city': 'Sin City',
            'x_ship_to_zip': '1000',
            'x_ship_to_country': 'Belgium',
            'x_ship_to_phone': '0032 12 34 56 78',
            'x_ship_to_email': 'norbert.buyer@example.com',
            'x_ship_to_state': None,
        }

        form_values['x_fp_hash'] = self.authorize._authorize_generate_hashing(form_values)
        # render the button
        res = self.authorize.render('SO004', 56.16, self.currency_usd.id, values=self.buyer_values)
        # check form result
        tree = objectify.fromstring(res)

        data_set = tree.xpath("//input[@name='data_set']")
        self.assertEqual(len(data_set), 1, 'Authorize: Found %d "data_set" input instead of 1' % len(data_set))
        self.assertEqual(data_set[0].get('data-action-url'), 'https://test.authorize.net/gateway/transact.dll', 'Authorize: wrong data-action-url POST url')
        for el in tree.iterfind('input'):
            values = list(el.attrib.values())
            if values[1] in ['submit', 'x_fp_hash', 'return_url', 'x_state', 'x_ship_to_state', 'data_set']:
                continue
            self.assertEqual(
                values[2],
                form_values[values[1]],
                'Authorize: wrong value for input %s: received %s instead of %s' % (values[1], values[2], form_values[values[1]])
            )

    @mute_logger('odoo.addons.payment_authorize.models.payment', 'ValidationError')
    def test_20_authorize_form_management(self):
        # be sure not to do stupid thing
        self.assertEqual(self.authorize.state, 'test', 'test without test environment')

        # typical data posted by authorize after client has successfully paid
        authorize_post_data = {
            'return_url': u'/shop/payment/validate',
            # x_MD5_Hash will be empty starting the 28th March 2019
            'x_MD5_Hash': u'7934485E1C105940BE854208D10FAB4F',
            'x_SHA2_Hash': u'7D3AC844BE8CA3F649AB885A90D22CFE35B850338EC91D1A5ADD819A85FF948A3D777334A18CDE36821DC8F2B42A6E1950C1FF96B52B60F23201483A656195FB',
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
            'x_email': u'norbert.buyer@example.com',
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
            self.env['payment.transaction'].form_feedback(authorize_post_data, 'authorize')

        tx = self.env['payment.transaction'].create({
            'amount': 320.0,
            'acquirer_id': self.authorize.id,
            'currency_id': self.currency_usd.id,
            'reference': 'SO004',
            'partner_name': 'Norbert Buyer',
            'partner_country_id': self.country_france.id})

        # validate it
        self.env['payment.transaction'].form_feedback(authorize_post_data, 'authorize')
        # check state
        self.assertEqual(tx.state, 'done', 'Authorize: validation did not put tx into done state')
        self.assertEqual(tx.acquirer_reference, authorize_post_data.get('x_trans_id'), 'Authorize: validation did not update tx payid')

        tx = self.env['payment.transaction'].create({
            'amount': 320.0,
            'acquirer_id': self.authorize.id,
            'currency_id': self.currency_usd.id,
            'reference': 'SO004-2',
            'partner_name': 'Norbert Buyer',
            'partner_country_id': self.country_france.id})

        # simulate an error
        authorize_post_data['x_response_code'] = u'3'
        self.env['payment.transaction'].form_feedback(authorize_post_data, 'authorize')
        # check state
        self.assertNotEqual(tx.state, 'done', 'Authorize: erroneous validation did put tx into done state')


@odoo.tests.tagged('post_install', '-at_install', '-standard')
class AuthorizeS2s(AuthorizeCommon):
    def test_30_authorize_s2s(self):
        # be sure not to do stupid thing
        authorize = self.authorize
        self.assertEqual(authorize.state, 'test', 'test without test environment')

        # add credential
        # FIXME: put this test in master-nightly on odoo/odoo + create sandbox account
        authorize.write({
            'authorize_transaction_key': '',
            'authorize_login': '',
        })
        self.assertTrue(authorize.authorize_test_credentials, 'Authorize.net: s2s authentication failed')

        # create payment meethod
        payment_token = self.env['payment.token'].create({
            'acquirer_id': authorize.id,
            'partner_id': self.buyer_id,
            'opaqueData': {
                'dataDescriptor': 'COMMON.ACCEPT.INAPP.PAYMENT',
                'dataValue': '9487801666614876704604'
            },
        })

        # create normal s2s transaction
        transaction = self.env['payment.transaction'].create({
            'amount': 500,
            'acquirer_id': authorize.id,
            'type': 'server2server',
            'currency_id': self.currency_usd.id,
            'reference': 'test_ref_%s' % int(time.time()),
            'payment_token_id': payment_token.id,
            'partner_id': self.buyer_id,

        })
        transaction.authorize_s2s_do_transaction()
        self.assertEqual(transaction.state, 'done',)

        # switch to 'authorize only'
        # create authorize only s2s transaction & capture it
        self.authorize.capture_manually = True
        transaction = self.env['payment.transaction'].create({
            'amount': 500,
            'acquirer_id': authorize.id,
            'type': 'server2server',
            'currency_id': self.currency_usd.id,
            'reference': 'test_%s' % int(time.time()),
            'payment_token_id': payment_token.id,
            'partner_id': self.buyer_id,

        })
        transaction.authorize_s2s_do_transaction()
        self.assertEqual(transaction.state, 'authorized')
        transaction.action_capture()
        self.assertEqual(transaction.state, 'done')

        # create authorize only s2s transaction & void it
        self.authorize.capture_manually = True
        transaction = self.env['payment.transaction'].create({
            'amount': 500,
            'acquirer_id': authorize.id,
            'type': 'server2server',
            'currency_id': self.currency_usd.id,
            'reference': 'test_%s' % int(time.time()),
            'payment_token_id': payment_token.id,
            'partner_id': self.buyer_id,

        })
        transaction.authorize_s2s_do_transaction()
        self.assertEqual(transaction.state, 'authorized')
        transaction.action_void()
        self.assertEqual(transaction.state, 'cancel')

        # try charging an unexisting profile
        ghost_payment_token = payment_token.copy()
        ghost_payment_token.authorize_profile = '99999999999'
        # create normal s2s transaction
        transaction = self.env['payment.transaction'].create({
            'amount': 500,
            'acquirer_id': authorize.id,
            'type': 'server2server',
            'currency_id': self.currency_usd.id,
            'reference': 'test_ref_%s' % int(time.time()),
            'payment_token_id': ghost_payment_token.id,
            'partner_id': self.buyer_id,

        })
        transaction.authorize_s2s_do_transaction()
        self.assertEqual(transaction.state, 'cancel')
