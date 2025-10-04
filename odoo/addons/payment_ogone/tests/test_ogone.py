# Part of Odoo. See LICENSE file for full copyright and licensing details.

from unittest.mock import patch

from freezegun import freeze_time
from werkzeug.exceptions import Forbidden

from odoo.fields import Command
from odoo.tests import tagged
from odoo.tools import mute_logger

from odoo.addons.payment import utils as payment_utils
from odoo.addons.payment.tests.http_common import PaymentHttpCommon
from odoo.addons.payment_ogone.controllers.main import OgoneController
from odoo.addons.payment_ogone.tests.common import OgoneCommon


@tagged('post_install', '-at_install')
class OgoneTest(OgoneCommon, PaymentHttpCommon):

    def test_incompatibility_with_validation_operation(self):
        providers = self.env['payment.provider']._get_compatible_providers(
            self.company.id, self.partner.id, 0., is_validation=True
        )
        self.assertNotIn(self.ogone, providers)

    @freeze_time('2011-11-02 12:00:21')  # Freeze time for consistent singularization behavior
    def test_reference_is_singularized(self):
        """ Test singularization of reference prefixes. """
        reference = self.env['payment.transaction']._compute_reference(self.ogone.code)
        self.assertEqual(
            reference, 'tx-20111102120021', "transaction reference was not correctly singularized"
        )

    @freeze_time('2011-11-02 12:00:21')  # Freeze time for consistent singularization behavior
    def test_reference_is_stripped_at_max_length(self):
        """ Test stripping of reference prefixes of length > 40 chars. """
        reference = self.env['payment.transaction']._compute_reference(
            self.ogone.code,
            prefix='this is a reference of more than 40 characters to annoy ogone',
        )
        self.assertEqual(reference, 'this is a reference of mo-20111102120021')
        self.assertEqual(len(reference), 40)

    @freeze_time('2011-11-02 12:00:21')  # Freeze time for consistent singularization behavior
    def test_reference_is_computed_based_on_document_name(self):
        """ Test computation of reference prefixes based on the provided invoice. """
        self._skip_if_account_payment_is_not_installed()

        invoice = self.env['account.move'].create({})
        reference = self.env['payment.transaction']._compute_reference(
            self.ogone.code, invoice_ids=[Command.set([invoice.id])]
        )
        self.assertEqual(reference, 'MISC/2011/11/0001-20111102120021')

    @freeze_time('2011-11-02 12:00:21')  # Freeze time for consistent singularization behavior
    def test_redirect_form_values(self):
        """ Test the values of the redirect form inputs for online payments. """
        return_url = self._build_url(OgoneController._return_url)
        expected_values = {
            'PSPID': self.ogone.ogone_pspid,
            'ORDERID': self.reference,
            'AMOUNT': str(payment_utils.to_minor_currency_units(self.amount, None, 2)),
            'CURRENCY': self.currency.name,
            'LANGUAGE': self.partner.lang,
            'EMAIL': self.partner.email,
            'CN': self.partner.name,
            'OWNERZIP': self.partner.zip,
            'OWNERADDRESS': payment_utils.format_partner_address(
                self.partner.street, self.partner.street2
            ),
            'OWNERCTY': self.partner.country_id.code,
            'OWNERTOWN': self.partner.city,
            'OWNERTELNO': self.partner.phone,
            'OPERATION': 'SAL',  # direct sale
            'USERID': self.ogone.ogone_userid,
            'ACCEPTURL': return_url,
            'DECLINEURL': return_url,
            'EXCEPTIONURL': return_url,
            'CANCELURL': return_url,
            'ALIAS': None,
            'ALIASUSAGE': None,
            'PM': self.payment_method_code,
        }
        expected_values['SHASIGN'] = self.ogone._ogone_generate_signature(
            expected_values, incoming=False
        ).upper()

        tx = self._create_transaction(flow='redirect')
        self.assertEqual(tx.tokenize, False)
        with mute_logger('odoo.addons.payment.models.payment_transaction'):
            processing_values = tx._get_processing_values()

        form_info = self._extract_values_from_html_form(processing_values['redirect_form_html'])

        self.assertEqual(form_info['action'], 'https://ogone.test.v-psp.com/ncol/test/orderstandard_utf8.asp')
        inputs = form_info['inputs']
        self.assertEqual(len(expected_values), len(inputs))
        for rendering_key, value in expected_values.items():
            form_key = rendering_key.replace('_', '.')
            self.assertEqual(
                inputs[form_key],
                value,
                f"received value {inputs[form_key]} for input {form_key} (expected {value})"
            )

    @mute_logger('odoo.addons.payment_ogone.controllers.main')
    def test_webhook_notification_confirms_transaction(self):
        """ Test the processing of a webhook notification. """
        tx = self._create_transaction('redirect')
        url = self._build_url(OgoneController._return_url)
        with patch(
            'odoo.addons.payment_ogone.controllers.main.OgoneController'
            '._verify_notification_signature'
        ):
            self._make_http_post_request(url, data=self.notification_data)
        self.assertEqual(tx.state, 'done')

    @mute_logger('odoo.addons.payment_ogone.controllers.main')
    def test_webhook_notification_triggers_signature_check(self):
        """ Test that receiving a webhook notification triggers a signature check. """
        self._create_transaction('redirect')
        url = self._build_url(OgoneController._return_url)
        with patch(
            'odoo.addons.payment_ogone.controllers.main.OgoneController'
            '._verify_notification_signature'
        ) as signature_check_mock, patch(
            'odoo.addons.payment.models.payment_transaction.PaymentTransaction'
            '._handle_notification_data'
        ):
            self._make_http_post_request(url, data=self.notification_data)
            self.assertEqual(signature_check_mock.call_count, 1)

    def test_accept_notification_with_valid_signature(self):
        """ Test the verification of a notification with a valid signature. """
        tx = self._create_transaction('redirect')
        self._assert_does_not_raise(
            Forbidden,
            OgoneController._verify_notification_signature,
            self.notification_data,
            self.notification_data['SHASIGN'],
            tx,
        )

    @mute_logger('odoo.addons.payment_ogone.controllers.main')
    def test_reject_notification_with_missing_signature(self):
        """ Test the verification of a notification with a missing signature. """
        tx = self._create_transaction('redirect')
        self.assertRaises(
            Forbidden,
            OgoneController._verify_notification_signature,
            self.notification_data,
            None,
            tx,
        )

    @mute_logger('odoo.addons.payment_ogone.controllers.main')
    def test_reject_notification_with_invalid_signature(self):
        """ Test the verification of a notification with an invalid signature. """
        tx = self._create_transaction('redirect')
        self.assertRaises(
            Forbidden,
            OgoneController._verify_notification_signature,
            self.notification_data,
            'dummy',
            tx,
        )
