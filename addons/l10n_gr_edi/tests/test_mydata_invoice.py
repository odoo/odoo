from lxml import etree

from odoo import Command
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests import tagged
from odoo.tools import misc


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestMyDATAInvoice(AccountTestInvoicingCommon):

    @classmethod
    @AccountTestInvoicingCommon.setup_country('gr')
    def setUpClass(cls):
        super().setUpClass()

        cls.env.company.write({
            'name': 'My Greece Company',
            'vat': '047747270',
            'l10n_gr_edi_test_env': True,
            'l10n_gr_edi_aade_id': 'odoodev',
            'l10n_gr_edi_aade_key': '20ea658627fd8c7d90594fe4601d3327',
        })
        cls.partner_a.write({
            'country_id': cls.env.ref('base.gr').id,
            'vat': '047747210',
        })
        cls.env['res.company'].create({
            'name': 'Greece Partner A',
            'partner_id': cls.partner_a.id,
            'l10n_gr_edi_test_env': True,
        })
        cls.tax_24 = cls.env.ref("account.%s_l10n_gr_tax_s24_G" % cls.env.company.id)
        cls.tax_13 = cls.env.ref("account.%s_l10n_gr_tax_s13_G" % cls.env.company.id)
        cls.tax_0 = cls.env.ref("account.%s_l10n_gr_tax_s0_exempt" % cls.env.company.id)

    def _create_mydata_invoice(
            self,
            inv_type='1.1',
            tax_ids=False,
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
                'tax_ids': tax_ids or [Command.set(self.tax_24.ids)],
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

    def _create_mydata_bill(
            self,
            mydata_mark='400001924190891',
            inv_type='13.1',
            invoice_line_ids=False,
            **kwargs,
    ):
        if not invoice_line_ids:
            invoice_line_ids = [
                Command.create({
                    'product_id': self.product_a.id,
                    'tax_ids': [Command.set(self.tax_24.ids)],
                    'l10n_gr_edi_cls_category': 'category2_1',
                    'l10n_gr_edi_cls_type': 'E3_102_001',
                }),
                Command.create({
                    'product_id': self.product_b.id,
                    'tax_ids': [Command.set(self.tax_13.ids)],
                    'l10n_gr_edi_cls_category': 'category2_10',
                    'l10n_gr_edi_cls_type': 'E3_313_004',
                }),
            ]
        bill = self._create_mydata_invoice(
            move_type='in_invoice',
            inv_type=inv_type,
            invoice_line_ids=invoice_line_ids,
            **kwargs,
        )
        bill.l10n_gr_edi_document_ids = self.env['l10n_gr_edi.document'].create([{
            'move_id': bill.id,
            'mydata_mark': mydata_mark,
            'state': 'bill_fetched',
        }])
        return bill

    @staticmethod
    def _add_address(partner):
        partner.write({'zip': '10431', 'city': 'Athens'})

    def assert_mydata_xml_tree(self, invoice, expected_file_path, send_classification=False):
        if send_classification:
            xml_template = 'l10n_gr_edi.mydata_expense_classification'
            xml_vals = invoice._l10n_gr_edi_get_expense_classification_xml_vals()
        else:
            xml_template = 'l10n_gr_edi.mydata_invoice'
            xml_vals = invoice._l10n_gr_edi_get_invoices_xml_vals()

        xml_content = self.env['account.move']._l10n_gr_edi_generate_xml_content(xml_template, xml_vals)
        xml_etree = self.get_xml_tree_from_string(xml_content)

        expected_file_full_path = misc.file_path(f'{self.test_module}/tests/test_files/{expected_file_path}')
        expected_etree = etree.parse(expected_file_full_path).getroot()

        self.assertXmlTreeEqual(xml_etree, expected_etree)

    def assert_mydata_error(self, invoice, expected_error_message):
        """
        :param account.move invoice:
        :param str expected_error_message:
        """
        document = invoice.l10n_gr_edi_document_ids.sorted()[0]
        self.assertRecordValues(document, [{
            'state': 'invoice_error' if invoice.is_sale_document(include_receipts=True) else 'bill_error',
            'message': expected_error_message,
        }])

    ####################################################################################################
    # Test: assert available classification value for dynamic selection fields
    ####################################################################################################

    def test_mydata_available_inv_type_values(self):
        invoice = self._create_mydata_invoice(inv_type='1.1', cls_category='', cls_type='')
        self.assertRecordValues(invoice, [{
            'l10n_gr_edi_available_inv_type': '1.1,1.2,1.3,1.4,1.5,1.6,2.1,2.2,2.3,2.4,3.1,3.2,5.1,5.2,'
                                              '6.1,6.2,7.1,8.1,8.2,11.1,11.2,11.3,11.4,11.5,17.3,17.4',
        }])
        self.assertRecordValues(invoice.invoice_line_ids, [{
            'l10n_gr_edi_available_cls_category': 'category1_1,category1_2,category1_3,category1_4,category1_5,'
                                                  'category1_7,category1_8,category1_9,category1_95',
            'l10n_gr_edi_available_cls_type': False,
            'l10n_gr_edi_available_cls_vat': False,
        }])

        invoice.invoice_line_ids.l10n_gr_edi_cls_category = 'category1_1'
        self.assertRecordValues(invoice.invoice_line_ids, [{
            'l10n_gr_edi_available_cls_type': 'E3_561_001,E3_561_002,E3_561_007',
        }])
        invoice.invoice_line_ids.l10n_gr_edi_cls_category = 'category1_8'
        # In some cases, the order of available types are jumbled
        self.assertEqual(sorted(invoice.invoice_line_ids.l10n_gr_edi_available_cls_type.split(',')), [
            'E3_561_001', 'E3_561_002', 'E3_561_007', 'E3_562', 'E3_563', 'E3_564', 'E3_565', 'E3_566', 'E3_567',
            'E3_568', 'E3_570', 'E3_596', 'E3_597', 'E3_880_001', 'E3_881_001', 'E3_881_003', 'E3_881_004'])

    ####################################################################################################
    # Test: assert XML tree to file
    ####################################################################################################

    def test_mydata_send_invoice(self):
        invoice = self._create_mydata_invoice(invoice_line_ids=[
            Command.create({
                'product_id': self.product_a.id,
                'tax_ids': [Command.set(self.tax_24.ids)],
                'l10n_gr_edi_cls_category': 'category1_1',
                'l10n_gr_edi_cls_type': 'E3_561_001',
            }),
            Command.create({
                'product_id': self.product_b.id,
                'tax_ids': [Command.set(self.tax_13.ids)],
                'l10n_gr_edi_cls_category': 'category1_3',
                'l10n_gr_edi_cls_type': 'E3_561_002',
            }),
        ])
        self.assert_mydata_xml_tree(invoice, expected_file_path='from_odoo/mydata_invoice.xml')

    def test_mydata_send_multi_invoices(self):
        invoice_1 = self._create_mydata_invoice(inv_type='2.1', cls_category='category1_3', cls_type='E3_561_002')
        invoice_2 = self._create_mydata_invoice(inv_type='11.1', cls_category='category1_95', cls_type='')
        self.assert_mydata_xml_tree(invoice_1 + invoice_2, expected_file_path='from_odoo/mydata_multi_invoices.xml')

    def test_mydata_send_bill_cls_expense(self):
        bill = self._create_mydata_bill()
        self.assert_mydata_xml_tree(bill, expected_file_path='from_odoo/mydata_cls_expense.xml', send_classification=True)

    ####################################################################################################
    # Test: assert built-in constraints
    ####################################################################################################

    def test_l10n_gr_edi_try_send_invoices_no_credentials_and_vat(self):
        self.company_data['company'].write({
            'l10n_gr_edi_aade_id': False,
            'l10n_gr_edi_aade_key': False,
        })
        invoice = self._create_mydata_invoice()
        invoice.l10n_gr_edi_try_send_invoices()
        self.assert_mydata_error(invoice, "You need to set AADE ID and Key in the company settings.")

    def test_l10n_gr_edi_try_send_invoices_no_classification(self):
        # No invoice type
        invoice = self._create_mydata_invoice()
        invoice.l10n_gr_edi_inv_type = False
        invoice.l10n_gr_edi_try_send_invoices()
        self.assert_mydata_error(invoice, 'Missing myDATA Invoice Type.')

        # No classification category
        invoice = self._create_mydata_invoice(cls_category='')
        invoice.l10n_gr_edi_try_send_invoices()
        self.assert_mydata_error(invoice, 'Missing myDATA classification category on line 1.')

        # No classification type, and inv_type + cls_category combination doesn't allow empty cls_type
        invoice = self._create_mydata_invoice(cls_type='')
        invoice.l10n_gr_edi_try_send_invoices()
        self.assert_mydata_error(invoice, 'Missing myDATA classification type on line 1.')

    def test_l10n_gr_edi_try_send_invoices_allowed_no_cls_type(self):
        """Allow no cls_type on some combinations with available cls_type"""
        allowed_inv_type_category = (('1.1', 'category1_95'), ('3.2', 'category1_95'), ('5.1', 'category1_95'))
        for inv_type, category in allowed_inv_type_category:
            invoice = self._create_mydata_invoice(inv_type=inv_type, cls_category=category, cls_type='')
            self.assertFalse(invoice._l10n_gr_edi_get_pre_error_string())

    def test_l10n_gr_edi_try_send_invoices_invalid_tax_amount(self):
        """ Invalid tax amount should raises error. """
        invalid_tax = self.env['account.tax'].create([{
            'name': 'Bad 12%',
            'type_tax_use': 'sale',
            'amount': 12.0,
            'company_id': self.env.company.id,
        }])
        invoice = self._create_mydata_invoice(tax_ids=[Command.set(invalid_tax.ids)])
        invoice.l10n_gr_edi_try_send_invoices()
        self.assert_mydata_error(invoice, 'Invalid tax amount for line 1. The valid values are 24, 13, 6, 17, 9, 4, 0.')

    def test_l10n_gr_edi_try_send_invoices_invalid_tax_multi(self):
        """ Multiple tax should raises error. """
        invoice = self._create_mydata_invoice(tax_ids=[Command.set((self.tax_24 + self.tax_0).ids)])
        invoice.l10n_gr_edi_try_send_invoices()
        self.assert_mydata_error(invoice, 'myDATA does not support multiple taxes on line 1.')

    def test_l10n_gr_edi_try_send_invoices_invalid_tax_nonexistent(self):
        """ No tax should raises error. """
        invoice = self._create_mydata_invoice(post=False)
        invoice.invoice_line_ids.tax_ids = False
        invoice.action_post()
        invoice.l10n_gr_edi_try_send_invoices()
        self.assert_mydata_error(invoice, 'Missing tax on line 1.')

    def test_l10n_gr_edi_try_send_invoices_invalid_tax_exempt_no_category(self):
        """ Tax 0% and no tax exemption category should raises error. """
        invoice = self._create_mydata_invoice(tax_ids=[Command.set(self.tax_0.ids)])
        invoice.with_context(skip_readonly_check=True).invoice_line_ids.l10n_gr_edi_tax_exemption_category = False
        invoice.l10n_gr_edi_try_send_invoices()
        self.assert_mydata_error(invoice, 'Missing myDATA Tax Exemption Category for line 1.')
