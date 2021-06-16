# Part of Odoo. See LICENSE file for full copyright and licensing details.

from freezegun import freeze_time

from odoo.fields import Command
from odoo.tests import tagged
from odoo.tools import mute_logger

from odoo.addons.payment import utils as payment_utils

from .common import OgoneCommon
from ..controllers.main import OgoneController


@tagged('post_install', '-at_install')
class OgoneTest(OgoneCommon):

    def test_validation_amount(self):
        """ Test the value of the validation amount. """
        self.assertEqual(self.ogone._get_validation_amount(), 1.0)

    @freeze_time('2011-11-02 12:00:21')  # Freeze time for consistent singularization behavior
    def test_reference_is_singularized(self):
        """ Test singularization of reference prefixes. """
        reference = self.env['payment.transaction']._compute_reference(self.ogone.provider)
        self.assertEqual(
            reference, 'tx-20111102120021', "transaction reference was not correctly singularized"
        )

    @freeze_time('2011-11-02 12:00:21')  # Freeze time for consistent singularization behavior
    def test_reference_is_stripped_at_max_length(self):
        """ Test stripping of reference prefixes of length > 40 chars. """
        reference = self.env['payment.transaction']._compute_reference(
            self.ogone.provider,
            prefix='this is a reference of more than 40 characters to annoy ogone',
        )
        self.assertEqual(reference, 'this is a reference of mo-20111102120021')
        self.assertEqual(len(reference), 40)

    @freeze_time('2011-11-02 12:00:21')  # Freeze time for consistent singularization behavior
    def test_reference_is_computed_based_on_document_name(self):
        """ Test computation of reference prefixes based on the provided invoice. """
        invoice = self.env['account.move'].create({})
        reference = self.env['payment.transaction']._compute_reference(
            self.ogone.provider, invoice_ids=[Command.set([invoice.id])]
        )
        self.assertEqual(reference, 'MISC/2011/11/0001-20111102120021')

    @freeze_time('2011-11-02 12:00:21')  # Freeze time for consistent singularization behavior
    def test_redirect_form_values(self):
        """ Test the values of the redirect form inputs. """
        return_url = self._build_url(OgoneController._flexcheckout_return_url)
        expected_values = {
            'ACCOUNT_PSPID': self.ogone.ogone_pspid,
            'ALIAS_ALIASID': payment_utils.singularize_reference_prefix(prefix='ODOO-ALIAS'),
            'ALIAS_ORDERID': self.reference,
            'ALIAS_STOREPERMANENTLY': 'N',  # 'Y' if self.tokenize
            'CARD_PAYMENTMETHOD': 'CreditCard',
            'LAYOUT_LANGUAGE': self.partner.lang,
            'PARAMETERS_ACCEPTURL': return_url,
            'PARAMETERS_EXCEPTIONURL': return_url,
        }
        expected_values['SHASIGNATURE_SHASIGN'] = self.ogone._ogone_generate_signature(
            expected_values, incoming=False, format_keys=True
        ).upper()

        tx = self.create_transaction(flow='redirect')
        with mute_logger('odoo.addons.payment.models.payment_transaction'):
            processing_values = tx._get_processing_values()

        form_info = self._extract_values_from_html_form(processing_values['redirect_form_html'])

        self.assertEqual(form_info['action'], 'https://ogone.test.v-psp.com/Tokenization/HostedPage')
        inputs = form_info['inputs']
        self.assertEqual(len(expected_values), len(inputs))
        for rendering_key, value in expected_values.items():
            form_key = rendering_key.replace('_', '.')
            self.assertEqual(
                inputs[form_key],
                value,
                f"received value {inputs[form_key]} for input {form_key} (expected {value})"
            )
