from lxml import etree

from odoo import Command
from odoo.tests import tagged
from odoo.tools.safe_eval import expr_eval
from .test_xml_ubl_tr_common import TestUBLTRCommon
from odoo.addons.account.tests.test_account_move_send import TestAccountMoveSendCommon
import xml.etree.ElementTree as ET


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestTRAccountMoveSend(TestAccountMoveSendCommon, TestUBLTRCommon):

    _test_user_groups = None  # FIXME list needed groups

    @classmethod
    @TestAccountMoveSendCommon.setup_country('tr')
    def setUpClass(cls):
        super().setUpClass()
        # ==== Partners ====
        cls.partner_tr = cls.env['res.partner'].create({
            'name': 'partner_tr',
            'invoice_edi_format': 'ubl_tr',
            'l10n_tr_nilvera_customer_status': 'earchive',
        })

    def test_invoice_names_valid_for_nilvera(self):
        valid_names = [
            'INV-2025-00001',
            'R01/2025/00001',
            '123/2025/00001',
            'res.2025.00001',
            'RES2025/00001',
        ]
        invoices = self.env['account.move']
        for name in valid_names:
            invoice = self.init_invoice('out_invoice', invoice_date='2025-11-28', amounts=[1000])
            invoice.name = name
            invoice.action_post()
            invoices |= invoice

        wizard = self.create_send_and_print(invoices)
        self.assertNotIn('tr_moves_with_invalid_name', wizard.alerts)

    def test_invoice_names_invalid_for_nilvera(self):
        invalid_names = [
            'INV/2025/0',
            'INV/25/1012',
            'RESXYZ00001',
            'res2025ABCDE',
            'RES-XYZ-00001',
            'INVOICE/2025/00010',
        ]
        for name in invalid_names:
            invoice = self.init_invoice('out_invoice', invoice_date='2025-11-28', amounts=[1000])
            invoice.name = name
            invoice.action_post()

            wizard = self.create_send_and_print(invoice)
            self.assertIn('tr_moves_with_invalid_name', wizard.alerts)

    def test_no_attachment_on_ubl_xml_for_ubl_tr(self):
        # Setup invoice
        invoice = self.init_invoice(
            move_type='out_invoice',
            partner=self.partner_tr,
            invoice_date='2025-11-28',
            amounts=[1000],
            taxes=self.tax_sale_a,
            post=True,
        )

        # Execute send
        wizard = self.create_send_and_print(invoice, True)
        wizard.sending_methods = False
        wizard.extra_edis = False
        wizard.alerts = False
        wizard.action_send_and_print()

        xml_data = invoice.ubl_cii_xml_id.raw
        self.assertIsNotNone(xml_data, "XML data should exist")

        xml_tree = ET.fromstring(xml_data.decode('utf-8'))

        ns = {'cac': 'urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2'}

        # Main assertion - no attachments should exist
        attachments = xml_tree.findall('.//cac:AdditionalDocumentReference/cac:Attachment', ns)
        self.assertFalse(
            attachments,
            f"Found {len(attachments)} unexpected Attachment node(s) in UBL TR XML"
        )

    def test_send_email_with_recipient_bank(self):
        """
        invoice xml generation should work when company has bank account with bank information
        in order to send email with invoice xml to recipient's bank
        """
        bank = self.company_data['company'].bank_ids[0]
        bank.bank_name = 'Test Bank'
        bank.bank_bic = 'TESTTRISXXX'
        self.assertTrue(self._generate_invoice_xml(self.einvoice_partner), "XML generation failed")

    def test_missing_mersis_and_trade_registry_blocks_send(self):
        company_partner = self.company_data['company'].partner_id
        company_partner.additional_identifiers = {}

        invoice = self._generate_invoice(self.einvoice_partner)

        # Block if no Identifier
        wizard = self.create_send_and_print(invoice)
        self.assertIn('tr_companies_missing_required_codes', wizard.alerts)

        # Allow if TR_MERSIS or TR_TICARET_SICIL is there
        company_partner.additional_identifiers = {'TR_MERSIS': '0-123456780100019'}
        wizard = self.create_send_and_print(invoice)
        self.assertNotIn('tr_companies_missing_required_codes', wizard.alerts)

        company_partner.additional_identifiers = {'TR_TICARET_SICIL': '12345'}
        wizard = self.create_send_and_print(invoice)
        self.assertNotIn('tr_companies_missing_required_codes', wizard.alerts)

    def test_withholding_reason_inconsistent_with_the_lines_blocks_send(self):
        chart = self.env['account.chart.template']
        tax_wh_9_10 = chart.ref('tr_s_wh_20_9_10')
        tax_wh_7_10 = chart.ref('tr_s_wh_20_7_10')
        reason_607 = chart.ref('l10n_tr_nilvera_einvoice.account_tax_code_607')  # 90%

        invoice = self._generate_invoice(
            self.einvoice_partner,
            tax_wh_9_10,
            l10n_tr_exemption_code_id=reason_607.id,
        )
        wizard = self.create_send_and_print(invoice)
        self.assertNotIn('tr_moves_with_inconsistent_withholding', wizard.alerts)
        self.assertNotIn('tr_moves_without_withholding_reason', wizard.alerts)

        # a 90% reason cannot describe a 7/10 tax
        invoice.button_draft()
        invoice.invoice_line_ids.tax_ids = tax_wh_7_10
        invoice.l10n_tr_exemption_code_id = reason_607
        invoice.action_post()
        wizard = self.create_send_and_print(invoice)
        self.assertIn('tr_moves_with_inconsistent_withholding', wizard.alerts)

    def test_withholding_at_two_ratios_blocks_send(self):
        chart = self.env['account.chart.template']
        tax_wh_9_10 = chart.ref('tr_s_wh_20_9_10')
        tax_wh_7_10 = chart.ref('tr_s_wh_20_7_10')

        # forced type: the shape only an import or the API can produce
        invoice = self._generate_invoice(
            self.einvoice_partner,
            tax_wh_9_10,
            l10n_tr_gib_invoice_type='TEVKIFAT',
        )
        invoice.button_draft()
        invoice.invoice_line_ids = [Command.create({
            'product_id': self.product_a.id,
            'price_unit': 40.0,
            'tax_ids': [Command.set(tax_wh_7_10.ids)],
        })]
        invoice.l10n_tr_gib_invoice_type = 'TEVKIFAT'
        invoice.action_post()

        wizard = self.create_send_and_print(invoice)
        self.assertIn('tr_moves_with_inconsistent_withholding', wizard.alerts)

    def test_withholding_return_does_not_block_send(self):
        chart = self.env['account.chart.template']
        tax_wh_9_10 = chart.ref('tr_s_wh_20_9_10')
        reason_607 = chart.ref('l10n_tr_nilvera_einvoice.account_tax_code_607')

        invoice = self._generate_invoice(
            self.einvoice_partner,
            tax_wh_9_10,
            l10n_tr_exemption_code_id=reason_607.id,
        )
        invoice.l10n_tr_nilvera_send_status = 'succeed'
        credit_note = invoice._reverse_moves()
        credit_note.action_post()

        wizard = self.create_send_and_print(credit_note)
        self.assertEqual(credit_note.l10n_tr_gib_invoice_type, 'TEVKIFATIADE')
        self.assertNotIn('tr_moves_with_inconsistent_withholding', wizard.alerts)

        # positive control: the same wizard does report a return that withholds nothing
        credit_note.button_draft()
        credit_note.invoice_line_ids.tax_ids = self.env['account.tax']
        credit_note.action_post()
        wizard = self.create_send_and_print(credit_note)
        self.assertIn('tr_moves_with_inconsistent_withholding', wizard.alerts)

    def test_send_demands_the_reason_exactly_when_the_lines_withhold(self):
        chart = self.env['account.chart.template']
        tax_20 = chart.ref('tr_s_20')
        fpos_wh_9_10 = chart.ref('tr_fp_wh_9_10')
        fpos_wh_7_10 = chart.ref('tr_fp_wh_7_10')
        reason_607 = chart.ref('l10n_tr_nilvera_einvoice.account_tax_code_607')  # 90%
        reason_603 = chart.ref('l10n_tr_nilvera_einvoice.account_tax_code_603')  # 70%
        # `Update Taxes and Accounts` maps the product's own tax
        self.product_a.taxes_id = tax_20

        # `Form` ANDs the modifiers of every occurrence of a field, and this one is in the
        # view twice, so the withholding occurrence's `required` is evaluated by hand.
        arch = etree.fromstring(
            self.env['account.move'].get_view(self.env.ref('account.view_move_form').id, 'form')['arch'],
        )
        required_expression = arch.xpath(
            "//field[@name='l10n_tr_exemption_code_id'][@string='Withholding Reason']",
        )[0].get('required')

        def reason_is_required(invoice):
            return bool(expr_eval(required_expression, {
                'l10n_tr_gib_invoice_type': invoice.l10n_tr_gib_invoice_type,
                'l10n_tr_withholding_ratio': invoice.l10n_tr_withholding_ratio,
            }))

        def alerts_of(invoice):
            invoice.action_post()
            keys = self.create_send_and_print(invoice).alerts
            invoice.button_draft()
            return keys

        invoice = self._generate_invoice(self.einvoice_partner, tax_20)
        invoice.button_draft()

        # 1. plain VAT: nothing withholds
        self.assertEqual(invoice.l10n_tr_gib_invoice_type, 'SATIS')
        self.assertFalse(reason_is_required(invoice))
        self.assertNotIn('tr_moves_without_withholding_reason', alerts_of(invoice))

        # 2. picked, not applied: nothing may be demanded while the line carries 20% VAT
        invoice.fiscal_position_id = fpos_wh_9_10
        self.assertEqual(invoice.invoice_line_ids.tax_ids, tax_20)
        self.assertEqual(invoice.l10n_tr_gib_invoice_type, 'SATIS')
        self.assertFalse(reason_is_required(invoice), "nothing may be demanded before the update")
        self.assertNotIn('tr_moves_without_withholding_reason', alerts_of(invoice))

        # 3. applied: the lines withhold 9/10, so the reason is demanded
        invoice.action_update_fpos_values()
        self.assertEqual(invoice.l10n_tr_gib_invoice_type, 'TEVKIFAT')
        self.assertFalse(invoice.l10n_tr_exemption_code_id)
        self.assertTrue(reason_is_required(invoice))
        self.assertIn('tr_moves_without_withholding_reason', alerts_of(invoice))

        # 4. a 90% reason for a 9/10 tax
        invoice.l10n_tr_exemption_code_id = reason_607
        alerts = alerts_of(invoice)
        self.assertNotIn('tr_moves_without_withholding_reason', alerts)
        self.assertNotIn('tr_moves_with_inconsistent_withholding', alerts)

        # 5. another rate, applied: the 90% reason is dropped and demanded again
        invoice.fiscal_position_id = fpos_wh_7_10
        invoice.action_update_fpos_values()
        self.assertEqual(invoice.l10n_tr_withholding_ratio, 0.7)
        self.assertFalse(invoice.l10n_tr_exemption_code_id)
        self.assertTrue(reason_is_required(invoice))
        self.assertIn('tr_moves_without_withholding_reason', alerts_of(invoice))

        # 6. the matching reason clears it
        invoice.l10n_tr_exemption_code_id = reason_603
        alerts = alerts_of(invoice)
        self.assertNotIn('tr_moves_without_withholding_reason', alerts)
        self.assertNotIn('tr_moves_with_inconsistent_withholding', alerts)
