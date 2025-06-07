
from odoo.fields import Command
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests import tagged
from unittest.mock import patch


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestQrisTransaction(AccountTestInvoicingCommon):
    """ Testing the behaviours of QRIS Transaction """

    @classmethod
    @AccountTestInvoicingCommon.setup_chart_template('id')
    def setUpClass(cls):
        super().setUpClass()
        cls.invoice = cls.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': cls.partner_a.id,
            'invoice_date': '2019-05-01',
            'date': '2019-05-01',
            'invoice_line_ids': [
                Command.create({'name': 'line1', 'price_unit': 110.0}),
            ],
        })
        cls.qris_status_success = {
            "status": "success",
            "data": {
                "qris_status": "paid",
                "qris_payment_customername": "Zainal Arief",
                "qris_payment_methodby": "Sakuku"
            },
            "qris_api_version_code": "2206091709"
        }
        cls.qris_status_fail = {
            "status": "failed",
            "data": {
                "qris_status": "unpaid"
            }
        }

        cls.acc_qris_id = cls.env['res.partner.bank'].create({
            'acc_number': '123456789012345678',
            'partner_id': cls.company_data['company'].partner_id.id,
            'l10n_id_qris_api_key': 'apikey',
            'l10n_id_qris_mid': 'mid',
        })

    # Utility method to help create QRIS transactions
    def _create_sample_transaction(self, model, model_id, qris_id, amount, create_at, content):
        return self.env['l10n_id.qris.transaction'].create({
            'model': model,
            'model_id': model_id,
            'qris_invoice_id': qris_id,
            'qris_amount': amount,
            'qris_creation_datetime': create_at,
            'qris_content': content,
        })

    def test_retrieve_backend_record(self):
        """ Test the _get_record method to retrieve original record accordingly """
        trx = self._create_sample_transaction(
            "account.move", str(self.invoice.id), "11254", 11000, "2024-08-01", "qris_content_sample"
        )
        invoice = trx._get_record()
        self.assertEqual(invoice, self.invoice)

    def test_latest_transaction(self):
        """ Test method _get_latest_transaction"""
        self._create_sample_transaction(
            "account.move", "1", "11254", 11000, "2024-08-01 03:00:00", "qris_content_sample"
        )
        self._create_sample_transaction(
            "account.move", "1", "11254", 11000, "2024-08-01 03:00:15", "qris_content_sample_latest"
        )

        trx = self.env['l10n_id.qris.transaction']._get_latest_transaction('account.move', '1')
        self.assertTrue(
            trx['qris_amount'] == 11000 and trx['qris_content'] == "qris_content_sample_latest"
        )

    def test_l10n_id_get_qris_qr_statuses(self):
        """ Test the method _l10n_id_get_qris_qr_statuses """

        # Create QRIS transaction with 2 entries in invoice details
        trx = self._create_sample_transaction(
            "account.move", "1", "11253", 11000, "2024-08-01", "qris_content_sample"
        )
        trx |= self._create_sample_transaction(
            "account.move", "1", "11254", 11000, "2024-08-01", "qris_content_sample"
        )

        # if QRIS returns success, _l10n_id_make_request should only be called once and
        # status returned is {'paid': True, 'qr_statuses': [{self.qris_status_success}]}
        # and check that the transaction is also paid
        with patch(
            'odoo.addons.l10n_id.models.res_bank._l10n_id_make_qris_request', return_value=self.qris_status_success
        ) as patched:
            res = trx._l10n_id_get_qris_qr_statuses()
            patched.assert_called_once()
            self.assertEqual(len(res['qr_statuses']), 1)
            success_response = res['qr_statuses'][0]
            self.assertTrue(res['paid'] and success_response['qris_payment_customername'] == 'Zainal Arief' and trx[0].paid)

        # if QRIS returns fail for all, _l10n_id_make-request should be called twice and
        # status returned is {'paid': False, 'qr_statuses': [{self.qris_status}, {self.qris_status_fail}]}
        with patch(
            'odoo.addons.l10n_id.models.res_bank._l10n_id_make_qris_request', return_value=self.qris_status_fail
        ) as patched:
            res = trx._l10n_id_get_qris_qr_statuses()
            self.assertEqual(patched.call_count, 2)
            self.assertEqual(len(res['qr_statuses']), 2)
