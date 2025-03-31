# Part of Odoo. See LICENSE file for full copyright and licensing details.
from freezegun import freeze_time
from lxml import etree

from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.addons.l10n_my_edi.tests.test_file_generation import NS_MAP
from odoo.tests import Form, tagged


@tagged('post_install_l10n', 'post_install', '-at_install')
class L10nMyEDITestFileGeneration(AccountTestInvoicingCommon):

    @classmethod
    @AccountTestInvoicingCommon.setup_country('my')
    def setUpClass(cls):
        super().setUpClass()

        # TIN number is required
        cls.company_data['company'].write({
            'vat': 'C2584563200',
            'l10n_my_edi_mode': 'test',
            'l10n_my_edi_industrial_classification': cls.env['l10n_my_edi.industry_classification'].search([('code', '=', '01111')]).id,
            'l10n_my_identification_type': 'BRN',
            'l10n_my_identification_number': '202001234567',
            'state_id': cls.env.ref('base.state_my_jhr').id,
            'street': 'that one street, 5',
            'city': 'Main city',
            'phone': '+60123456789',
        })
        cls.partner_b.write({
            'vat': '123456789',
            'l10n_my_identification_type': 'BRN',
            'l10n_my_identification_number': 'NA',
            'country_id': cls.env.ref('base.us').id,
            'state_id': cls.env.ref('base.state_us_1'),
            'street': 'that other street, 3',
            'city': 'Main city',
            'phone': '+60123456785',
            'l10n_my_edi_malaysian_tin': 'EI00000000020',
            'l10n_my_edi_industrial_classification': cls.env.ref('l10n_my_edi.class_00000', raise_if_not_found=False).id,
        })
        cls.product_a.l10n_my_edi_classification_code = "001"

        cls.purchase_tax = cls.env['account.tax'].create({
            'name': 'tax_10',
            'amount_type': 'percent',
            'amount': 10,
            'type_tax_use': 'purchase',
            'country_id': cls.env.ref('base.my').id,
        })

    @freeze_time('2024-07-15 10:00:00')
    def test_07_self_billing(self):
        bill = self.init_invoice(
            'in_invoice', partner=self.partner_b, products=self.product_a, taxes=self.purchase_tax,
        )
        bill.action_post()

        file, errors = bill._l10n_my_edi_generate_invoice_xml()
        self.assertFalse(errors)
        self.assertTrue(file)

        root = etree.fromstring(file)
        # We assert that the supplier is the partner of the invoice, with all information present.
        supplier_root = root.xpath('cac:AccountingSupplierParty/cac:Party', namespaces=NS_MAP)[0]
        data_to_check = [
            ('cac:PartyIdentification/cbc:ID[@schemeID="TIN"]', 'EI00000000030'),  # The partner_b malaysian TIN is set to the customer one, and it will be transformed to supplier during submission
            ('cac:PartyIdentification/cbc:ID[@schemeID="BRN"]', self.partner_b.commercial_partner_id.l10n_my_identification_number),
            ('cbc:IndustryClassificationCode', self.partner_b.commercial_partner_id.l10n_my_edi_industrial_classification.code),  # It should use the code on the partner.
            ('cac:PartyName/cbc:Name', self.partner_b.name),
        ]
        for path, expected_value in data_to_check:
            self._assert_node_values(supplier_root, path, expected_value)
        # And that the customer is the company.
        customer_root = root.xpath('cac:AccountingCustomerParty/cac:Party', namespaces=NS_MAP)[0]
        data_to_check = [
            ('cac:PartyIdentification/cbc:ID[@schemeID="TIN"]', self.company_data['company'].vat),  # We didn't set the new field as the company is malaysian, the vat should be in use.
            ('cac:PartyIdentification/cbc:ID[@schemeID="BRN"]', self.company_data['company'].l10n_my_identification_number),
            ('cac:PartyName/cbc:Name', self.company_data['company'].name),
        ]
        for path, expected_value in data_to_check:
            self._assert_node_values(customer_root, path, expected_value)

    def test_08_refund_note(self):
        """ A refund note is issued when an invoice has received a credit note, and that credit note was paid to the customer. """
        # Create the original invoice, and receive the payment.
        invoice = self.init_invoice(
            'out_invoice', partner=self.partner_b, products=self.product_a
        )
        invoice.l10n_my_edi_external_uuid = '12345678912345678912345678'
        invoice.action_post()
        self.env['account.payment.register'].with_context(active_model='account.move', active_ids=invoice.ids).create({
            'payment_date': '2019-01-02',
        })._create_payments()
        # Create the credit note, and pay it back.
        action = invoice.action_reverse()
        reversal_wizard = self.env[action['res_model']].with_context(
            active_ids=invoice.ids,
            active_model='account.move',
            default_journal_id=invoice.journal_id.id,
        ).create({})
        action = reversal_wizard.reverse_moves()
        credit_note = self.env['account.move'].browse(action['res_id'])
        credit_note.action_post()
        self.env['account.payment.register'].with_context(active_model='account.move', active_ids=credit_note.ids).create({
            'payment_date': '2019-01-02',
        })._create_payments()
        # Generate the file and assert the type, should be "refund" (04)
        file, _errors = credit_note._l10n_my_edi_generate_invoice_xml()
        root = etree.fromstring(file)
        self._assert_node_values(
            root,
            'cbc:InvoiceTypeCode',
            '04',
            attributes={'listVersionID': '1.1'},
        )

    def test_09_credit_note(self):
        """ A credit note is issued when an invoice has received a credit note, and that credit note was not paid to the customer. """
        # Create the original invoice, don't receive a payment.
        invoice = self.init_invoice(
            'out_invoice', partner=self.partner_b, products=self.product_a
        )
        invoice.l10n_my_edi_external_uuid = '12345678912345678912345678'
        invoice.action_post()
        # Create the credit note to reduce the amount due of the invoice
        action = invoice.action_reverse()
        reversal_wizard = self.env[action['res_model']].with_context(
            active_ids=invoice.ids,
            active_model='account.move',
            default_journal_id=invoice.journal_id.id,
        ).create({})
        action = reversal_wizard.reverse_moves()
        credit_note = self.env['account.move'].browse(action['res_id'])
        with Form(credit_note) as credit_note_form:
            with credit_note_form.invoice_line_ids.edit(0) as line:
                line.price_unit = 500
        credit_note.action_post()
        # Generate the file and assert the type, should be "credit note" (03)
        file, _errors = credit_note._l10n_my_edi_generate_invoice_xml()
        root = etree.fromstring(file)
        self._assert_node_values(
            root,
            'cbc:InvoiceTypeCode',
            '02',
            attributes={'listVersionID': '1.1'},
        )

    def _assert_node_values(self, root, node_path, text, attributes=None):
        node = root.xpath(node_path, namespaces=NS_MAP)

        assert node, f'The requested node has not been found: {node_path}'

        self.assertEqual(
            node[0].text,
            text,
        )
        if attributes:
            for attribute, value in attributes.items():
                self.assertEqual(
                    node[0].attrib[attribute],
                    value,
                )
