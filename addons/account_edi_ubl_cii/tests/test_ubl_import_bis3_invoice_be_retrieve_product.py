from odoo.addons.account_edi_ubl_cii.tests.test_ubl_import_bis3_invoice_be import TestUblImportBis3InvoiceBE
from odoo.tests import tagged

from freezegun import freeze_time


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestUblImportBis3InvoiceBERetrieveProduct(TestUblImportBis3InvoiceBE):

    _test_groups = None  # FIXME list needed groups

    def test_partial_import_product_description(self):
        self._create_product(name='XYZ')
        invoice = self._import_invoice_as_attachment_on(test_name='test_partial_import_product_description')

        # Not enough information to retrieve the product.
        self.assertRecordValues(invoice.invoice_line_ids, [{
            'name': '[1234] XYZ',
            'product_id': None,
        }])

    def test_partial_import_product_name(self):
        product = self._create_product(name='important product1')
        invoice = self._import_invoice_as_attachment_on(test_name='test_partial_import_product_name')
        self.assertRecordValues(invoice.invoice_line_ids, [
            {
                'name': 'important product',
                'product_id': product.id,
            },
            {
                'name': 'XYZ',
                'product_id': None,
            },
        ])

    def test_partial_import_product_barcode(self):
        product = self._create_product(name='XYZ', barcode='12345678912345')
        invoice = self._import_invoice_as_attachment_on(test_name='test_partial_import_product_barcode')
        self.assertRecordValues(invoice.invoice_line_ids, [{
            'name': 'XYZ',
            'product_id': product.id,
        }])

    def test_partial_import_product_default_code(self):
        product = self._create_product(name='XYZ', default_code='abcdefghij')
        invoice = self._import_invoice_as_attachment_on(test_name='test_partial_import_product_default_code')
        self.assertRecordValues(invoice.invoice_line_ids, [{
            'name': '[abcdefghij] XYZ',
            'product_id': product.id,
        }])

    def test_import_ignored_uom_category_mismatch(self):
        # If the XML UoM category does not match the matched product's UoM
        # category, the product is still matched but the UoM is left empty.
        product = self._create_product(name='XYZ', uom_id=self.env.ref('uom.product_uom_unit').id)
        invoice = self._import_invoice_as_attachment_on(test_name='test_partial_import_product_uom_category_mismatch')
        self.assertRecordValues(invoice.invoice_line_ids, [{
            'name': 'XYZ',
            'product_id': product.id,
            'product_uom_id': False,
        }])

    @freeze_time('2020-01-01')
    def test_partial_import_product_invoice_predictive(self):
        self.ensure_installed('account_accountant')

        # First invoice to train the prediction.
        product = self._create_product(name='XYZ')
        self._create_invoice_one_line(
            name="turlututu",
            product_id=product,
            partner_id=self.partner_be,
            post=True,
        )

        # Check the prediction.
        invoice = self._import_invoice_as_attachment_on(
            test_name='test_partial_import_product_invoice_predictive',
            journal=self.company_data['default_journal_sale'],
        )
        self.assertRecordValues(invoice, [{'partner_id': self.partner_be.id}])
        self.assertRecordValues(invoice.invoice_line_ids, [{
            'name': "turlutututu",
            'product_id': product.id,
        }])
