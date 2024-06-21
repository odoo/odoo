from lxml import etree

from odoo import Command
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests import tagged
from odoo.tools import misc


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestGreeceMyDATA(AccountTestInvoicingCommon):
    @classmethod
    def setUpClass(cls, chart_template_ref='gr'):
        super().setUpClass(chart_template_ref=chart_template_ref)
        cls.env.company.write({
            'name': 'My Greece Company',
            'vat': '047747270',
            'l10n_gr_edi_test_env': True,
            'l10n_gr_edi_aade_id': 'odoodev',
            'l10n_gr_edi_aade_key': '20ea658627fd8c7d90594fe4601d3327',
        })
        cls.partner_a.write({
            'country_id': cls.env.ref('base.gr').id,
        })
        cls.env['res.company'].create({
            'name': 'Greece Partner A',
            'vat': '047747210',
            'partner_id': cls.partner_a.id,
            'l10n_gr_edi_test_env': True,
        })

        cls.tax_24 = cls.env['account.tax'].create({
            'name': '24%',
            'type_tax_use': 'sale',
            'amount': 24.0,
            'company_id': cls.env.company.id,
        })
        cls.tax_13 = cls.env['account.tax'].create({
            'name': '13%',
            'type_tax_use': 'sale',
            'amount': 13.0,
            'company_id': cls.env.company.id,
        })
        cls.tax_0 = cls.env['account.tax'].create({
            'name': '0%',
            'type_tax_use': 'sale',
            'amount': 0.0,
            'company_id': cls.env.company.id,
        })

    def _create_multi_invoice_line_ids(
            self,
            tax_id=False,
            cls_categories=('category1_1', 'category1_3'),
            cls_types=('E3_561_001', 'E3_561_002'),
    ):
        return [
            Command.create({
                'product_id': self.product_a.id,
                'tax_ids': [tax_id or self.tax_24.id],
                'l10n_gr_edi_cls_category': cls_categories[0],
                'l10n_gr_edi_cls_type': cls_types[0],
            }),
            Command.create({
                'product_id': self.product_b.id,
                'tax_ids': [tax_id or self.tax_13.id],
                'l10n_gr_edi_cls_category': cls_categories[1],
                'l10n_gr_edi_cls_type': cls_types[1],
            }),
        ]

    def _create_invoice(
            self,
            inv_type='1.1',
            tax_id=False,
            cls_category='category1_1',
            cls_type='E3_561_001',
            post=True,
            paid=True,
            **kwargs,
    ):
        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_a.id,
            'invoice_date': '2024-01-01',
            'date': '2024-01-01',
            'l10n_gr_edi_inv_type': inv_type,
            'invoice_line_ids': [Command.create({
                'product_id': self.product_a.id,
                'tax_ids': [tax_id or self.tax_24.id],
                'l10n_gr_edi_cls_category': cls_category,
                'l10n_gr_edi_cls_type': cls_type,
            })],
            **kwargs,
        })
        if post:
            invoice.action_post()
        if paid:
            self.env['account.payment.register'] \
                .with_context(active_ids=invoice.ids, active_model='account.move') \
                .create({'payment_date': invoice.date}) \
                ._create_payments()

        return invoice

    def _create_bill(
            self,
            l10n_gr_edi_mark='400001924190891',
            inv_type='13.1',
            invoice_line_ids=False,
            **kwargs,
    ):
        if not invoice_line_ids:
            invoice_line_ids = self._create_multi_invoice_line_ids(
                cls_categories=('category2_1', 'category2_10'),
                cls_types=('E3_102_001', 'E3_313_004'),
            )
        return self._create_invoice(
            move_type='in_invoice',
            l10n_gr_edi_mark=l10n_gr_edi_mark,
            inv_type=inv_type,
            invoice_line_ids=invoice_line_ids,
            **kwargs,
        )

    @staticmethod
    def _add_address(partner):
        partner.write({'zip': '10431', 'city': 'Athens'})

    def assert_mydata_xml_tree(self, invoice, expected_file_path, send_classification=False):
        xml_vals = invoice._l10n_gr_edi_get_invoices_xml_vals() if not send_classification else \
            invoice._l10n_gr_edi_get_expense_classification_xml_vals()
        xml_content = self.env['l10n_gr_edi.document']._generate_xml_content(xml_vals, send_classification)
        xml_etree = self.get_xml_tree_from_string(xml_content.encode('utf-8'))

        expected_file_full_path = misc.file_path(f'{self.test_module}/tests/test_files/{expected_file_path}')
        expected_etree = etree.parse(expected_file_full_path).getroot()

        self.assertXmlTreeEqual(xml_etree, expected_etree)

    def assert_mydata_error(self, invoice, expected_error_message):
        self.assertRecordValues(invoice.l10n_gr_edi_active_document_id, [{'state': 'error'}])
        self.assertRecordValues(invoice, [{'l10n_gr_edi_message': expected_error_message}])

    ####################################################################################################
    # Test: assert available classification value for dynamic selection fields
    ####################################################################################################

    def test_mydata_available_inv_type_values(self):
        invoice = self._create_invoice(inv_type='1.1', cls_category='', cls_type='')
        self.assertRecordValues(invoice, [{
            'l10n_gr_edi_available_inv_type': '1.1,1.2,1.3,1.4,1.5,1.6,2.1,2.2,2.3,2.4,3.1,3.2,5.1,5.2,6.1,6.2,7.1,'
                                              '8.1,8.2,11.1,11.2,11.3,11.4,11.5,17.3,17.4',
        }])
        self.assertRecordValues(invoice.invoice_line_ids, [{
            'l10n_gr_edi_available_cls_category': 'category1_1,category1_2,category1_3,category1_4,category1_5,'
                                                  'category1_7,category1_8,category1_9,category1_95',
            'l10n_gr_edi_available_cls_type': False,
            'l10n_gr_edi_available_cls_vat': False,
        }])

        invoice.invoice_line_ids.write({'l10n_gr_edi_cls_category': 'category1_1'})
        self.assertRecordValues(invoice.invoice_line_ids, [{
            'l10n_gr_edi_available_cls_type': 'E3_561_001,E3_561_002,E3_561_007',
        }])
        invoice.invoice_line_ids.write({'l10n_gr_edi_cls_category': 'category1_8'})
        # In some cases, the order of available types are jumbled
        self.assertEqual(sorted(invoice.invoice_line_ids.l10n_gr_edi_available_cls_type.split(',')), [
            'E3_561_001', 'E3_561_002', 'E3_561_007', 'E3_562', 'E3_563', 'E3_564', 'E3_565', 'E3_566', 'E3_567',
            'E3_568', 'E3_570', 'E3_596', 'E3_597', 'E3_880_001', 'E3_881_001', 'E3_881_003', 'E3_881_004'])

    ####################################################################################################
    # Test: assert XML tree to file
    ####################################################################################################

    def test_mydata_send_invoice(self):
        invoice = self._create_invoice(invoice_line_ids=self._create_multi_invoice_line_ids())
        self.assert_mydata_xml_tree(invoice, expected_file_path='from_odoo/mydata_invoice.xml')

    def test_mydata_send_multi_invoices(self):
        invoice = self._create_invoice(inv_type='2.1', cls_category='category1_3', cls_type='E3_561_002')
        invoice |= self._create_invoice(inv_type='11.1', cls_category='category1_95', cls_type='')
        self.assert_mydata_xml_tree(invoice, expected_file_path='from_odoo/mydata_multi_invoices.xml')

    def test_mydata_send_bill_cls_expense(self):
        bill = self._create_bill()
        self.assert_mydata_xml_tree(bill, expected_file_path='from_odoo/mydata_cls_expense.xml', send_classification=True)

    ####################################################################################################
    # Test: assert xml_vals dictionary values
    ####################################################################################################

    def test_mydata_xml_vals_invoice(self):
        invoice = self._create_invoice(invoice_line_ids=self._create_multi_invoice_line_ids())
        xml_vals = invoice._l10n_gr_edi_get_invoices_xml_vals()
        self.assertDictEqual(xml_vals, {'invoices': [{
            'header_series': 'INV_2024', 'header_aa': '00001', 'header_issue_date': '2024-01-01',
            'header_invoice_type': '1.1', 'header_currency': 'EUR',

            'issuer_vat': '047747270', 'issuer_country': 'GR', 'issuer_branch': 0,
            'counterpart_vat': '123456780', 'counterpart_country': 'GR', 'counterpart_branch': 0,
            'payment_details': [{'type': '1', 'amount': 1466.0}],

            'details': [
                {'line_number': 1, 'net_value': 1000.0, 'vat_amount': 240.0, 'vat_category': 1,
                 'icls': [{'category': 'category1_1', 'type': 'E3_561_001', 'amount': 1000.0}]},
                {'line_number': 2, 'net_value': 200.0, 'vat_amount': 26.0, 'vat_category': 2,
                 'icls': [{'category': 'category1_3', 'type': 'E3_561_002', 'amount': 200.0}]}],

            'summary_total_net_value': 1200.0, 'summary_total_vat_amount': 266.0, 'summary_total_withheld_amount': 0,
            'summary_total_fees_amount': 0, 'summary_total_stamp_duty_amount': 0,
            'summary_total_other_taxes_amount': 0, 'summary_total_deductions_amount': 0,
            'summary_total_gross_value': 1466.0,
            'summary_icls': [{'type': 'E3_561_001', 'category': 'category1_1', 'amount': 1000.0},
                             {'type': 'E3_561_002', 'category': 'category1_3', 'amount': 200.0}]}]})

    def test_mydata_xml_vals_multi_invoices(self):
        invoice = self._create_invoice(inv_type='2.1', cls_category='category1_3', cls_type='E3_561_002')
        invoice |= self._create_invoice(inv_type='11.1', cls_category='category1_95', cls_type='')
        xml_vals = invoice._l10n_gr_edi_get_invoices_xml_vals()

        self.assertDictEqual(xml_vals, {'invoices': [
            {'header_series': 'INV_2024', 'header_aa': '00001', 'header_issue_date': '2024-01-01',
             'header_invoice_type': '2.1', 'header_currency': 'EUR', 'details': [
                {'line_number': 1, 'net_value': 1000.0, 'vat_amount': 240.0, 'vat_category': 1,
                 'icls': [{'category': 'category1_3', 'type': 'E3_561_002', 'amount': 1000.0}]}],
             'summary_total_net_value': 1000.0, 'summary_total_vat_amount': 240.0, 'summary_total_withheld_amount': 0,
             'summary_total_fees_amount': 0, 'summary_total_stamp_duty_amount': 0,
             'summary_total_other_taxes_amount': 0, 'summary_total_deductions_amount': 0,
             'summary_total_gross_value': 1240.0,
             'issuer_vat': '047747270', 'issuer_country': 'GR', 'issuer_branch': 0,
             'counterpart_vat': '123456780', 'counterpart_country': 'GR', 'counterpart_branch': 0,
             'payment_details': [{'type': '1', 'amount': 1240.0}],
             'summary_icls': [{'type': 'E3_561_002', 'category': 'category1_3', 'amount': 1000.0}]},

            {'header_series': 'INV_2024', 'header_aa': '00002', 'header_issue_date': '2024-01-01',
             'header_invoice_type': '11.1', 'header_currency': 'EUR', 'details': [
                {'line_number': 1, 'net_value': 1000.0, 'vat_amount': 240.0, 'vat_category': 1,
                 'icls': [{'category': 'category1_95', 'amount': 1000.0}]}],
             'summary_total_net_value': 1000.0, 'summary_total_vat_amount': 240.0, 'summary_total_withheld_amount': 0,
             'summary_total_fees_amount': 0, 'summary_total_stamp_duty_amount': 0,
             'summary_total_other_taxes_amount': 0, 'summary_total_deductions_amount': 0,
             'summary_total_gross_value': 1240.0,
             'issuer_vat': '047747270', 'issuer_country': 'GR', 'issuer_branch': 0,
             'payment_details': [{'type': '1', 'amount': 1240.0}],
             'summary_icls': [{'category': 'category1_95', 'amount': 1000.0}]}]})

    def test_mydata_xml_vals_invoice_no_counterpart(self):
        invoice = self._create_invoice(inv_type='11.1', cls_category='category1_8', cls_type='E3_562')
        xml_vals = invoice._l10n_gr_edi_get_invoices_xml_vals()

        self.assertDictEqual(xml_vals, {'invoices': [
            {'header_series': 'INV_2024', 'header_aa': '00001', 'header_issue_date': '2024-01-01',
             'header_invoice_type': '11.1', 'header_currency': 'EUR', 'details': [
                {'line_number': 1, 'net_value': 1000.0, 'vat_amount': 240.0, 'vat_category': 1,
                 'icls': [{'category': 'category1_8', 'type': 'E3_562', 'amount': 1000.0}]}],
             'summary_total_net_value': 1000.0, 'summary_total_vat_amount': 240.0, 'summary_total_withheld_amount': 0,
             'summary_total_fees_amount': 0, 'summary_total_stamp_duty_amount': 0,
             'summary_total_other_taxes_amount': 0, 'summary_total_deductions_amount': 0,
             'summary_total_gross_value': 1240.0, 'issuer_vat': '047747270', 'issuer_country': 'GR',
             'issuer_branch': 0, 'payment_details': [{'type': '1', 'amount': 1240.0}],
             'summary_icls': [{'type': 'E3_562', 'category': 'category1_8', 'amount': 1000.0}]}]})

    def test_mydata_xml_vals_cls_expense(self):
        bill = self._create_bill()
        xml_vals = bill._l10n_gr_edi_get_expense_classification_xml_vals()

        self.assertDictEqual(xml_vals, {'invoices': [{'mark': '400001924190891', 'details': [
            {'line_number': 1, 'ecls': [{'category': 'category2_1', 'type': 'E3_102_001', 'amount': 800.0}]},
            {'line_number': 2, 'ecls': [{'category': 'category2_10', 'type': 'E3_313_004', 'amount': 160.0}]}]}]})

    def test_mydata_xml_vals_cls_expense_details_xor_transaction(self):
        bill = self._create_bill()
        xml_vals = bill._l10n_gr_edi_get_expense_classification_xml_vals()
        have_transaction_mode = 'transaction_mode' in xml_vals['invoices'][0]
        have_details = 'details' in xml_vals['invoices'][0]
        self.assertTrue(have_transaction_mode ^ have_details,
                        'Bill xml_vals should have either transaction_mode or details, but not both or none')

    def test_mydata_xml_vals_cls_expense_with_cls_vat(self):
        bill = self._create_bill(inv_type='13.1', invoice_line_ids=[Command.create({
            'product_id': self.product_a.id,
            'tax_ids': [self.tax_24.id],
            'l10n_gr_edi_cls_category': 'category2_4',
            'l10n_gr_edi_cls_type': 'E3_585_016',
            'l10n_gr_edi_cls_vat': 'VAT_361',
        })])
        xml_vals = bill._l10n_gr_edi_get_expense_classification_xml_vals()

        self.assertDictEqual(xml_vals, {'invoices': [{'mark': '400001924190891', 'details': [
            {'line_number': 1, 'ecls': [{'category': 'category2_4', 'type': 'E3_585_016', 'amount': 800.0},
                                        {'type': 'VAT_361', 'amount': 800.0}]}]}]})

    ####################################################################################################
    # Test: assert built-in constraints
    ####################################################################################################

    def test_l10n_gr_edi_get_errors_pre_request_no_credentials_and_vat(self):
        self.company_data['company'].write({
            'l10n_gr_edi_aade_id': False,
            'l10n_gr_edi_aade_key': False,
        })
        invoice = self._create_invoice()
        invoice._l10n_gr_edi_get_errors_pre_request()
        errors = '\n'.join(('Missing VAT on Company My Greece Company',
                            'Missing VAT on Partner Greece Partner A',
                            'You need to set AADE User ID and Subscription Key in the settings.'))
        self.assert_mydata_error(invoice, errors)

    def test_l10n_gr_edi_get_errors_pre_request_no_classification(self):
        # No invoice type
        invoice = self._create_invoice(inv_type='')
        invoice._l10n_gr_edi_get_errors_pre_request()
        self.assert_mydata_error(invoice, 'Missing MyDATA Invoice Type')

        # No classification category
        invoice = self._create_invoice(cls_category='')
        invoice._l10n_gr_edi_get_errors_pre_request()
        self.assert_mydata_error(invoice, 'Missing MyDATA classification category on line product_a')

        # No classification type, and inv_type + cls_category combination doesn't allow empty cls_type
        invoice = self._create_invoice(cls_type='')
        invoice._l10n_gr_edi_get_errors_pre_request()
        self.assert_mydata_error(invoice, 'Missing MyDATA classification type on line product_a')

    def test_l10n_gr_edi_get_errors_pre_request_allowed_no_cls_type(self):
        allowed_inv_type_category = (('1.1', 'category1_95'), ('3.2', 'category1_95'), ('5.1', 'category1_95'))
        for inv_type, category in allowed_inv_type_category:
            invoice = self._create_invoice(inv_type=inv_type, cls_category=category, cls_type='')
            invoice._l10n_gr_edi_get_errors_pre_request()
            # Allow no cls_type on some combinations with available cls_type
            self.assertFalse(invoice.l10n_gr_edi_active_document_id.message)

    def test_l10n_gr_edi_get_errors_pre_request_invalid_tax(self):
        # Invalid tax amount
        self.tax_13.amount = 12.0
        invoice = self._create_invoice(tax_id=self.tax_13.id)
        invoice._l10n_gr_edi_get_errors_pre_request()
        self.assert_mydata_error(invoice, 'Invalid tax amount for line product_a. The valid values are 24, 13, 6, 17, 9, 4, 0')
        invoice.button_draft()  # for easier modification

        # Multiple tax
        invoice.invoice_line_ids.tax_ids = [self.tax_24.id, self.tax_0.id]
        invoice._l10n_gr_edi_get_errors_pre_request()
        self.assert_mydata_error(invoice, 'MyDATA does not support multiple taxes on line product_a')

        # No tax
        invoice.invoice_line_ids.tax_ids = False
        invoice._l10n_gr_edi_get_errors_pre_request()
        self.assert_mydata_error(invoice, 'Missing tax on line product_a')

        # Tax 0% and no tax exemption category
        invoice.invoice_line_ids.tax_ids = [self.tax_0.id]
        invoice.invoice_line_ids.l10n_gr_edi_tax_exemption_category = False
        invoice._l10n_gr_edi_get_errors_pre_request()
        self.assert_mydata_error(invoice, 'MyDATA Tax Exemption Category is missing for line product_a')
