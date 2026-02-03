import base64
from datetime import timedelta

from lxml import etree

from odoo import Command, fields, tools
from odoo.exceptions import UserError
from odoo.tests import freeze_time, patch, tagged

from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.addons.base.tests.test_ir_cron import CronMixinCase
from odoo.addons.l10n_pl_edi.tools.ksef_api_service import KsefApiService


def attachment_to_dict(attachment):
    return {'name': attachment.name, 'raw': attachment.raw}


@tagged('post_install', '-at_install', 'post_install_l10n')
class TestL10nPlEdi(AccountTestInvoicingCommon, CronMixinCase):

    @classmethod
    @AccountTestInvoicingCommon.setup_country('pl')
    @freeze_time('2026-01-23')
    def setUpClass(cls):
        super().setUpClass()

        cls.country_pl = cls.env.ref('base.pl')
        cls.company = cls.company_data['company']
        cls.company.write({
            'country_id': cls.country_pl.id,
            'vat': 'PL1234567883',
            'street': 'Test Street 1',
            'city': 'Warsaw',
            'zip': '00-001',
        })

        cls.partner_pl = cls.env['res.partner'].create({
            'name': 'Test Customer PL',
            'is_company': True,
            'country_id': cls.country_pl.id,
            'vat': 'PL1111111111',
            'street': 'Partner St. 5',
            'city': 'Krakow',
            'zip': '30-001',
        })
        cls.tax_23 = cls.company_data['default_tax_sale'].copy({
            'amount': 23.0,
            'name': 'VAT 23%',
            'amount_type': 'percent',
        })
        cls.product_a.taxes_id = cls.tax_23
        cls.cash_journal = cls.company_data['default_journal_cash']
        cls.cash_journal.inbound_payment_method_line_ids.payment_account_id = cls.cash_journal.default_account_id.id

        cls.env['ir.config_parameter'].sudo().set_param('l10n_pl_edi_ksef.mode', 'test')

        def read_certificate_file(filename, b64=False):
            path = f'l10n_pl_edi/tests/certificate/{filename}'
            with tools.file_open(path, mode='rb') as fd:
                content = fd.read()
                return base64.b64encode(content) if b64 else content

        # This Certificate will NOT work for the current test VAT with KSEF (not even in test mode),
        # AND will even expire, but it's useful to have something to test with when we mock
        # the API calls
        key_filename, cert_filename = 'l10n_pl_edi_test.key', 'l10n_pl_edi_test.pem'
        key = cls.env['certificate.key'].create(dict(
            company_id=cls.company.id,
            name=key_filename,
            content=read_certificate_file(key_filename, b64=True),
            password='Qwertyuiop@12345',
        ))
        cert = cls.env['certificate.certificate'].create(dict(
            company_id=cls.company.id,
            name=cert_filename,
            content=read_certificate_file(cert_filename, b64=True),
            private_key_id=key.id,
        ))
        cls.company.sudo().write({
            'l10n_pl_edi_register': True,
            'l10n_pl_edi_certificate': cert.id,
            'l10n_pl_edi_access_token': "aa33ccee",
            'l10n_pl_edi_refresh_token': "bb44ddff",
        })

        cls.standard_invoice = cls.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': cls.partner_pl.id,
            'invoice_date': fields.Date.today(),
            'invoice_line_ids': [
                Command.create({
                    'product_id': cls.product_a.id,
                    'quantity': 1,
                    'price_unit': 1000.0,
                })
            ],
        })

    def _get_xml_value(self, xml_content, xpath):
        """Helper to parse XML and return text of a specific node."""
        nodes = self._get_xml_nodes(xml_content, xpath)
        if nodes:
            return nodes[0].text
        return ""

    def _get_xml_nodes(self, xml_content, xpath):
        """Helper to return a list of nodes."""
        root = etree.fromstring(xml_content)
        ns = {'ns': 'http://crd.gov.pl/wzor/2025/06/25/13775/'}
        return root.xpath(xpath, namespaces=ns)

    def _assert_export_invoice(self, invoice, filename):
        path = f'l10n_pl_edi/tests/export_xmls/{filename}'
        with tools.file_open(path, mode='rb') as fd:
            expected_tree = etree.fromstring(fd.read())
        xml = invoice._l10n_pl_edi_render_xml()
        invoice_etree = etree.fromstring(xml)
        try:
            self.assertXmlTreeEqual(invoice_etree, expected_tree)
        except AssertionError as ae:
            ae.args = (ae.args[0] + f"\nFile used for comparison: {filename}", )
            raise

    @freeze_time('2026-01-23')
    def test_ksef_fa3_standard_vat(self):
        """
        Standard VAT Invoice.
        This test verifies that a regular Odoo invoice (not a down payment or correction)
        generates a KSeF XML with the invoice type <RodzajFaktury>VAT</RodzajFaktury>.
        It simulates a simple sale of a product.
        """
        self.standard_invoice.action_post()
        self._assert_export_invoice(self.standard_invoice, "standert_fa3_format.xml")

    @freeze_time('2026-01-23')
    def test_scenario_correction_standard(self):
        """
        Correction of a Standard Invoice (KOR).
        This test verifies that creating a Credit Note (reversal) for a standard invoice
        generates a KSeF XML with invoice type KOR.
        """
        # Create Invoice
        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_pl.id,
            'invoice_date': fields.Date.today(),
            'invoice_line_ids': [Command.create({'product_id': self.product_a.id, 'price_unit': 1000.0})],
        })
        invoice.action_post()

        reversal_wizard = self.env['account.move.reversal'].create({
            'reason': 'Correction Test',
            'journal_id': invoice.journal_id.id,
            'move_ids': invoice.ids,
        })
        reversal_wizard.refund_moves()

        credit_note = invoice.reversal_move_ids
        credit_note.action_post()

        self._assert_export_invoice(credit_note, 'standerd_fa3_credit_note.xml')

    @freeze_time('2026-01-23')
    def test_payment_logic_partial_mixed_methods(self):
        """
        Test the <Platnosc> block for a Partially Paid invoice with mixed methods.
        We expect:
        - ZnacznikZaplatyCzesciowej = 1
        - Two ZaplataCzesciowa blocks.
        - FormaPlatnosci = 1 for Cash.
        - FormaPlatnosci = 6 for Bank.
        """
        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_pl.id,
            'invoice_date': fields.Date.today(),
            'currency_id': self.env.ref('base.PLN').id,
            'invoice_line_ids': [Command.create({
                'product_id': self.product_a.id,
                'quantity': 1,
                'price_unit': 1000.0,
            })],
        })
        invoice.action_post()

        self.env['account.payment.register'].create({
            'amount': 300.0,
            'journal_id': self.cash_journal.id,
            'payment_date': fields.Date.today(),
            'line_ids': invoice.line_ids.filtered(lambda line: line.display_type == 'payment_term'),
        })._create_payments()

        self.env['account.payment.register'].create({
            'amount': 400.0,
            'journal_id': self.cash_journal.id,
            'payment_date': fields.Date.today(),
            'line_ids': invoice.line_ids.filtered(lambda line: line.display_type == 'payment_term'),
        })._create_payments()

        self.assertEqual(invoice.payment_state, 'partial')
        self._assert_export_invoice(invoice, 'partial_paid_invoice_bank_cash.xml')

    @freeze_time('2026-01-23')
    def test_payment_logic_fully_paid(self):
        """
        Test the <Platnosc> block for a Fully Paid invoice.
        We expect:
        - Zaplacono = 1
        - ZnacznikZaplatyCzesciowej = 2 (Not partial, because it is fully paid)
        - DataZaplaty present
        """
        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_pl.id,
            'invoice_date': fields.Date.today(),
            'invoice_line_ids': [Command.create({'product_id': self.product_a.id, 'price_unit': 100.0})],
        })
        invoice.action_post()
        self.env['account.payment.register'].create({
            'journal_id': self.cash_journal.id,
            'line_ids': invoice.line_ids.filtered(lambda line: line.display_type == 'payment_term'),
        })._create_payments()

        self.assertEqual(invoice.payment_state, 'paid')
        self._assert_export_invoice(invoice, 'full_paid_invoice.xml')

    @freeze_time('2026-01-23')
    def test_payment_logic_partial_then_full_payment(self):
        """
        Test the <Platnosc> block when an invoice is paid in installments (Partial -> Full).

        Scenario:
        1. Create Invoice for 1000 PLN.
        2. Pay 400 PLN (Status becomes Partial).
        3. Pay remaining 600 PLN (Status becomes Paid).

        Expectations:
        - ZnacznikZaplatyCzesciowej = 2 (It is fully paid, so flag is 2/No).
        - ZaplataCzesciowa nodes should be present (listing the 2 payments).
        - Zaplacono should NOT be present (based on your template logic for multi-payment).
        """
        # 1. Create Invoice
        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_pl.id,
            'invoice_date': fields.Date.today(),
            'currency_id': self.env.ref('base.PLN').id,
            'invoice_line_ids': [Command.create({
                'product_id': self.product_a.id,
                'quantity': 1,
                'price_unit': 1000.0,
                'tax_ids': [],
            })],
        })
        invoice.action_post()

        # 2. Register First Partial Payment (400 PLN)
        self.env['account.payment.register'].create({
            'amount': 400.0,
            'journal_id': self.cash_journal.id,
            'payment_date': fields.Date.today(),
            'line_ids': invoice.line_ids.filtered(lambda line: line.display_type == 'payment_term'),
        })._create_payments()
        self.assertEqual(invoice.payment_state, 'partial')

        # 3. Register Remaining 600 PLN Payment
        self.env['account.payment.register'].create({
            'amount': 600.0,
            'journal_id': self.cash_journal.id,
            'payment_date': fields.Date.today(),
            'line_ids': invoice.line_ids.filtered(lambda line: line.display_type == 'payment_term'),
        })._create_payments()
        self.assertEqual(invoice.payment_state, 'paid')
        self.assertEqual(len(invoice._get_reconciled_payments()), 2)

        # 4. Render XML
        xml = invoice._l10n_pl_edi_render_xml()

        # Expectation: ZnacznikZaplatyCzesciowej is 2 because invoice is fully paid
        self.assertEqual(
            self._get_xml_value(xml, "//ns:Platnosc/ns:ZnacznikZaplatyCzesciowej"),
            '2',
            "ZnacznikZaplatyCzesciowej should be 2 when fully paid (even with multiple payments)"
        )

        # Expectation: ZaplataCzesciowa nodes SHOULD be present for both payments
        payment_nodes = self._get_xml_nodes(xml, "//ns:Platnosc/ns:ZaplataCzesciowa")
        self.assertEqual(len(payment_nodes), 2, "Should list history of both payments")

        # Optional: Verify amounts in the history
        amounts = sorted([n.find('ns:KwotaZaplatyCzesciowej', namespaces={'ns': 'http://crd.gov.pl/wzor/2025/06/25/13775/'}).text for n in payment_nodes])
        self.assertEqual(amounts, ['400.00', '600.00'])

    def test_payment_bank_account_details(self):
        """
        Test that RachunekBankowy is generated when a partner_bank_id is set on the invoice.
        """
        # Create a Bank Account for the Company
        bank_acc = self.env['res.partner.bank'].create({
            'acc_number': '12 3456 7890 0000 0000 1234 5678',
            'partner_id': self.partner_pl.id,
            'bank_id': self.env['res.bank'].create({'name': 'Test Bank PL'}).id,
            'allow_out_payment': True,
        })

        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_pl.id,
            'invoice_date': fields.Date.today(),
            'partner_bank_id': bank_acc.id,
            'invoice_line_ids': [Command.create({'product_id': self.product_a.id, 'price_unit': 100.0})],
        })
        invoice.action_post()

        self.env['account.payment.register'].create({
            'amount': 10.0,
            'journal_id': self.cash_journal.id,
            'line_ids': invoice.line_ids.filtered(lambda line: line.display_type == 'payment_term'),
        })._create_payments()

        xml = invoice._l10n_pl_edi_render_xml()

        expected_acc = '12345678900000000012345678'
        self.assertEqual(self._get_xml_value(xml, "//ns:Platnosc/ns:RachunekBankowy/ns:NrRB"), expected_acc)
        self.assertEqual(self._get_xml_value(xml, "//ns:Platnosc/ns:RachunekBankowy/ns:NazwaBanku"), 'Test Bank PL')

    @freeze_time('2026-01-23')
    def test_payment_terms_structure(self):
        """
        Test the <TerminPlatnosci> block logic.

        Scenario:
        1. Create a custom Payment Term: "45 Days after End of Month".
        2. Create an Invoice using this term.
        3. Verify the XML output contains:
           - Termin: The calculated due date.
           - Ilosc: 45
           - Jednostka: Dni
           - ZdarzeniePoczatkowe: Koniec miesiąca
        """
        # 1. Create Custom Payment Term (45 Days After End of Month)
        pay_term = self.env['account.payment.term'].create({
            'name': '45 Days EOM',
            'line_ids': [
                Command.create({
                    'value': 'percent',
                    'value_amount': 100.0,
                    'nb_days': 45,
                    'delay_type': 'days_after_end_of_month',
                })
            ]
        })

        # 2. Create Invoice with this Payment Term
        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_pl.id,
            'invoice_date': fields.Date.today(),
            'invoice_payment_term_id': pay_term.id,
            'invoice_line_ids': [Command.create({
                'product_id': self.product_a.id,
                'price_unit': 100.0
            })],
        })
        invoice.action_post()
        self.env['account.payment.register'].create({
            'amount': 100.0,
            'journal_id':  self.cash_journal.id,
            'line_ids': invoice.line_ids.filtered(lambda line: line.display_type == 'payment_term'),
        })._create_payments()
        self.assertEqual(invoice.payment_state, 'partial')

        # 3. Render XML
        xml = invoice._l10n_pl_edi_render_xml()
        expected_date = str(invoice.invoice_date_due)
        self.assertEqual(
            self._get_xml_value(xml, "//ns:Platnosc/ns:TerminPlatnosci/ns:Termin"),
            expected_date,
            "Termin should match the invoice due date"
        )

        # Check TerminOpis (Structured Description)
        # Ilosc (Quantity)
        self.assertEqual(
            self._get_xml_value(xml, "//ns:Platnosc/ns:TerminPlatnosci/ns:TerminOpis/ns:Ilosc"),
            '45',
            "Ilosc should be 45"
        )

        # Jednostka (Unit)
        self.assertEqual(
            self._get_xml_value(xml, "//ns:Platnosc/ns:TerminPlatnosci/ns:TerminOpis/ns:Jednostka"),
            'Dni',
            "Jednostka should be Dni"
        )

    @freeze_time('2026-01-23')
    def test_scenario_correction_values_are_negative(self):
        """
        Verification of Negative Values for Corrections (Difference Method).

        This test ensures that when a Credit Note (KOR) is generated:
        1. Quantity (P_8B) is NEGATIVE.
        2. Net Amount (P_11) is NEGATIVE.
        3. Unit Price (P_9A) is POSITIVE.
        """
        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_pl.id,
            'invoice_date': fields.Date.today(),
            'currency_id': self.env.ref('base.PLN').id,
            'invoice_line_ids': [Command.create({
                'product_id': self.product_a.id,
                'quantity': 10,
                'price_unit': 100.0,
            })],
        })
        invoice.action_post()
        reversal_wizard = self.env['account.move.reversal'].create({
            'reason': 'Return of goods',
            'journal_id': invoice.journal_id.id,
            'move_ids': invoice.ids,
        })
        reversal_wizard.refund_moves()

        credit_note = invoice.reversal_move_ids
        credit_note.action_post()

        xml = credit_note._l10n_pl_edi_render_xml()
        self.assertEqual(self._get_xml_value(xml, "//ns:RodzajFaktury"), 'KOR')

        p_8b = self._get_xml_value(xml, "//ns:Fa/ns:FaWiersz/ns:P_8B")
        self.assertEqual(float(p_8b), -10.0, "Quantity (P_8B) must be negative for corrections")

        p_11 = self._get_xml_value(xml, "//ns:Fa/ns:FaWiersz/ns:P_11")
        self.assertEqual(float(p_11), -1000.0, "Net Amount (P_11) must be negative for corrections")

        p_9a = self._get_xml_value(xml, "//ns:Fa/ns:FaWiersz/ns:P_9A")
        self.assertEqual(float(p_9a), 100.0, "Unit Price (P_9A) must remain positive")

    def l10n_pl_edi_generate_attachments(self, invoices, from_cron=False):
        moves_data = {
            invoice: self.env['account.move.send']._get_default_sending_settings(invoice, from_cron=from_cron)
            for invoice in invoices
        }
        with patch('odoo.addons.l10n_pl_edi.models.account_move_send.AccountMoveSend._call_web_service_before_invoice_pdf_render'):
            self.env['account.move.send']._generate_invoice_documents(moves_data)

    def test_l10n_pl_edi_send_success(self):
        invoice = self.standard_invoice
        invoice.action_post()
        with (
            patch.object(KsefApiService, 'open_ksef_session') as mock_open_session,
            patch.object(KsefApiService, 'send_invoice', return_value={'referenceNumber': '999999'}) as mock_send
        ):
            wizard = self.env['account.move.send.wizard'].with_company(self.company).create({
                'move_id': invoice.id,
                'extra_edi_checkboxes': {'pl_ksef': {'checked': True}}
            })
            wizard.action_send_and_print()
            self.assertEqual(mock_open_session.call_count, 1)
            self.assertEqual(mock_send.call_count, 1)
        self.assertEqual(invoice.l10n_pl_edi_status, 'sent')
        self.assertEqual(invoice.l10n_pl_edi_session_id, invoice.company_id.l10n_pl_edi_session_id)
        self.assertEqual(invoice.l10n_pl_edi_ref, '999999')
        self.assertEqual(invoice.l10n_pl_edi_attachment_id.name, 'FA3-INV_2026_00001.xml')

    def test_l10n_pl_edi_send_api_error(self):
        invoice = self.standard_invoice
        invoice.action_post()

        def send_invoice_raise(xml_content):
            raise Exception("turlututu")

        with (
            patch.object(KsefApiService, 'open_ksef_session') as mock_open_session,
            patch.object(KsefApiService, 'send_invoice', side_effect=send_invoice_raise) as mock_send,
            self.assertRaises(UserError),
        ):
            wizard = self.env['account.move.send.wizard'].with_company(self.company).create({
                'move_id': invoice.id,
                'extra_edi_checkboxes': {'pl_ksef': {'checked': True}}
            })
            wizard.action_send_and_print()
        self.assertEqual(mock_open_session.call_count, 1)
        self.assertEqual(mock_send.call_count, 1)
        self.assertEqual(invoice.l10n_pl_edi_status, False)
        self.assertEqual(invoice.l10n_pl_edi_session_id, False)
        self.assertEqual(invoice.l10n_pl_edi_ref, False)
        self.assertEqual(invoice.l10n_pl_edi_attachment_id.name, False)

    def test_l10n_pl_edi_download_bill_success(self):

        def query_invoice_metadata(query_criteria, page_size=100, page_offset=0):
            return {
                'hasMore': False,
                'invoices': [
                    {
                        'acquisitionDate': '2026-02-10T10:50:29.348439+00:00',
                        'buyer': {'identifier': {'type': 'Nip', 'value': '5795955811'}, 'name': 'PL Company'},
                        'currency': 'PLN',
                        'formCode': {'schemaVersion': '1-0E', 'systemCode': 'FA (3)', 'value': 'FA'},
                        'hasAttachment': False,
                        'invoiceHash': 'DOFApZsfUkl3BLgW1nd7frNq4IVHvYoXHEudpyCFbpg=',
                        'invoiceNumber': 'FV/2026/00001-demo-test-005',
                        'invoiceType': 'Vat',
                        'invoicingDate': '2026-02-10T10:50:29.189345+00:00',
                        'invoicingMode': 'Online',
                        'isSelfInvoicing': False,
                        'issueDate': '2026-02-10',
                        'ksefNumber': '7492091229-20260210-0700A043714A-5E',
                        'permanentStorageDate': '2026-02-10T10:50:30.40494+00:00',
                        'seller': {'name': 'HADRON FOR BUSINESS SP Z O O', 'nip': '7492091229'},
                    },
                ],
            }

        def get_invoice_by_ksef_number(ksef_number):
            path = 'l10n_pl_edi/tests/export_xmls/fa3_bill.xml'
            with tools.file_open(path, mode='rb') as file:
                return {'xml_content': file.read()}

        with (
            patch.object(KsefApiService, 'query_invoice_metadata', side_effect=query_invoice_metadata),
            patch.object(KsefApiService, 'get_invoice_by_ksef_number', side_effect=get_invoice_by_ksef_number),
        ):
            self.env['account.move'].with_company(self.company)._l10n_pl_edi_download_bills_from_ksef()

        created_move = self.env['account.move'].search([('l10n_pl_edi_number', '=', '7492091229-20260210-0700A043714A-5E')])
        self.assertTrue(created_move)
        self.assertEqual(created_move.partner_id.vat, '7492091229')
        self.assertEqual(len(created_move), 1)
        self.assertRecordValues(
            created_move, [
                {
                    'state': 'draft',
                    'move_type': 'in_invoice',
                    'invoice_date': fields.Date.to_date('2026-02-10'),
                    'invoice_date_due': fields.Date.to_date('2026-02-10'),
                    'ref': 'FV/2026/00001-demo-test-005',
                    'currency_id': self.env['res.currency'].search([('name', '=', 'PLN')]).id,
                },
            ],
        )
        self.assertRecordValues(
            created_move.invoice_line_ids, [
                {
                    'name': "[FURN_0006] Podstawka pod monitor",
                    'quantity': 1.0,
                    'price_unit': 3.19,
                },
                {
                    'name': "[FOOD_0001] Chleb pszenny",
                    'quantity': 2.5,
                    'price_unit': 5.00,
                },
                {
                    'name': "[BOOK_0001] Podręcznik szkolny",
                    'quantity': 4.0,
                    'price_unit': 5.00,
                },
            ],
        )

        self.assertEqual(
            created_move.invoice_line_ids.tax_ids.ids,
            self.env['account.tax'].search(
                [
                    ('name', 'in', ('23% G', '8%', '5%')),
                    ('type_tax_use', '=', 'purchase'),
                    *self.env['account.tax']._check_company_domain(self.company),
                ],
            ).ids,
        )

    def test_l10n_pl_edi_download_bill_retry_after(self):
        """Test that when a rate limit error occurs the progress is preserved and the cron is rescheduled."""

        def query_invoice_metadata(query_criteria, page_size=100, page_offset=0):
            return {
                'hasMore': False,
                'invoices': [
                    {
                        'ksefNumber': 'KSEF-BILL-001',
                    },
                    {
                        'ksefNumber': 'KSEF-BILL-002',
                    },
                ],
            }

        call_count = 0

        def get_invoice_by_ksef_number(ksef_number):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                path = 'l10n_pl_edi/tests/export_xmls/fa3_bill.xml'
                with tools.file_open(path, mode='rb') as file:
                    return {'xml_content': file.read()}
            return {'error': {'retry_after': 120, 'message': 'Too Many Requests'}}

        with (
            patch.object(KsefApiService, 'query_invoice_metadata', side_effect=query_invoice_metadata),
            patch.object(KsefApiService, 'get_invoice_by_ksef_number', side_effect=get_invoice_by_ksef_number),
            self.capture_triggers() as capt,
        ):
            cron_runs_before = len(capt.records)
            self.env['account.move'].with_company(self.company)._l10n_pl_edi_download_bills_from_ksef()

        bill_1 = self.env['account.move'].search([('l10n_pl_edi_number', '=', 'KSEF-BILL-001')])
        self.assertTrue(bill_1)

        bill_2 = self.env['account.move'].search([('l10n_pl_edi_number', '=', 'KSEF-BILL-002')])
        self.assertFalse(bill_2)

        self.assertEqual(len(capt.records), cron_runs_before + 1)
        self.assertGreaterEqual(capt.records[-1].call_at, fields.Datetime.now() + timedelta(seconds=120))
        self.assertLessEqual(capt.records[-1].call_at, fields.Datetime.now() + timedelta(seconds=240))
