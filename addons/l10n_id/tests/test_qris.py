from markupsafe import Markup

from odoo.fields import Command
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests import tagged
from unittest.mock import patch
from freezegun import freeze_time


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestQris(AccountTestInvoicingCommon):
    """ Test QRIS QR generation on invoices and auto-payment registration"""

    @classmethod
    @AccountTestInvoicingCommon.setup_chart_template('id')
    def setUpClass(cls):
        super().setUpClass()
        cls.company_data['company'].qr_code = True
        cls.company_data['company'].partner_id.update({
            'country_id': cls.env.ref('base.id').id,
            'city': 'Jakarta',
        })

        cls.acc_qris_id = cls.env['res.partner.bank'].create({
            'acc_number': '123456789012345678',
            'partner_id': cls.company_data['company'].partner_id.id,
            'l10n_id_qris_api_key': 'apikey',
            'l10n_id_qris_mid': 'mid',
        })

        cls.qris_qr_invoice = cls.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': cls.partner_a.id,
            'currency_id': cls.env.ref('base.IDR').id,
            'partner_bank_id': cls.acc_qris_id.id,
            'company_id': cls.company_data['company'].id,
            'invoice_line_ids': [Command.create({'quantity': 1, 'price_unit': 100})],
            'qr_code_method': 'id_qr',
        })._post()

        cls.success_qris_get = {
            "status": "success",
            "data": {
                "qris_content": "Test Content",
                "qris_request_date": "2024-02-27 11:13:42",
                "qris_invoiceid": "413255111",
                "qris_nmid": "ID1020021181745"
            }
        }
        cls.success_qris_get_second = {
            "status": "success",
            "data": {
                "qris_content": "Test Content Second",
                "qris_request_date": "2024-02-27 11:13:42",
                "qris_invoiceid": "413255111",
                "qris_nmid": "ID1020021181745"
            }
        }

        cls.qris_status_fail = {
            "status": "failed",
            "data": {
                "qris_status": "unpaid"
            }
        }

        cls.qris_status_success = {
            "status": "success",
            "data": {
                "qris_status": "paid",
                "qris_payment_customername": "Zainal Arief",
                "qris_payment_methodby": "Sakuku"
            },
            "qris_api_version_code": "2206091709"
        }

    @freeze_time("2024-02-27 04:15:00")
    def test_qris_qr_code_generation(self):
        """ QR-Code generation conditions:

        - should only come from portal side
        - only call the API when the QRIS transaction not found or lasted for > 30 minutes
        - if transaction found and < 30 minutes, no API call needed
        """

        with patch(
            'odoo.addons.l10n_id.models.res_bank._l10n_id_make_qris_request', return_value=self.success_qris_get
        ) as patched:
            # QR code shouldn't be generated without the context.
            result = self.qris_qr_invoice._generate_qr_code()
            self.assertIsNone(result)

            # But of course, should be with it.
            result = self.qris_qr_invoice.with_context({'is_online_qr': True})._generate_qr_code()
            self.assertIsNotNone(result)

            # Confirm that the QR was successfully registered on the invoice.
            qr_details = self.qris_qr_invoice.l10n_id_qris_invoice_details
            self.assertNotEqual(qr_details, False)

            qris_data = self.success_qris_get['data']
            self.assertEqual(qr_details[-1]['qris_invoice_id'], qris_data['qris_invoiceid'])
            self.assertEqual(qr_details[-1]['qris_content'], qris_data['qris_content'])
            patched.assert_called_once()

        with patch(
                'odoo.addons.l10n_id.models.res_bank._l10n_id_make_qris_request', return_value=self.success_qris_get
        ) as patched:
            # Check the API is not called again, as it should reuse the existing QR until it is expired
            self.qris_qr_invoice.with_context({'is_online_qr': True})._generate_qr_code()
            patched.assert_not_called()

            # Check that if the qr code has expired, we correctly generate a new one.
            qr_details[0]['qris_creation_datetime'] = '2024-02-27 03:00:00'
            self.qris_qr_invoice.l10n_id_qris_invoice_details = qr_details
            self.qris_qr_invoice.with_context({'is_online_qr': True})._generate_qr_code()
            patched.assert_called_once()

        with patch(
            'odoo.addons.l10n_id.models.res_bank._l10n_id_make_qris_request', return_value=self.success_qris_get_second
        ):
            qr_details = self.qris_qr_invoice.l10n_id_qris_invoice_details
            qr_details[-1]['qris_creation_datetime'] = '2024-02-27 03:00:00'
            self.qris_qr_invoice.l10n_id_qris_invoice_details = qr_details
            self.qris_qr_invoice.with_context({'is_online_qr': True})._generate_qr_code()

            # Ensure that the l10n_id_latest_qris_content is the new one, while the l10n_id_qris_invoice_details contains all three QR data
            qr_details = self.qris_qr_invoice.l10n_id_qris_invoice_details
            qris_data = self.success_qris_get_second['data']
            self.assertEqual(qr_details[-1]['qris_invoice_id'], qris_data['qris_invoiceid'])
            self.assertEqual(qr_details[-1]['qris_content'], qris_data['qris_content'])

            self.assertEqual(len(qr_details), 3)

    @freeze_time("2024-02-27 04:15:00")
    def test_fetch_payment_status_fail(self):
        """ If API return unpaid status """

        with patch(
            'odoo.addons.l10n_id.models.res_bank._l10n_id_make_qris_request', return_value=self.success_qris_get
        ):
            self.qris_qr_invoice.with_context({'is_online_qr': True})._generate_qr_code()

        with patch(
            'odoo.addons.l10n_id.models.res_bank._l10n_id_make_qris_request', return_value=self.qris_status_fail
        ):
            self.qris_qr_invoice.action_l10n_id_update_payment_status()
            self.assertEqual(self.qris_qr_invoice.payment_state, 'not_paid')

    @freeze_time("2024-02-27 04:15:00")
    def test_fetch_payment_status_success(self):
        """ If API returns 'paid' status """

        with patch(
            'odoo.addons.l10n_id.models.res_bank._l10n_id_make_qris_request', return_value=self.success_qris_get
        ):
            self.qris_qr_invoice.with_context({'is_online_qr': True})._generate_qr_code()

        with patch(
            'odoo.addons.l10n_id.models.res_bank._l10n_id_make_qris_request', return_value=self.qris_status_success
        ):
            self.qris_qr_invoice.action_l10n_id_update_payment_status()
            self.assertEqual(self.qris_qr_invoice.payment_state, self.env['account.move']._get_invoice_in_payment_state())
            # Ensure that the message is logged as expected.
            self.assertEqual(
                self.qris_qr_invoice.message_ids[0].body,
                Markup('<p>This invoice was paid by Zainal Arief using QRIS with the payment method Sakuku.</p>')
            )

    @freeze_time("2024-02-27 04:15:00")
    def test_cron_removes_outdated_transactions(self):
        """ Everytime CRON runs, should do cleanup transactions to remove paid transactions and
        transactions that have been around for more than 30 minutes """

        with patch(
            'odoo.addons.l10n_id.models.res_bank._l10n_id_make_qris_request', return_value=self.success_qris_get
        ):
            self.qris_qr_invoice.with_context({'is_online_qr': True})._generate_qr_code()
            qr_details = self.qris_qr_invoice.l10n_id_qris_invoice_details
            qr_details[-1]['qris_creation_datetime'] = '2024-02-27 03:00:00'
            self.qris_qr_invoice.l10n_id_qris_invoice_details = qr_details

            self.qris_qr_invoice.with_context({'is_online_qr': True})._generate_qr_code()

        # There should be two transactions, one recent and one outdated
        self.assertEqual(len(self.qris_qr_invoice.l10n_id_qris_invoice_details), 2)
        with patch(
            'odoo.addons.l10n_id.models.res_bank._l10n_id_make_qris_request', return_value=self.qris_status_fail
        ):
            # After updating the status, the outdated one is removed as it cannot be paid anymore.
            self.qris_qr_invoice.action_l10n_id_update_payment_status()
            self.assertEqual(len(self.qris_qr_invoice.l10n_id_qris_invoice_details), 1)

        with patch(
            'odoo.addons.l10n_id.models.res_bank._l10n_id_make_qris_request', return_value=self.qris_status_success
        ):
            # On the other hand, the most recent one is still there, and is only removed if it becomes outdated or in this case, is paid.
            self.qris_qr_invoice.action_l10n_id_update_payment_status()
            self.assertFalse(self.qris_qr_invoice.l10n_id_qris_invoice_details)
            self.assertEqual(self.qris_qr_invoice.payment_state, self.env['account.move']._get_invoice_in_payment_state())
