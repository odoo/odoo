from collections import Counter
from unittest.mock import patch

from lxml import etree

from odoo import fields
from odoo.addons.l10n_fr_pdp.tests.common import TestL10nFrPdpCommon
from odoo.tests import tagged
from odoo.tools import file_open


@tagged('post_install', '-at_install', 'test_flow_lifecycle')
class TestPdpReportsFlowLifecycle(TestL10nFrPdpCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.company = cls.company_data['company']

        cls.proxy_user.company_id = cls.company
        cls.company.write({
            'account_fiscal_country_id': cls.env.ref('base.fr').id,
            'country_id': cls.env.ref('base.fr').id,
            'currency_id': cls.env.ref('base.EUR').id,
            'email': 'info@company.frexample.com',
            'l10n_fr_pdp_annuaire_start_date': '2025-01-01',
            'l10n_fr_pdp_periodicity': 'normal_monthly',
            'l10n_fr_pdp_pilot_phase': True,
            'l10n_fr_pdp_send_to_ppf': True,
            'name': 'NOM MATELAS',
            'siret': '34057796400024',
            'vat': 'FR23334175221',
        })
        cls.company.invalidate_recordset([
            'account_peppol_edi_user',
            'l10n_fr_f10_enable_reporting',
        ])
        cls.company._compute_account_peppol_edi_user()
        cls.company._compute_l10n_fr_f10_enable_reporting()
        cls.env.flush_all()
        if not cls.company.l10n_fr_f10_enable_reporting:
            raise AssertionError("The test company must be eligible for Flux 10 reporting.")

        cls.b2c_customer = cls.env['res.partner'].create({
            'name': 'PDP B2C Customer',
            'street': '1 rue du Client',
            'zip': '75001',
            'city': 'Paris',
            'country_id': cls.env.ref('base.fr').id,
        })
        cls.domestic_b2b_partner = cls.env['res.partner'].with_context(no_vat_validation=True).create({
            'name': 'PDP Domestic B2B Partner',
            'street': '5 rue du Fournisseur',
            'zip': '75002',
            'city': 'Paris',
            'country_id': cls.env.ref('base.fr').id,
            'vat': 'FR40303265045',
        })
        cls.b2bi_customer = cls.env['res.partner'].create({
            'name': 'PDP B2BI Customer',
            'street': 'Rue du Paradis, 10',
            'zip': '6870',
            'city': 'Eghezee',
            'country_id': cls.env.ref('base.be').id,
            'vat': 'BE0477472701',
        })
        cls.b2bi_italian_customer = cls.env['res.partner'].with_context(no_vat_validation=True).create({
            'name': 'PDP Italian B2BI Customer',
            'street': 'Via Francesco Crispi 226',
            'zip': '90139',
            'city': 'Palermo',
            'country_id': cls.env.ref('base.it').id,
            'vat': 'IT04119190371',
        })

    def _get_tax_on_payment(self):
        return self.env['account.chart.template'].ref('tva_sale_service_0')

    def _get_tax_on_payment_20(self):
        return self.env['account.chart.template'].ref('tva_normale_encaissement')

    def _get_tax_sale_good_intra_0(self):
        return self.env['account.chart.template'].ref('tva_sale_good_intra_0')

    def _get_tax_sale_service_intra_0(self):
        return self.env['account.chart.template'].ref('tva_sale_service_intra_0')

    def _get_tax_sale_good_20_tax_included(self):
        return self.env['account.chart.template'].ref('tva_normale_ttc')

    def _get_tax_on_payment_20_tax_included(self):
        return self.env['account.chart.template'].ref('tva_normale_encaissement_ttc')

    def _get_purchase_tax_on_payment(self):
        return self.env['account.chart.template'].ref('tva_acq_encaissement')

    def _create_reporting_move(
        self,
        move_type,
        partner,
        amount=100.0,
        invoice_date='2025-02-05',
        name=None,
        sent=True,
        tax_ids=None,
        total_amount=False,
        currency=None,
        invoice_date_due=None,
    ):
        invoice_date = fields.Date.to_date(invoice_date)
        move = self._create_invoice_one_line(
            move_type=move_type,
            partner_id=partner,
            product_id=self.product_a,
            price_unit=amount,
            quantity=1.0,
            tax_ids=tax_ids,
            currency_id=currency,
            invoice_date=invoice_date,
            invoice_date_due=fields.Date.to_date(invoice_date_due) if invoice_date_due else None,
            date=invoice_date,
            post=False,
        )
        if name:
            move.name = name
        move.action_post()
        if move.is_sale_document(include_receipts=True):
            move.is_move_sent = sent
        self._refresh_pdp_fields(move)
        return move

    def _create_reporting_invoice_with_lines(
        self,
        partner,
        lines,
        invoice_date='2025-02-05',
        invoice_date_due=None,
        name=None,
        sent=True,
    ):
        invoice_date = fields.Date.to_date(invoice_date)
        invoice = self._create_invoice(
            move_type='out_invoice',
            partner_id=partner,
            invoice_date=invoice_date,
            date=invoice_date,
            invoice_line_ids=[
                self._prepare_invoice_line(
                    product_id=line.get('product_id', self.product_a),
                    price_unit=line['price_unit'],
                    quantity=line.get('quantity', 1.0),
                    tax_ids=line.get('tax_ids'),
                )
                for line in lines
            ],
            post=False,
            invoice_date_due=fields.Date.to_date(invoice_date_due) if invoice_date_due else None,
        )
        if name:
            invoice.name = name
        invoice.action_post()
        invoice.is_move_sent = sent
        self._refresh_pdp_fields(invoice)
        return invoice

    def _create_reporting_invoice(
        self,
        partner,
        amount=100.0,
        invoice_date='2025-02-05',
        name=None,
        sent=True,
        tax_ids=None,
        total_amount=False,
        currency=None,
        invoice_date_due=None,
    ):
        return self._create_reporting_move(
            'out_invoice',
            partner,
            amount=amount,
            invoice_date=invoice_date,
            name=name,
            sent=sent,
            tax_ids=tax_ids or self._get_tax_on_payment(),
            total_amount=total_amount,
            currency=currency,
            invoice_date_due=invoice_date_due,
        )

    def _create_reporting_vendor_bill(
        self,
        partner=None,
        amount=100.0,
        invoice_date='2025-02-05',
        name=None,
        currency=None,
    ):
        return self._create_reporting_move(
            'in_invoice',
            partner or self.b2bi_customer,
            amount=amount,
            invoice_date=invoice_date,
            name=name,
            tax_ids=self._get_purchase_tax_on_payment(),
            currency=currency,
        )

    def _refresh_pdp_fields(self, move):
        self.env.flush_all()
        move.company_id.invalidate_recordset([
            'account_peppol_edi_user',
            'l10n_fr_f10_enable_reporting',
        ])
        move.company_id._compute_account_peppol_edi_user()
        move.company_id._compute_l10n_fr_f10_enable_reporting()
        move.invalidate_recordset([
            'l10n_fr_pdp_has_error',
            'l10n_fr_pdp_is_flow_10_report_type',
            'l10n_fr_pdp_is_flow_10_operation_type',
            'l10n_fr_pdp_last_flow_id',
            'l10n_fr_pdp_status',
            'l10n_fr_pdp_error_message',
        ])

    def _register_payment(self, invoices, payment_date, amount=None, group_payment=True, currency=None):
        payment_vals = {
            'group_payment': group_payment,
            'journal_id': self.company_data['default_journal_bank'].id,
            'payment_date': fields.Date.to_date(payment_date),
        }
        if amount is not None:
            payment_vals['amount'] = amount
        if currency:
            payment_vals['currency_id'] = currency.id
        payment = self.env['account.payment.register'].with_context(
            active_model='account.move',
            active_ids=invoices.ids,
        ).create(payment_vals)._create_payments()
        self._refresh_pdp_fields(payment.move_id)
        return payment

    def _create_unreconciled_customer_payment(self, invoice, payment_date, amount=None):
        journal = self.company_data['default_journal_bank']
        method_line = (
            journal.inbound_payment_method_line_ids.filtered(lambda line: line.code == 'manual')[:1]
            or journal.inbound_payment_method_line_ids[:1]
        )
        self.assertTrue(method_line)
        if not method_line.payment_account_id:
            method_line.payment_account_id = journal.default_account_id or self.company_data['default_account_assets']
        payment = self.env['account.payment'].create({
            'payment_type': 'inbound',
            'partner_type': 'customer',
            'partner_id': invoice.partner_id.id,
            'amount': amount or invoice.amount_total,
            'date': fields.Date.to_date(payment_date),
            'journal_id': journal.id,
            'payment_method_line_id': method_line.id,
        })
        payment.action_post()
        self._refresh_pdp_fields(payment.move_id)
        return payment

    def _proxy_success_response(self, identifier='FLOW-TEST-001'):
        return {
            'id': identifier,
            'flow_id': identifier,
            'status': 'DRAFT',
            'message': '',
            'acknowledgement': [],
        }

    def _run_send_cron(self, date, identifier='FLOW-TEST-001'):
        with patch('odoo.fields.Date.today', return_value=fields.Date.to_date(date)):
            with patch(
                'odoo.addons.l10n_fr_pdp_reports.models.pdp_flow.PdpFlow._send_to_proxy',
                return_value=self._proxy_success_response(identifier),
            ):
                self.env['l10n.fr.pdp.reports.flow']._cron_process_company(self.company)

<<<<<<< HEAD
    def _build_flow_xml(self, flow, moves=None):
        flow._build_payload(moves)
=======
    def _create_sent_flow_for_scope(self, report_type, operation_type, date, name):
        period_data = self.env['l10n.fr.pdp.reports.flow']._get_period_flow_properties(
            self.company,
            fields.Date.to_date(date),
            report_type,
        )
        return self.env['l10n.fr.pdp.reports.flow'].create({
            **period_data,
            'company_id': self.company.id,
            'name': name,
            'operation_type': operation_type,
            'report_type': report_type,
            'state': 'sent',
        })

    def _build_flow_xml(self, flow):
        flow._build_payload()
>>>>>>> 3e1cf322fbb4 ([IMP] l10n_fr_pdp_reports: add e-reporting tests)
        self.assertTrue(flow.payload_id)
        return etree.fromstring(flow.payload_id.raw)

    def _load_expected_report_xml(self, filename):
        with file_open(f'l10n_fr_pdp_reports/tests/data/{filename}', 'rb', filter_ext=('.xml',)) as report_file:
            return etree.fromstring(report_file.read())

    def _ignore_runtime_report_values(self, xml):
        for xpath in (
            './ReportDocument/Id',
            './ReportDocument/IssueDateTime/DateTimeString',
            './TransactionsReport/Invoice/Seller/TaxRegistrationId',
        ):
            for node in xml.findall(xpath):
                node.text = '___ignore___'
        return xml

    def _assert_identification_nodes(self, actual_xml, expected_xml):
        for xpath in (
            './ReportDocument/Sender/Id',
            './ReportDocument/Issuer/Id',
            './TransactionsReport/Invoice/Seller/CompanyId',
            './TransactionsReport/Invoice/Buyer/CompanyId',
        ):
            actual_nodes = actual_xml.findall(xpath)
            expected_nodes = expected_xml.findall(xpath)
            if not actual_nodes and not expected_nodes:
                continue

            self.assertEqual(
                len(actual_nodes),
                len(expected_nodes),
                f'Unexpected number of identification nodes for {xpath}',
            )
            for index, (actual_node, expected_node) in enumerate(zip(actual_nodes, expected_nodes)):
                self.assertEqual(
                    actual_node.get('schemeId'),
                    expected_node.get('schemeId'),
                    f'Wrong schemeId for {xpath}[{index}]',
                )
                self.assertEqual(
                    actual_node.text,
                    expected_node.text,
                    f'Wrong identifier value for {xpath}[{index}]',
                )

    def _assert_flow_matches_report_fixture(self, flow, filename):
        actual_xml = self._build_flow_xml(flow)
        expected_xml = self._ignore_runtime_report_values(self._load_expected_report_xml(filename))
        self._assert_identification_nodes(actual_xml, expected_xml)
        self.assertXmlTreeEqual(actual_xml, expected_xml)

    def test_no_activity_does_not_create_flow(self):
        period_data = self.env['l10n.fr.pdp.reports.flow']._get_period_flow_properties(
            self.company,
            fields.Date.to_date('2035-01-15'),
            'transaction',
        )
        flows = self.env['l10n.fr.pdp.reports.flow'].search([
            ('company_id', '=', self.company.id),
            ('period_start', '=', period_data['period_start']),
            ('period_end', '=', period_data['period_end']),
            ('report_type', '=', 'transaction'),
        ])

        self.assertFalse(flows)

    def test_transaction_flow_matches_reserve_fixture_0290(self):
        self.company.l10n_fr_pdp_periodicity = 'normal_quarterly'
        b2bi_invoice_1 = self._create_reporting_invoice(
            partner=self.b2bi_italian_customer,
            amount=10000.0,
            invoice_date='2025-09-01',
            invoice_date_due='2025-09-30',
            name='S1F1_REPORT2025',
            tax_ids=self._get_tax_sale_service_intra_0(),
        )
        b2bi_invoice_2 = self._create_reporting_invoice(
            partner=self.b2bi_italian_customer,
            amount=200000.0,
            invoice_date='2025-09-01',
            invoice_date_due='2025-09-30',
            name='S1F2_REPORT2025',
            tax_ids=self._get_tax_sale_service_intra_0(),
        )
        b2c_invoice_1 = self._create_reporting_invoice(
            partner=self.b2c_customer,
            amount=12000.0,
            invoice_date='2025-09-16',
            name='B2C_TRANSACTION_1',
            tax_ids=self._get_tax_on_payment_20_tax_included(),
            total_amount=True,
        )
        b2c_invoice_2 = self._create_reporting_invoice(
            partner=self.b2c_customer,
            amount=12000.0,
            invoice_date='2025-09-22',
            name='B2C_TRANSACTION_2',
            tax_ids=self._get_tax_sale_good_20_tax_included(),
            total_amount=True,
        )
        moves = b2bi_invoice_1 | b2bi_invoice_2 | b2c_invoice_1 | b2c_invoice_2
        flow = moves.mapped('l10n_fr_pdp_last_flow_id')

        self.assertEqual(len(flow), 1)
        self._assert_flow_matches_report_fixture(
            flow,
            'FFE1025A_PPF262_PPF2621025000000000000290.xml',
        )

    def test_b2c_invoice_creates_transaction_flow_payload(self):
        invoice = self._create_reporting_invoice(
            partner=self.b2c_customer,
        )

        self.assertRecordValues(invoice, [{
            'l10n_fr_pdp_is_flow_10_report_type': 'transaction',
            'l10n_fr_pdp_is_flow_10_operation_type': 'sale',
            'l10n_fr_pdp_status': 'pending',
        }])
        flow = invoice.l10n_fr_pdp_last_flow_id
        self.assertRecordValues(flow, [{
            'report_type': 'transaction',
            'operation_type': 'sale',
            'state': 'ready',
        }])
        self.env.flush_all()
        flow.invalidate_recordset(['move_ids'])
        self.assertIn(invoice, flow.move_ids)

        xml = self._build_flow_xml(flow)
        self.assertEqual(xml.tag, 'Report')
        self.assertEqual(xml.findtext('./ReportDocument/TypeCode'), 'IN')

        transactions = xml.findall('./TransactionsReport/Transactions')
        self.assertEqual(len(transactions), 1)
        self.assertEqual(transactions[0].findtext('CategoryCode'), 'TNT1')
        self.assertEqual(transactions[0].findtext('TransactionsCurrency'), invoice.currency_id.name)

    def test_b2c_service_on_debits_reports_tax_due_date_type_code(self):
        service_tax_on_debits = self._get_tax_on_payment_20_tax_included().copy({
            'name': '20% Service on debits',
            'tax_exigibility': 'on_invoice',
        })
        invoice = self._create_reporting_invoice(
            partner=self.b2c_customer,
            tax_ids=service_tax_on_debits,
        )

        xml = self._build_flow_xml(invoice.l10n_fr_pdp_last_flow_id)
        transaction = xml.find('./TransactionsReport/Transactions')
        self.assertEqual(transaction.findtext('CategoryCode'), 'TPS1')
        self.assertEqual(transaction.findtext('TaxDueDateTypeCode'), '3')

    def test_b2c_invoice_without_taxes_creates_transaction_flow(self):
        invoice = self._create_reporting_invoice(
            partner=self.b2c_customer,
            tax_ids=self.env['account.tax'],
        )

        self.assertRecordValues(invoice, [{
            'l10n_fr_pdp_flow_10_report_type': 'transaction',
            'l10n_fr_pdp_flow_10_operation_type': 'sale',
            'l10n_fr_pdp_status': 'pending',
        }])
        self.assertTrue(invoice.l10n_fr_pdp_last_flow_id)

    def test_b2c_invoice_not_sent_is_in_error(self):
        invoice = self._create_reporting_invoice(
            partner=self.b2c_customer,
            sent=False,
        )

        self.assertFalse(invoice.is_move_sent)
        self.assertRecordValues(invoice, [{
            'l10n_fr_pdp_is_flow_10_report_type': 'transaction',
            'l10n_fr_pdp_is_flow_10_operation_type': 'sale',
            'l10n_fr_pdp_has_error': True,
            'l10n_fr_pdp_status': 'error',
        }])
        self.assertIn(
            "Invoice/credit note has not been sent to the customer.",
            invoice.l10n_fr_pdp_error_message or '',
        )

    def test_b2bi_invoice_creates_transaction_flow_payload(self):
        invoice = self._create_reporting_invoice(partner=self.b2bi_customer)

        self.assertTrue(invoice.is_move_sent)
        self.assertRecordValues(invoice, [{
            'l10n_fr_pdp_is_flow_10_report_type': 'transaction',
            'l10n_fr_pdp_is_flow_10_operation_type': 'sale',
            'l10n_fr_pdp_status': 'pending',
        }])
        flow = invoice.l10n_fr_pdp_last_flow_id
        self.assertRecordValues(flow, [{
            'report_type': 'transaction',
            'operation_type': 'sale',
            'state': 'ready',
        }])
        flow.invalidate_recordset(['move_ids'])
        self.assertIn(invoice, flow.move_ids)

        xml = self._build_flow_xml(flow)
        invoices = xml.findall('./TransactionsReport/Invoice')
        transactions = xml.findall('./TransactionsReport/Transactions')
        self.assertEqual(len(invoices), 1)
        self.assertEqual(len(transactions), 0)
        self.assertEqual(invoices[0].findtext('ID'), invoice.name)
        self.assertEqual(invoices[0].findtext('CurrencyCode'), invoice.currency_id.name)

    def test_b2bi_service_on_debits_reports_tax_due_date_type_code(self):
        service_tax_on_debits = self._get_tax_on_payment_20_tax_included().copy({
            'name': '20% Service on debits',
            'tax_exigibility': 'on_invoice',
        })
        invoice = self._create_reporting_invoice(
            partner=self.b2bi_customer,
            tax_ids=service_tax_on_debits,
        )

        xml = self._build_flow_xml(invoice.l10n_fr_pdp_last_flow_id)
        invoice_node = xml.find('./TransactionsReport/Invoice')
        self.assertEqual(invoice_node.findtext('TaxDueDateTypeCode'), '5')

    def test_b2bi_invoice_not_sent_is_in_error(self):
        invoice = self._create_reporting_invoice(
            partner=self.b2bi_customer,
            sent=False,
        )

        self.assertFalse(invoice.is_move_sent)
        self.assertRecordValues(invoice, [{
            'l10n_fr_pdp_is_flow_10_report_type': 'transaction',
            'l10n_fr_pdp_is_flow_10_operation_type': 'sale',
            'l10n_fr_pdp_has_error': True,
            'l10n_fr_pdp_status': 'error',
        }])
        self.assertIn(
            "Invoice/credit note has not been sent to the customer.",
            invoice.l10n_fr_pdp_error_message or '',
        )

    def test_domestic_b2b_invoice_stays_out_of_scope(self):
        invoice = self._create_reporting_invoice(
            partner=self.domestic_b2b_partner,
            name='DOMESTIC_B2B_OUT_OF_SCOPE',
        )

        self.assertRecordValues(invoice, [{
<<<<<<< HEAD
            'l10n_fr_pdp_is_flow_10_report_type': False,
            'l10n_fr_pdp_is_flow_10_operation_type': False,
=======
            'l10n_fr_pdp_flow_10_report_type': False,
>>>>>>> 3e1cf322fbb4 ([IMP] l10n_fr_pdp_reports: add e-reporting tests)
            'l10n_fr_pdp_status': 'out_of_scope',
        }])
        self.assertFalse(invoice.l10n_fr_pdp_last_flow_id)

    def test_domestic_vendor_bill_stays_out_of_scope(self):
        bill = self._create_reporting_vendor_bill(
            partner=self.domestic_b2b_partner,
            name='DOMESTIC_VENDOR_BILL_OUT_OF_SCOPE',
        )

        self.assertRecordValues(bill, [{
<<<<<<< HEAD
            'l10n_fr_pdp_is_flow_10_report_type': False,
            'l10n_fr_pdp_is_flow_10_operation_type': False,
=======
            'l10n_fr_pdp_flow_10_report_type': False,
>>>>>>> 3e1cf322fbb4 ([IMP] l10n_fr_pdp_reports: add e-reporting tests)
            'l10n_fr_pdp_status': 'out_of_scope',
        }])
        self.assertFalse(bill.l10n_fr_pdp_last_flow_id)

    def test_international_vendor_bill_creates_purchase_transaction_flow(self):
        bill = self._create_reporting_vendor_bill(
            partner=self.b2bi_customer,
            invoice_date='2025-09-03',
            name='INTERNATIONAL_VENDOR_BILL',
        )

        self.assertRecordValues(bill, [{
            'l10n_fr_pdp_is_flow_10_report_type': 'transaction',
            'l10n_fr_pdp_is_flow_10_operation_type': 'purchase',
            'l10n_fr_pdp_status': 'pending',
        }])
        flow = bill.l10n_fr_pdp_last_flow_id
        self.assertRecordValues(flow, [{
            'report_type': 'transaction',
            'operation_type': 'purchase',
            'state': 'ready',
        }])
        flow.invalidate_recordset(['move_ids'])
        self.assertIn(bill, flow.move_ids)

        xml = self._build_flow_xml(flow)
        self.assertEqual(xml.findtext('./ReportDocument/Issuer/RoleCode'), 'BY')
        invoices = xml.findall('./TransactionsReport/Invoice')
        self.assertEqual(len(invoices), 1)
        self.assertEqual(invoices[0].findtext('ID'), bill.name)

    def test_mixed_b2c_b2bi_invoices_create_transaction_flow_payload(self):
        b2c_invoice = self._create_reporting_invoice(partner=self.b2c_customer)
        b2bi_invoice = self._create_reporting_invoice(partner=self.b2bi_customer)

        self.assertEqual(b2c_invoice.l10n_fr_pdp_last_flow_id, b2bi_invoice.l10n_fr_pdp_last_flow_id)
        flow = b2c_invoice.l10n_fr_pdp_last_flow_id

        self.env.flush_all()
        flow.invalidate_recordset(['move_ids'])
        self.assertIn(b2c_invoice, flow.move_ids)
        self.assertIn(b2bi_invoice, flow.move_ids)

        xml = self._build_flow_xml(flow)
        invoices = xml.findall('./TransactionsReport/Invoice')
        transactions = xml.findall('./TransactionsReport/Transactions')
        self.assertEqual(len(invoices), 1)
        self.assertEqual(len(transactions), 1)
        self.assertEqual(invoices[0].findtext('ID'), b2bi_invoice.name)
        self.assertEqual(transactions[0].findtext('CategoryCode'), 'TNT1')

    def test_payment_reconciliation_creates_payment_flow(self):
        invoice = self._create_reporting_invoice(
            partner=self.b2bi_customer,
            amount=100.0,
            invoice_date='2025-09-03',
            name='S2F3_REPORT2025',
        )

        payment = self._register_payment(invoice, '2025-09-03')
        payment_move = payment.move_id

        self.assertRecordValues(payment_move, [{
            'l10n_fr_pdp_is_flow_10_report_type': 'payment',
            'l10n_fr_pdp_is_flow_10_operation_type': 'sale',
            'l10n_fr_pdp_status': 'pending',
        }])
        flow = payment_move.l10n_fr_pdp_last_flow_id
        self.assertRecordValues(flow, [{
            'report_type': 'payment',
            'operation_type': 'sale',
            'state': 'ready',
        }])

    def test_unreconciled_payment_is_excluded_from_payment_flow(self):
        invoice = self._create_reporting_invoice(
            partner=self.b2bi_customer,
            amount=100.0,
            invoice_date='2025-09-03',
            name='UNRECONCILED_PAYMENT_INVOICE',
        )

        payment = self._create_unreconciled_customer_payment(invoice, '2025-09-03')
        payment_move = payment.move_id

        self.assertRecordValues(payment_move, [{
            'l10n_fr_pdp_is_flow_10_report_type': False,
            'l10n_fr_pdp_is_flow_10_operation_type': False,
            'l10n_fr_pdp_status': 'out_of_scope',
        }])
        self.assertFalse(payment_move.l10n_fr_pdp_last_flow_id)

    def test_partial_payment_reports_only_reconciled_amount(self):
        invoice = self._create_reporting_invoice(
            partner=self.b2bi_customer,
            amount=100.0,
            invoice_date='2025-09-03',
            name='PARTIAL_PAYMENT_INVOICE',
        )

        payment = self._register_payment(invoice, '2025-09-09', amount=40.0)
        payment_move = payment.move_id
        flow = payment_move.l10n_fr_pdp_last_flow_id

        self.assertRecordValues(payment_move, [{
            'l10n_fr_pdp_is_flow_10_report_type': 'payment',
            'l10n_fr_pdp_is_flow_10_operation_type': 'sale',
            'l10n_fr_pdp_status': 'pending',
        }])
        xml = self._build_flow_xml(flow)
        payment_subtotal = xml.find('./PaymentsReport/Invoice/Payment/SubTotals')
        self.assertIsNotNone(payment_subtotal)
        self.assertAlmostEqual(float(payment_subtotal.findtext('Amount')), payment.amount, places=2)

    def test_credit_note_compensation_is_not_reported_as_payment(self):
        invoice = self._create_reporting_invoice(
            partner=self.b2bi_customer,
            amount=100.0,
            invoice_date='2025-09-03',
            name='COMPENSATED_INVOICE',
        )
        refund = self._create_reporting_move(
            'out_refund',
            self.b2bi_customer,
            amount=100.0,
            invoice_date='2025-09-03',
            name='COMPENSATING_CREDIT_NOTE',
            tax_ids=self._get_tax_on_payment(),
        )

        (invoice.line_ids + refund.line_ids).filtered(
            lambda line: line.account_id.reconcile and line.account_id.account_type == 'asset_receivable',
        ).reconcile()
        self._refresh_pdp_fields(invoice | refund)

        reconciled_moves = invoice._get_reconciled_amls().move_id
        self.assertFalse(reconciled_moves.filtered(
            lambda move: move.l10n_fr_pdp_is_flow_10_report_type == 'payment',
        ))
        self.assertEqual(invoice.l10n_fr_pdp_is_flow_10_report_type, 'transaction')
        self.assertEqual(refund.l10n_fr_pdp_is_flow_10_report_type, 'transaction')

    def test_b2c_goods_only_payment_is_excluded_from_payment_flow(self):
        invoice = self._create_reporting_invoice(
            partner=self.b2c_customer,
            amount=120.0,
            invoice_date='2025-09-03',
            name='B2C_GOODS_ONLY_PAYMENT',
            tax_ids=self._get_tax_sale_good_20_tax_included(),
        )

        payment = self._register_payment(invoice, '2025-09-09')
        payment_move = payment.move_id

        self.assertRecordValues(payment_move, [{
            'l10n_fr_pdp_is_flow_10_report_type': False,
            'l10n_fr_pdp_is_flow_10_operation_type': False,
            'l10n_fr_pdp_status': 'out_of_scope',
        }])
        self.assertFalse(payment_move.l10n_fr_pdp_last_flow_id)

    def test_b2c_mixed_goods_services_payment_reports_service_part_only(self):
        service_tax = self._get_tax_on_payment_20_tax_included()
        goods_tax = self._get_tax_sale_good_20_tax_included()
        invoice = self._create_reporting_invoice_with_lines(
            partner=self.b2c_customer,
            invoice_date='2025-09-03',
            name='B2C_MIXED_PAYMENT',
            lines=[
                {'price_unit': 120.0, 'tax_ids': goods_tax},
                {'price_unit': 60.0, 'tax_ids': service_tax},
            ],
        )

        payment = self._register_payment(invoice, '2025-09-09')
        payment_move = payment.move_id
        flow = payment_move.l10n_fr_pdp_last_flow_id
        service_line = invoice.invoice_line_ids.filtered(lambda line: service_tax in line.tax_ids)

        self.assertRecordValues(payment_move, [{
            'l10n_fr_pdp_is_flow_10_report_type': 'payment',
            'l10n_fr_pdp_is_flow_10_operation_type': 'sale',
            'l10n_fr_pdp_status': 'pending',
        }])
        xml = self._build_flow_xml(flow)
        payment_amount = sum(
            float(subtotal.findtext('Amount'))
            for subtotal in xml.findall('./PaymentsReport/Transactions/Payment/SubTotals')
        )
        self.assertAlmostEqual(payment_amount, service_line.price_total, places=2)

    def test_b2bi_goods_only_payment_is_excluded_from_payment_flow(self):
        invoice = self._create_reporting_invoice(
            partner=self.b2bi_customer,
            amount=100.0,
            invoice_date='2025-09-03',
            name='B2BI_GOODS_ONLY_PAYMENT',
            tax_ids=self._get_tax_sale_good_intra_0(),
        )

        payment = self._register_payment(invoice, '2025-09-09')
        payment_move = payment.move_id

        self.assertRecordValues(payment_move, [{
            'l10n_fr_pdp_is_flow_10_report_type': False,
            'l10n_fr_pdp_is_flow_10_operation_type': False,
            'l10n_fr_pdp_status': 'out_of_scope',
        }])
        self.assertFalse(payment_move.l10n_fr_pdp_last_flow_id)

    def test_b2bi_mixed_goods_services_payment_reports_service_part_only(self):
        service_tax = self._get_tax_on_payment_20()
        goods_tax = self._get_tax_sale_good_intra_0()
        invoice = self._create_reporting_invoice_with_lines(
            partner=self.b2bi_customer,
            invoice_date='2025-09-03',
            name='B2BI_MIXED_PAYMENT',
            lines=[
                {'price_unit': 100.0, 'tax_ids': goods_tax},
                {'price_unit': 50.0, 'tax_ids': service_tax},
            ],
        )

        payment = self._register_payment(invoice, '2025-09-09')
        payment_move = payment.move_id
        flow = payment_move.l10n_fr_pdp_last_flow_id
        service_line = invoice.invoice_line_ids.filtered(lambda line: service_tax in line.tax_ids)

        self.assertRecordValues(payment_move, [{
            'l10n_fr_pdp_is_flow_10_report_type': 'payment',
            'l10n_fr_pdp_is_flow_10_operation_type': 'sale',
            'l10n_fr_pdp_status': 'pending',
        }])
        xml = self._build_flow_xml(flow)
        payment_amount = sum(
            float(subtotal.findtext('Amount'))
            for subtotal in xml.findall('./PaymentsReport/Invoice/Payment/SubTotals')
        )
        self.assertAlmostEqual(payment_amount, service_line.price_total, places=2)

    def test_payment_after_invoice_period_creates_flow_in_payment_period(self):
        invoice = self._create_reporting_invoice(
            partner=self.b2bi_customer,
            amount=100.0,
            invoice_date='2025-09-03',
            name='PAYMENT_AFTER_INVOICE_PERIOD',
        )

        payment = self._register_payment(invoice, '2025-10-03')
        payment_move = payment.move_id
        payment_flow = payment_move.l10n_fr_pdp_last_flow_id

        self.assertNotEqual(invoice.l10n_fr_pdp_last_flow_id, payment_flow)
        self.assertRecordValues(payment_flow, [{
            'report_type': 'payment',
            'operation_type': 'sale',
            'period_start': fields.Date.to_date('2025-10-01'),
            'period_end': fields.Date.to_date('2025-10-31'),
        }])
        september_payment_flow = self.env['l10n.fr.pdp.reports.flow'].search([
            ('company_id', '=', self.company.id),
            ('report_type', '=', 'payment'),
            ('operation_type', '=', 'sale'),
            ('period_start', '=', fields.Date.to_date('2025-09-01')),
            ('period_end', '=', fields.Date.to_date('2025-09-30')),
        ])
        self.assertFalse(september_payment_flow)

    def test_payment_before_invoice_period_creates_flow_in_payment_period(self):
        invoice = self._create_reporting_invoice(
            partner=self.b2bi_customer,
            amount=100.0,
            invoice_date='2025-10-03',
            name='PAYMENT_BEFORE_INVOICE_PERIOD',
        )

        payment = self._register_payment(invoice, '2025-09-29')
        payment_move = payment.move_id
        payment_flow = payment_move.l10n_fr_pdp_last_flow_id

        self.assertNotEqual(invoice.l10n_fr_pdp_last_flow_id, payment_flow)
        self.assertRecordValues(payment_flow, [{
            'report_type': 'payment',
            'operation_type': 'sale',
            'period_start': fields.Date.to_date('2025-09-01'),
            'period_end': fields.Date.to_date('2025-09-30'),
        }])

    def test_credit_note_creates_transaction_flow_payload(self):
        refund = self._create_reporting_move(
            'out_refund',
            self.b2bi_customer,
            amount=100.0,
            invoice_date='2025-09-03',
            name='B2BI_CREDIT_NOTE',
            tax_ids=self._get_tax_on_payment(),
        )

        self.assertRecordValues(refund, [{
            'l10n_fr_pdp_is_flow_10_report_type': 'transaction',
            'l10n_fr_pdp_is_flow_10_operation_type': 'sale',
            'l10n_fr_pdp_status': 'pending',
        }])
        flow = refund.l10n_fr_pdp_last_flow_id
        self.assertRecordValues(flow, [{
            'report_type': 'transaction',
            'operation_type': 'sale',
            'state': 'ready',
        }])

        xml = self._build_flow_xml(flow)
        invoices = xml.findall('./TransactionsReport/Invoice')
        self.assertEqual(len(invoices), 1)
        self.assertEqual(invoices[0].findtext('ID'), refund.name)
        self.assertEqual(invoices[0].findtext('TypeCode'), '381')

    def test_foreign_currency_invoice_reports_invoice_currency_amounts(self):
        invoice_currency = self.setup_other_currency('USD', rates=[('2025-09-01', 2.0)])
        invoice = self._create_reporting_invoice(
            partner=self.b2bi_customer,
            amount=100.0,
            invoice_date='2025-09-03',
            name='FOREIGN_CURRENCY_TRANSACTION',
            currency=invoice_currency,
            tax_ids=self._get_tax_on_payment_20(),
        )
        transaction_flow = invoice.l10n_fr_pdp_last_flow_id
        expected_tax_amount_eur = invoice.currency_id._convert(
            invoice.amount_tax,
            self.company.currency_id,
            self.company,
            invoice.date,
        )

        transaction_xml = self._build_flow_xml(transaction_flow)
        invoice_node = transaction_xml.find('./TransactionsReport/Invoice')
        self.assertIsNotNone(invoice_node)
        self.assertNotEqual(invoice.currency_id, self.company.currency_id)
        self.assertEqual(invoice.currency_id, invoice_currency)
        self.assertEqual(invoice_node.findtext('CurrencyCode'), invoice_currency.name)
        self.assertAlmostEqual(
            float(invoice_node.findtext('MonetaryTotal/TaxExclusiveAmount')),
            invoice.amount_untaxed,
            places=2,
            msg='TT-51 TaxExclusiveAmount must be expressed in the invoice currency',
        )
        self.assertAlmostEqual(
            float(invoice_node.findtext('MonetaryTotal/TaxAmount')),
            expected_tax_amount_eur,
            places=2,
            msg='TT-52 TaxAmount must be converted to EUR',
        )
        self.assertEqual(
            invoice_node.find('MonetaryTotal/TaxAmount').get('CurrencyCode'),
            self.company.currency_id.name,
        )
        tax_subtotal_node = invoice_node.find('TaxSubTotal')
        self.assertIsNotNone(tax_subtotal_node)
        self.assertAlmostEqual(
            float(tax_subtotal_node.findtext('TaxableAmount')),
            invoice.amount_untaxed,
            places=2,
            msg='TaxSubTotal TaxableAmount must be expressed in the invoice currency',
        )
        self.assertAlmostEqual(
            float(tax_subtotal_node.findtext('TaxAmount')),
            invoice.amount_tax,
            places=2,
            msg='TaxSubTotal TaxAmount must be expressed in the invoice currency',
        )
        line_node = invoice_node.find('Line')
        self.assertIsNotNone(line_node)
        self.assertAlmostEqual(
            float(line_node.findtext('Price/PriceAmount')),
            invoice.invoice_line_ids.filtered(lambda line: line.display_type == 'product').price_unit,
            places=2,
            msg='Line PriceAmount must be expressed in the invoice currency',
        )

    def test_foreign_currency_invoice_paid_in_third_currency_reports_payment_currency_amounts(self):
        invoice_currency = self.setup_other_currency('USD', rates=[('2025-09-01', 2.0)])
        payment_currency = self.setup_other_currency('CAD', rates=[('2025-09-01', 3.0)])
        invoice = self._create_reporting_invoice(
            partner=self.b2bi_customer,
            amount=100.0,
            invoice_date='2025-09-03',
            name='FOREIGN_CURRENCY_PAYMENT',
            currency=invoice_currency,
            tax_ids=self._get_tax_on_payment_20(),
        )
        payment = self._register_payment(invoice, '2025-09-09', currency=payment_currency)
        payment_move = payment.move_id
        payment_flow = payment_move.l10n_fr_pdp_last_flow_id
        expected_payment_amount_eur = payment.currency_id._convert(
            payment.amount,
            self.company.currency_id,
            self.company,
            payment.date,
        )

        payment_xml = self._build_flow_xml(payment_flow)
        payment_subtotal = payment_xml.find('./PaymentsReport/Invoice/Payment/SubTotals')
        self.assertIsNotNone(payment_subtotal)
        self.assertNotEqual(invoice.currency_id, self.company.currency_id)
        self.assertNotEqual(payment.currency_id, self.company.currency_id)
        self.assertNotEqual(invoice.currency_id, payment.currency_id)
        self.assertEqual(invoice.currency_id, invoice_currency)
        self.assertEqual(payment.currency_id, payment_currency)
        self.assertEqual(payment_subtotal.findtext('CurrencyCode'), payment_currency.name)
        self.assertAlmostEqual(
            float(payment_subtotal.findtext('Amount')),
            expected_payment_amount_eur,
            places=2,
            msg='TT-95 payment Amount must be converted to EUR even when CurrencyCode is the payment currency',
        )

    def test_payment_on_vendor_bill_creates_purchase_payment_flow(self):
        bill = self._create_reporting_vendor_bill(
            amount=100.0,
            invoice_date='2025-09-03',
            name='VENDOR_BILL_PAYMENT',
        )

        payment = self._register_payment(bill, '2025-09-03')
        payment_move = payment.move_id

        self.assertRecordValues(payment_move, [{
            'l10n_fr_pdp_is_flow_10_report_type': 'payment',
            'l10n_fr_pdp_is_flow_10_operation_type': 'purchase',
            'l10n_fr_pdp_status': 'pending',
        }])
        flow = payment_move.l10n_fr_pdp_last_flow_id
        self.assertRecordValues(flow, [{
            'report_type': 'payment',
            'operation_type': 'purchase',
            'state': 'ready',
        }])

    def test_transaction_flow_is_not_auto_sent_before_due_date(self):
        invoice = self._create_reporting_invoice(
            partner=self.b2bi_customer,
            invoice_date='2025-09-03',
            name='CRON_BEFORE_DUE_DATE',
        )
        flow = invoice.l10n_fr_pdp_last_flow_id

        self._run_send_cron('2025-09-19')
        flow.invalidate_recordset(['state', 'payload_id'])

        self.assertRecordValues(flow, [{
            'state': 'ready',
        }])
        self.assertFalse(flow.payload_id)

    def test_transaction_flow_is_auto_sent_on_due_date(self):
        invoice = self._create_reporting_invoice(
            partner=self.b2bi_customer,
            invoice_date='2025-09-03',
            name='CRON_DUE_DATE',
        )
        flow = invoice.l10n_fr_pdp_last_flow_id

        self._run_send_cron('2025-09-20', identifier='FLOW-CRON-DUE-DATE')
        flow.invalidate_recordset(['state', 'payload_id'])
        invoice.invalidate_recordset(['l10n_fr_pdp_sent_in_flow_ids'])

        self.assertRecordValues(flow, [{
            'state': 'sent',
        }])
        self.assertTrue(flow.payload_id)
        self.assertIn(flow, invoice.l10n_fr_pdp_sent_in_flow_ids)

    def test_transaction_flow_with_errors_is_not_sent_before_due_date(self):
        valid_invoice = self._create_reporting_invoice(
            partner=self.b2bi_customer,
            invoice_date='2025-09-03',
            name='CRON_VALID_BEFORE_DUE',
        )
        invalid_invoice = self._create_reporting_invoice(
            partner=self.b2bi_customer,
            invoice_date='2025-09-03',
            name='CRON_ERROR_BEFORE_DUE',
            sent=False,
        )
        flow = valid_invoice.l10n_fr_pdp_last_flow_id
        flow.invalidate_recordset(['move_ids', 'error_moves_count'])

        self.assertEqual(flow, invalid_invoice.l10n_fr_pdp_last_flow_id)
        self.assertEqual(flow.error_moves_count, 1)

        self._run_send_cron('2025-09-19')
        flow.invalidate_recordset(['state', 'payload_id'])

        self.assertRecordValues(flow, [{
            'state': 'ready',
        }])
        self.assertFalse(flow.payload_id)

    def test_transaction_flow_with_errors_sends_valid_moves_on_due_date(self):
        valid_invoice = self._create_reporting_invoice(
            partner=self.b2bi_customer,
            invoice_date='2025-09-03',
            name='CRON_VALID_ON_DUE',
        )
        invalid_invoice = self._create_reporting_invoice(
            partner=self.b2bi_customer,
            invoice_date='2025-09-03',
            name='CRON_ERROR_ON_DUE',
            sent=False,
        )
        flow = valid_invoice.l10n_fr_pdp_last_flow_id
        flow.invalidate_recordset(['move_ids', 'error_moves_count'])

        self.assertEqual(flow.error_moves_count, 1)
        self._run_send_cron('2025-09-20', identifier='FLOW-CRON-DUE-DAY')
        flow.invalidate_recordset(['state', 'payload_id'])
        valid_invoice.invalidate_recordset(['l10n_fr_pdp_sent_in_flow_ids'])
        invalid_invoice.invalidate_recordset(['l10n_fr_pdp_status', 'l10n_fr_pdp_sent_in_flow_ids'])

        xml = etree.fromstring(flow.payload_id.raw)
        reported_invoice_ids = [
            invoice_node.findtext('ID')
            for invoice_node in xml.findall('./TransactionsReport/Invoice')
        ]

        self.assertRecordValues(flow, [{
            'state': 'sent',
        }])
        self.assertIn(valid_invoice.name, reported_invoice_ids)
        self.assertNotIn(invalid_invoice.name, reported_invoice_ids)
        self.assertIn(flow, valid_invoice.l10n_fr_pdp_sent_in_flow_ids)
        self.assertNotIn(flow, invalid_invoice.l10n_fr_pdp_sent_in_flow_ids)
        self.assertEqual(invalid_invoice.l10n_fr_pdp_status, 'error')

    def test_sent_flow_creates_rectificative_flow_when_new_invoice_added(self):
        first_invoice = self._create_reporting_invoice(
            partner=self.b2c_customer,
            invoice_date='2025-09-03',
            name='INITIAL_FLOW_INVOICE',
        )
        initial_flow = first_invoice.l10n_fr_pdp_last_flow_id
        initial_flow.write({'state': 'sent'})

        second_invoice = self._create_reporting_invoice(
            partner=self.b2c_customer,
            invoice_date='2025-09-10',
            name='RECTIFICATIVE_FLOW_INVOICE',
        )
        rectificative_flow = second_invoice.l10n_fr_pdp_last_flow_id

        self.assertNotEqual(initial_flow, rectificative_flow)
        self.assertRecordValues(rectificative_flow, [{
            'report_type': 'transaction',
            'operation_type': 'sale',
            'state': 'ready',
            'transmission_type': 'rectificative',
            'initial_flow_id': initial_flow.id,
        }])
        xml = self._build_flow_xml(rectificative_flow)
        self.assertEqual(xml.findtext('./ReportDocument/TypeCode'), 'RE')

    def test_error_moves_are_moved_to_rectificative_flow_when_initial_is_sent(self):
        valid_invoice = self._create_reporting_invoice(
            partner=self.b2bi_customer,
            invoice_date='2025-09-03',
            name='INITIAL_VALID_WITH_ERROR_MOVE',
        )
        invalid_invoice = self._create_reporting_invoice(
            partner=self.b2bi_customer,
            invoice_date='2025-09-03',
            name='INITIAL_ERROR_MOVED_TO_RE',
            sent=False,
        )
        initial_flow = valid_invoice.l10n_fr_pdp_last_flow_id
        initial_flow.invalidate_recordset(['move_ids', 'error_moves_count'])

        self.assertEqual(initial_flow, invalid_invoice.l10n_fr_pdp_last_flow_id)
        self.assertEqual(initial_flow.error_moves_count, 1)

        self._run_send_cron('2025-09-20', identifier='FLOW-ERRORS-INITIAL-SENT')
        initial_flow.invalidate_recordset(['state'])
        valid_invoice.invalidate_recordset(['l10n_fr_pdp_sent_in_flow_ids'])
        invalid_invoice.invalidate_recordset([
            'l10n_fr_pdp_last_flow_id',
            'l10n_fr_pdp_sent_in_flow_ids',
            'l10n_fr_pdp_status',
        ])
        rectificative_flow = invalid_invoice.l10n_fr_pdp_last_flow_id

        self.assertRecordValues(initial_flow, [{
            'state': 'sent',
        }])
        self.assertIn(initial_flow, valid_invoice.l10n_fr_pdp_sent_in_flow_ids)
        self.assertNotIn(initial_flow, invalid_invoice.l10n_fr_pdp_sent_in_flow_ids)
        self.assertNotEqual(initial_flow, rectificative_flow)
        self.assertRecordValues(rectificative_flow, [{
            'report_type': 'transaction',
            'operation_type': 'sale',
            'state': 'ready',
            'transmission_type': 'rectificative',
            'initial_flow_id': initial_flow.id,
        }])
        self.assertIn(invalid_invoice, rectificative_flow.move_ids)

    def test_rectificative_flow_is_sent_when_error_moves_become_ready(self):
        valid_invoice = self._create_reporting_invoice(
            partner=self.b2bi_customer,
            invoice_date='2025-09-03',
            name='RE_VALID_BEFORE_FIX',
        )
        invalid_invoice = self._create_reporting_invoice(
            partner=self.b2bi_customer,
            invoice_date='2025-09-03',
            name='RE_ERROR_THEN_READY',
            sent=False,
        )
        initial_flow = valid_invoice.l10n_fr_pdp_last_flow_id

        self._run_send_cron('2025-09-20', identifier='FLOW-ERRORS-BEFORE-RE')
        invalid_invoice.invalidate_recordset(['l10n_fr_pdp_last_flow_id'])
        rectificative_flow = invalid_invoice.l10n_fr_pdp_last_flow_id
        self.assertNotEqual(initial_flow, rectificative_flow)

        invalid_invoice.is_move_sent = True
        self._refresh_pdp_fields(invalid_invoice)
        invalid_invoice.invalidate_recordset([
            'l10n_fr_pdp_has_error',
            'l10n_fr_pdp_status',
            'l10n_fr_pdp_last_flow_id',
        ])
        rectificative_flow.invalidate_recordset(['move_ids', 'error_moves_count'])

        self.assertEqual(invalid_invoice.l10n_fr_pdp_status, 'pending')
        self.assertEqual(rectificative_flow.error_moves_count, 0)

        self._run_send_cron('2025-09-21', identifier='FLOW-RE-ERROR-FIXED')
        rectificative_flow.invalidate_recordset(['state'])
        invalid_invoice.invalidate_recordset(['l10n_fr_pdp_sent_in_flow_ids'])

        self.assertRecordValues(rectificative_flow, [{
            'state': 'sent',
        }])
        self.assertIn(rectificative_flow, invalid_invoice.l10n_fr_pdp_sent_in_flow_ids)

    def test_payment_added_to_already_sent_period_creates_rectificative_payment_flow(self):
        initial_flow = self._create_sent_flow_for_scope(
            'payment',
            'sale',
            '2025-09-01',
            'INITIAL-SENT-PAYMENT-FLOW',
        )
        invoice = self._create_reporting_invoice(
            partner=self.b2c_customer,
            amount=120.0,
            invoice_date='2025-09-16',
            name='PAYMENT_ADDED_AFTER_INITIAL_SENT',
            tax_ids=self._get_tax_on_payment_20_tax_included(),
            total_amount=True,
        )
        payment = self._register_payment(invoice, '2025-09-16')
        payment_move = payment.move_id
        rectificative_flow = payment_move.l10n_fr_pdp_last_flow_id

        self.assertNotEqual(initial_flow, rectificative_flow)
        self.assertRecordValues(rectificative_flow, [{
            'report_type': 'payment',
            'operation_type': 'sale',
            'state': 'ready',
            'transmission_type': 'rectificative',
            'initial_flow_id': initial_flow.id,
        }])
        self.assertIn(payment_move, rectificative_flow.move_ids)

    def test_invoice_corrected_before_initial_flow_is_sent_stays_in_initial_flow(self):
        invoice = self._create_reporting_invoice(
            partner=self.b2c_customer,
            amount=100.0,
            invoice_date='2025-09-03',
            name='INVOICE_CORRECTED_BEFORE_SEND',
        )
        initial_flow = invoice.l10n_fr_pdp_last_flow_id

        invoice.with_context(l10n_fr_pdp_bypass_draft_check=True).button_draft()
        invoice.invoice_line_ids.price_unit = 150.0
        invoice.action_post()
        invoice.is_move_sent = True
        self._refresh_pdp_fields(invoice)
        invoice.invalidate_recordset(['l10n_fr_pdp_last_flow_id'])
        initial_flow.invalidate_recordset(['rectificative_flow_ids', 'move_ids'])

        self.assertEqual(invoice.l10n_fr_pdp_last_flow_id, initial_flow)
        self.assertEqual(initial_flow.transmission_type, 'initial')
        self.assertFalse(initial_flow.rectificative_flow_ids)
        self.assertIn(invoice, initial_flow.move_ids)

    def test_payment_corrected_before_payment_flow_is_sent_stays_in_initial_payment_flow(self):
        invoice = self._create_reporting_invoice(
            partner=self.b2c_customer,
            amount=120.0,
            invoice_date='2025-09-16',
            name='PAYMENT_CORRECTED_BEFORE_SEND',
            tax_ids=self._get_tax_on_payment_20_tax_included(),
            total_amount=True,
        )
        first_payment = self._register_payment(invoice, '2025-09-16', amount=40.0)
        initial_flow = first_payment.move_id.l10n_fr_pdp_last_flow_id

        second_payment = self._register_payment(invoice, '2025-09-18', amount=80.0)
        second_payment_move = second_payment.move_id
        initial_flow.invalidate_recordset(['rectificative_flow_ids', 'move_ids'])

        self.assertEqual(second_payment_move.l10n_fr_pdp_last_flow_id, initial_flow)
        self.assertEqual(initial_flow.transmission_type, 'initial')
        self.assertFalse(initial_flow.rectificative_flow_ids)
        self.assertIn(first_payment.move_id, initial_flow.move_ids)
        self.assertIn(second_payment_move, initial_flow.move_ids)

    def test_payment_flow_matches_reserve_fixture_0292(self):
        invoice_1 = self._create_reporting_invoice(
            partner=self.b2bi_customer,
            amount=30000.0,
            invoice_date='2025-09-03',
            name='S2F3_REPORT2025',
        )
        invoice_2 = self._create_reporting_invoice(
            partner=self.b2bi_customer,
            amount=400000.0,
            invoice_date='2025-09-10',
            name='S2F4_REPORT2025',
        )
        payment_1 = self._register_payment(invoice_1, '2025-09-03')
        payment_2 = self._register_payment(invoice_2, '2025-09-09')
        b2c_invoice_1 = self._create_reporting_invoice(
            partner=self.b2c_customer,
            amount=20000.0,
            invoice_date='2025-09-16',
            name='B2C_PAYMENT_1',
            tax_ids=self._get_tax_on_payment_20_tax_included(),
            total_amount=True,
        )
        b2c_invoice_2 = self._create_reporting_invoice(
            partner=self.b2c_customer,
            amount=20000.0,
            invoice_date='2025-09-22',
            name='B2C_PAYMENT_2',
            tax_ids=self._get_tax_on_payment_20_tax_included(),
            total_amount=True,
        )
        b2c_payment_1 = self._register_payment(b2c_invoice_1, '2025-09-16')
        b2c_payment_2 = self._register_payment(b2c_invoice_2, '2025-09-22')
        payment_moves = (
            payment_1.move_id
            | payment_2.move_id
            | b2c_payment_1.move_id
            | b2c_payment_2.move_id
        )
        flows = payment_moves.mapped('l10n_fr_pdp_last_flow_id')

        self.assertEqual(len(flows), 1)
        self._assert_flow_matches_report_fixture(
            flows,
            'FFE1025A_PPF262_PPF2621025000000000000292.xml',
        )

    def test_payment_flow_matches_reserve_fixture_0294(self):
        initial_flow = self._create_sent_flow_for_scope(
            'payment',
            'sale',
            '2025-09-01',
            'INITIAL-SENT-PAYMENT-FLOW-0294',
        )
        invoice_1 = self._create_reporting_invoice(
            partner=self.b2bi_customer,
            amount=30000.0,
            invoice_date='2025-09-03',
            name='S2F3_REPORT2025',
        )
        invoice_2 = self._create_reporting_invoice(
            partner=self.b2bi_customer,
            amount=400000.0,
            invoice_date='2025-09-10',
            name='S2F4_REPORT2025',
        )
        payment_1 = self._register_payment(invoice_1, '2025-09-03')
        payment_2 = self._register_payment(invoice_2, '2025-09-09')
        b2c_invoice_1 = self._create_reporting_invoice(
            partner=self.b2c_customer,
            amount=30000.0,
            invoice_date='2025-09-16',
            name='B2C_PAYMENT_1',
            tax_ids=self._get_tax_on_payment_20_tax_included(),
            total_amount=True,
        )
        b2c_invoice_2 = self._create_reporting_invoice(
            partner=self.b2c_customer,
            amount=30000.0,
            invoice_date='2025-09-22',
            name='B2C_PAYMENT_2',
            tax_ids=self._get_tax_on_payment_20_tax_included(),
            total_amount=True,
        )
        b2c_payment_1 = self._register_payment(b2c_invoice_1, '2025-09-16')
        b2c_payment_2 = self._register_payment(b2c_invoice_2, '2025-09-22')
        payment_moves = (
            payment_1.move_id
            | payment_2.move_id
            | b2c_payment_1.move_id
            | b2c_payment_2.move_id
        )
        flows = payment_moves.mapped('l10n_fr_pdp_last_flow_id')

        self.assertEqual(len(flows), 1)
        self.assertRecordValues(flows, [{
            'report_type': 'payment',
            'operation_type': 'sale',
            'transmission_type': 'rectificative',
            'initial_flow_id': initial_flow.id,
        }])
        self._assert_flow_matches_report_fixture(
            flows,
            'FFE1025A_PPF262_PPF2621025000000000000294.xml',
        )

    def test_single_payment_reconciled_with_two_invoices_reports_both_invoice_payments(self):
        invoices = self._create_reporting_invoice(
            partner=self.b2bi_customer,
            amount=30.0,
            invoice_date='2025-09-03',
            name='SINGLE_PAY_A',
        ) | self._create_reporting_invoice(
            partner=self.b2bi_customer,
            amount=70.0,
            invoice_date='2025-09-03',
            name='SINGLE_PAY_B',
        )

        payment = self._register_payment(invoices, '2025-09-09')
        payment_move = payment.move_id
        flow = payment_move.l10n_fr_pdp_last_flow_id
        xml = self._build_flow_xml(flow)
        reported_invoice_ids = [
            invoice_node.findtext('InvoiceId') or invoice_node.findtext('InvoiceID')
            for invoice_node in xml.findall('./PaymentsReport/Invoice')
        ]

        self.assertEqual(payment.amount, sum(invoices.mapped('amount_total')))
        self.assertEqual(Counter(reported_invoice_ids), Counter(invoices.mapped('name')))
