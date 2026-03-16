from odoo.addons.account_edi_ubl_cii.tests.test_ubl_import_bis3_invoice_be import TestUblImportBis3InvoiceBE
from odoo.tests import tagged

from freezegun import freeze_time


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestUblImportBis3InvoiceBERetrieveAccount(TestUblImportBis3InvoiceBE):

    @freeze_time('2020-01-01')
    def test_partial_import_account_invoice_predictive(self):
        self.ensure_installed('account_accountant')

        account = self.company_data['default_account_revenue'].copy()

        # First invoice to train the prediction.
        self._create_invoice_one_line(
            name="turlututu",
            price_unit=1.0,
            account_id=account.id,
            partner_id=self.partner_be,
            post=True,
        )

        # Check the prediction.
        invoice = self._import_invoice_as_attachment_on(
            test_name='test_partial_import_account_invoice_predictive',
            journal=self.company_data['default_journal_sale'],
        )
        self.assertRecordValues(invoice, [{'partner_id': self.partner_be.id}])
        self.assertRecordValues(invoice.invoice_line_ids, [{
            'name': "turlutututu",
            'account_id': account.id,
        }])
