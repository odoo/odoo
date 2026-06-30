from odoo.addons.account_edi_ubl_cii.tests.test_ubl_import_bis3_invoice_be import TestUblImportBis3InvoiceBE
from odoo.tests import tagged

from freezegun import freeze_time


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestUblImportBis3InvoiceBERetrieveProduct(TestUblImportBis3InvoiceBE):

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
        self.env.company.predict_bill_product = True

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

    def test_import_product_by_supplier_info(self):
        """Product has no barcode/default_code but is matched via product.supplierinfo Vendor Product Code."""

        product = self.env['product.product'].create({
            'name': 'Test Product',
        })
        partner = self.env['res.partner'].create({
            'name': 'Test Vendor',
            'vat': 'BE0202239951',
        })
        self.env['product.supplierinfo'].create({
            'partner_id': partner.commercial_partner_id.id,
            'product_tmpl_id': product.product_tmpl_id.id,
            'product_code': 'VENDOR-PRODUCT-001',
        })

        _fn, xml_content = self._import_file_content('test_import_product_by_supplier_info', 'xml')
        xml_attachment = self.env['ir.attachment'].create({
            'raw': xml_content,
            'name': 'test_import_product_by_supplier_info.xml',
        })
        imported_invoice = self._import_invoice_as_attachment_on(
            attachment=xml_attachment,
            journal=self.company_data['default_journal_purchase'],
        )
        self.assertEqual(imported_invoice.invoice_line_ids.product_id, product)

    def test_import_product_by_supplier_info_as_first_preference(self):
        """
        Product A matches by supplier info, Product B matches by barcode.
        Product A should win because supplier info has higher priority in the search plan.
        """
        partner = self.env['res.partner'].create({
            'name': 'Test Vendor',
            'vat': 'BE0202239951',
        })
        self.env['product.supplierinfo'].create({
            'partner_id': partner.commercial_partner_id.id,
            'product_tmpl_id': self.product_a.product_tmpl_id.id,
            'product_code': 'VENDOR-PRODUCT-002',
        })
        _product_b = self.env['product.product'].create({
            'name': 'Product B',
            'barcode': '1234567890128',  # matches StandardItemIdentification in XML
        })

        _fn, xml_content = self._import_file_content('test_import_product_by_supplier_info_as_first_preference', 'xml')
        xml_attachment = self.env['ir.attachment'].create({
            'raw': xml_content,
            'name': 'test_import_product_by_supplier_info_as_first_preference.xml',
        })
        imported_invoice = self._import_invoice_as_attachment_on(
            attachment=xml_attachment,
            journal=self.company_data['default_journal_purchase'],
        )
        matched_product = imported_invoice.invoice_line_ids.product_id
        self.assertEqual(matched_product, self.product_a)
