from odoo.addons.account_edi_ubl_cii.tests.test_ubl_import_bis3_invoice_be import TestUblImportBis3InvoiceBE
from odoo.tests import tagged

from freezegun import freeze_time


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestUblImportBis3InvoiceBERetrieveAccount(TestUblImportBis3InvoiceBE):

    @freeze_time('2020-01-01')
    def test_partial_import_account_invoice_predictive(self):
        self.ensure_installed('account_accountant')

        account = self.company_data['default_account_revenue'].copy(default={'name': "turlututu"})
        product = self._create_product(name='turlututu', barcode='12345678912345')

        # Invoice to train the prediction.
        # We also make an exact match with the name to ensure the prediction will
        # also retrieve the product.
        self._create_invoice_one_line(
            name="turlutututu",
            product_id=product,
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
            'product_id': product.id,
        }])

    @freeze_time('2020-01-01')
    def test_partial_import_account_invoice_predictive_exempt(self):
        """ Lines without taxes are exported with the 'E' category (see _get_tax_category_code),
        so importing such a line should predict from history lines without taxes as well.
        """
        self.ensure_installed('account_accountant')

        account = self.company_data['default_account_revenue'].copy(default={'name': "turlututu"})
        # Put it in the partner's fiscal position, so it competes with the other 0% taxes of it.
        fiscal_position = self.env['account.fiscal.position']._get_fiscal_position(self.partner_be)
        exempt_tax = self.percent_tax(0.0, ubl_cii_tax_category_code='E', fiscal_position_ids=fiscal_position.ids)

        # Invoice to train the prediction, without any tax.
        training_invoice = self._create_invoice_one_line(
            name="turlututu",
            price_unit=500.0,
            account_id=account.id,
            tax_ids=[],
            partner_id=self.partner_be,
            post=True,
        )
        self.assertFalse(training_invoice.line_ids.tax_ids)

        # Check the prediction.
        invoice = self._import_invoice_as_attachment_on(
            test_name='test_partial_import_account_invoice_predictive_exempt',
            journal=self.company_data['default_journal_sale'],
        )
        self.assertRecordValues(invoice, [{'partner_id': self.partner_be.id}])
        self.assertRecordValues(invoice.invoice_line_ids, [{
            'name': "turlututu",
            'account_id': account.id,
        }])
        self.assertEqual(invoice.line_ids.tax_ids, exempt_tax)
