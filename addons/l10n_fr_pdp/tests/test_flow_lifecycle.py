from collections import Counter
from unittest.mock import patch

from lxml import etree

from odoo import fields
from odoo.tests import Form, tagged
from odoo.tools import file_open

from odoo.addons.l10n_fr_pdp.tests.common import TestL10nFrPdpCommon


@tagged('post_install_l10n', 'post_install', '-at_install', 'test_flow_lifecycle')
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
            'company_registry': '34057796400024',
            'vat': 'FR23334175221',
        })
        cls.company.invalidate_recordset([
            'account_peppol_edi_user',
            'l10n_fr_f10_enable_reporting',
        ])
        cls.company._compute_account_peppol_edi_user()
        cls.company._compute_l10n_fr_f10_enable_reporting()
        cls.env.flush_all()

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
        cls.b2bi_invalid_customer = cls.env['res.partner'].create({
            'name': 'PDP B2BI Customer',
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
        cls._setup_taxes_included()

    @classmethod
    def _setup_taxes_included(cls):
        cls.tax_sale_good_20_tax_included = cls.env['account.chart.template'].ref('tva_normale').copy({'name': '20%G Testing'})
        cls.tax_sale_good_20_tax_included.price_include_override = 'tax_included'
        cls.tax_on_payment_20_tax_included = cls.env['account.chart.template'].ref('tva_normale_encaissement').copy({'name': '20%G Payment Testing'})
        cls.tax_on_payment_20_tax_included.price_include_override = 'tax_included'
        cls.tax_purchase_tax_on_payment = cls.env['account.chart.template'].ref('tva_acq_encaissement').copy({'name': '20%G Purchase Testing'})
        cls.tax_purchase_tax_on_payment.price_include_override = 'tax_included'

    def _get_tax_on_payment(self):
        return self.env['account.chart.template'].ref('tva_sale_service_0')

    def _get_tax_on_payment_20(self):
        return self.env['account.chart.template'].ref('tva_normale_encaissement')

    def _get_tax_sale_good_intra_0(self):
        return self.env['account.chart.template'].ref('tva_sale_good_intra_0')

    def _get_tax_sale_service_intra_0(self):
        return self.env['account.chart.template'].ref('tva_sale_service_intra_0')

    def _get_tax_sale_good_20_tax_included(self):
        return self.tax_sale_good_20_tax_included

    def _get_tax_on_payment_20_tax_included(self):
        return self.tax_on_payment_20_tax_included

    def _get_purchase_tax_on_payment(self):
        return self.tax_purchase_tax_on_payment

    def _create_reporting_move(
        self,
        move_type,
        partner,
        amount=100.0,
        invoice_date='2025-02-05',
        name=None,
        sent=True,
        tax_ids=None,
        currency=None,
        invoice_date_due=None,
        quantity=1.0,
    ):
        invoice_date = fields.Date.to_date(invoice_date)
        move = self._create_invoice_one_line(
            move_type=move_type,
            partner_id=partner,
            product_id=self.product_a,
            price_unit=amount,
            quantity=quantity,
            tax_ids=tax_ids,
            currency_id=currency,
            invoice_date=invoice_date,
            invoice_date_due=fields.Date.to_date(invoice_date_due) if invoice_date_due else None,
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
        sent=True,
    ):
        invoice_date = fields.Date.to_date(invoice_date)
        invoice = self._create_invoice(
            move_type='out_invoice',
            partner_id=partner,
            invoice_date=invoice_date,
            invoice_line_ids=[
                self._prepare_invoice_line(
                    product_id=line.get('product_id', self.product_a),
                    price_unit=line['price_unit'],
                    quantity=line.get('quantity', 1.0),
                    tax_ids=line.get('tax_ids'),
                    discount=line.get('discount', 0.0),
                )
                for line in lines
            ],
            post=False,
            invoice_date_due=fields.Date.to_date(invoice_date_due) if invoice_date_due else None,
        )
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
        currency=None,
        invoice_date_due=None,
        quantity=1.0
    ):
        return self._create_reporting_move(
            'out_invoice',
            partner,
            amount=amount,
            invoice_date=invoice_date,
            name=name,
            sent=sent,
            tax_ids=self._get_tax_on_payment() if tax_ids is None else tax_ids,
            currency=currency,
            invoice_date_due=invoice_date_due,
            quantity=quantity,
        )

    def _create_reporting_vendor_bill(
        self,
        partner=None,
        amount=100.0,
        invoice_date='2025-02-05',
        currency=None,
    ):
        return self._create_reporting_move(
            'in_invoice',
            partner or self.b2bi_customer,
            amount=amount,
            invoice_date=invoice_date,
            tax_ids=self._get_purchase_tax_on_payment(),
            currency=currency,
        )

    def _create_reporting_credit_note(self, invoice, invoice_date, sent=True):
        invoice_date = fields.Date.to_date(invoice_date)
        refund = invoice._reverse_moves([{
            'date': invoice_date,
            'invoice_date': invoice_date,
        }])
        refund.action_post()
        refund.is_move_sent = sent
        self._refresh_pdp_fields(refund)
        return refund

    def _refresh_pdp_fields(self, move):
        self.env.flush_all()
        move.company_id._compute_account_peppol_edi_user()
        move.company_id._compute_l10n_fr_f10_enable_reporting()
        move._compute_l10n_fr_pdp_has_error()
        move._compute_l10n_fr_pdp_status()

    def _correct_partner(self, invoice):
        invoice.partner_id.street = 'Mainstreet'
        self._refresh_pdp_fields(invoice)

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
            'uuid': identifier,
            'flow_id': identifier,
        }

    def _run_send_cron(self, date, identifier='FLOW-TEST-001'):
        with patch('odoo.fields.Date.today', return_value=fields.Date.to_date(date)):
            with patch(
                'odoo.addons.l10n_fr_pdp.models.pdp_flow.PdpFlow._send_to_proxy',
                return_value=self._proxy_success_response(identifier),
            ):
                self.env['l10n.fr.pdp.reports.flow']._cron_update_and_send_flows()

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
        self.assertTrue(flow.payload_id)
        return etree.fromstring(flow.payload_id.raw.content)

    def _load_expected_report_xml(self, filename):
        with file_open(f'l10n_fr_pdp/tests/data/{filename}', 'rb', filter_ext=('.xml',)) as report_file:
            return etree.fromstring(report_file.read())

    def _ignore_runtime_report_values(self, xml):
        for xpath in (
            './ReportDocument/Id',
            './ReportDocument/IssueDateTime/DateTimeString',
            './TransactionsReport/Invoice/Seller/TaxRegistrationId',
            './TransactionsReport/Invoice/TaxSubTotal/TaxCategory/TaxExemptionReason',
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

    def _create_form_invoice(self, partner, invoice_date, lines, sent=True, move_type='out_invoice'):
        with Form(self.env['account.move'].with_context(default_move_type=move_type)) as move_form:
            move_form.partner_id = partner
            move_form.invoice_date = fields.Date.to_date(invoice_date)
            for line_vals in lines:
                with move_form.invoice_line_ids.new() as line_form:
                    line_form.product_id = line_vals.get('product_id', self.product_a)
                    line_form.quantity = line_vals.get('quantity', 1.0)
                    line_form.price_unit = line_vals['price_unit']
                    line_form.tax_ids.clear()
                    for tax in line_vals.get('tax_ids', self._get_tax_on_payment()):
                        line_form.tax_ids.add(tax)
        move = move_form.save()
        move.action_post()
        self._refresh_pdp_fields(move)
        if move.is_sale_document(include_receipts=True):
            move.is_move_sent = sent
        return move

    def _register_form_payment(self, invoices, payment_date, amount=None):
        with Form(self.env['account.payment.register'].with_context(
            active_model='account.move',
            active_ids=invoices.ids,
        )) as payment_form:
            payment_form.journal_id = self.company_data['default_journal_bank']
            payment_form.payment_date = fields.Date.to_date(payment_date)
            if amount is not None:
                payment_form.amount = amount
        return payment_form.save()._create_payments()

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
        tax_151 = self._get_tax_sale_service_intra_0().copy({
            'ubl_cii_tax_category_code': 'E',
            'ubl_cii_tax_exemption_reason_code': 'VATEX-EU-151',
        })
        b2bi_invoice_1 = self._create_reporting_invoice(
            partner=self.b2bi_italian_customer,
            amount=1000.0,
            quantity=10.0,
            invoice_date='2025-09-01',
            invoice_date_due='2025-09-30',
            name='S1F1_REPORT2025',
            tax_ids=tax_151,
        )
        b2bi_invoice_2 = self._create_reporting_invoice(
            partner=self.b2bi_italian_customer,
            amount=200000.0,
            invoice_date='2025-09-01',
            invoice_date_due='2025-09-30',
            name='S1F2_REPORT2025',
            tax_ids=tax_151,
        )
        b2c_invoice_1 = self._create_reporting_invoice(
            partner=self.b2c_customer,
            amount=12000.0,
            invoice_date='2025-09-16',
            name='B2C_TRANSACTION_1',
            tax_ids=self._get_tax_on_payment_20_tax_included(),
        )
        b2c_invoice_2 = self._create_reporting_invoice(
            partner=self.b2c_customer,
            amount=12000.0,
            invoice_date='2025-09-22',
            name='B2C_TRANSACTION_2',
            tax_ids=self._get_tax_sale_good_20_tax_included(),
        )
        moves = b2bi_invoice_1 | b2bi_invoice_2 | b2c_invoice_1 | b2c_invoice_2
        flow = moves.mapped('l10n_fr_pdp_last_flow_id')

        self.assertEqual(len(flow), 1)

    def test_b2c_invoice_creates_transaction_flow_payload(self):
        invoice = self._create_reporting_invoice(
            partner=self.b2c_customer,
        )

        self.assertRecordValues(invoice, [{
            'l10n_fr_pdp_flow_10_report_type': 'transaction',
            'l10n_fr_pdp_flow_10_operation_type': 'sale',
            'l10n_fr_pdp_status': 'pending',
        }])
        flow = invoice.l10n_fr_pdp_last_flow_id
        self.assertRecordValues(flow, [{
            'report_type': 'transaction',
            'operation_type': 'sale',
            'state': 'ready',
        }])
        self.assertIn(invoice, flow._get_moves())

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
        self.assertEqual(transaction.findtext('TaxDueDateTypeCode'), '5')

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

    def test_b2bi_invoice_creates_transaction_flow_payload(self):
        invoice = self._create_reporting_invoice(partner=self.b2bi_customer)

        self.assertTrue(invoice.is_move_sent)
        self.assertRecordValues(invoice, [{
            'l10n_fr_pdp_flow_10_report_type': 'transaction',
            'l10n_fr_pdp_flow_10_operation_type': 'sale',
            'l10n_fr_pdp_status': 'pending',
        }])
        flow = invoice.l10n_fr_pdp_last_flow_id
        self.assertRecordValues(flow, [{
            'report_type': 'transaction',
            'operation_type': 'sale',
            'state': 'ready',
        }])
        self.assertIn(invoice, flow._get_moves())

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

    def test_domestic_b2b_invoice_stays_out_of_scope(self):
        invoice = self._create_reporting_invoice(
            partner=self.domestic_b2b_partner,
        )

        self.assertRecordValues(invoice, [{
            'l10n_fr_pdp_flow_10_report_type': False,
            'l10n_fr_pdp_status': 'out_of_scope',
        }])
        self.assertFalse(invoice.l10n_fr_pdp_last_flow_id)

    def test_domestic_vendor_bill_stays_out_of_scope(self):
        bill = self._create_reporting_vendor_bill(
            partner=self.domestic_b2b_partner,
        )

        self.assertRecordValues(bill, [{
            'l10n_fr_pdp_flow_10_report_type': False,
            'l10n_fr_pdp_status': 'out_of_scope',
        }])
        self.assertFalse(bill.l10n_fr_pdp_last_flow_id)

    def test_international_vendor_bill_creates_purchase_transaction_flow(self):
        bill = self._create_reporting_vendor_bill(
            partner=self.b2bi_customer,
            invoice_date='2025-09-03',
        )

        self.assertRecordValues(bill, [{
            'l10n_fr_pdp_flow_10_report_type': 'transaction',
            'l10n_fr_pdp_flow_10_operation_type': 'purchase',
            'l10n_fr_pdp_status': 'pending',
        }])
        flow = bill.l10n_fr_pdp_last_flow_id
        self.assertRecordValues(flow, [{
            'report_type': 'transaction',
            'operation_type': 'purchase',
            'state': 'ready',
        }])
        self.assertIn(bill, flow._get_moves())

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

        self.assertIn(b2c_invoice, flow._get_moves())
        self.assertIn(b2bi_invoice, flow._get_moves())

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
        )

        payment = self._register_payment(invoice, '2025-09-03')
        payment_move = payment.move_id

        self.assertRecordValues(payment_move, [{
            'l10n_fr_pdp_flow_10_report_type': 'payment',
            'l10n_fr_pdp_flow_10_operation_type': 'sale',
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
        )

        payment = self._create_unreconciled_customer_payment(invoice, '2025-09-03')
        payment_move = payment.move_id

        self.assertRecordValues(payment_move, [{
            'l10n_fr_pdp_flow_10_report_type': False,
            'l10n_fr_pdp_flow_10_operation_type': False,
            'l10n_fr_pdp_status': 'out_of_scope',
        }])
        self.assertFalse(payment_move.l10n_fr_pdp_last_flow_id)

    def test_partial_payment_reports_only_reconciled_amount(self):
        invoice = self._create_reporting_invoice(
            partner=self.b2bi_customer,
            amount=100.0,
            invoice_date='2025-09-03',
        )

        payment = self._register_payment(invoice, '2025-09-09', amount=40.0)
        payment_move = payment.move_id
        flow = payment_move.l10n_fr_pdp_last_flow_id

        self.assertRecordValues(payment_move, [{
            'l10n_fr_pdp_flow_10_report_type': 'payment',
            'l10n_fr_pdp_flow_10_operation_type': 'sale',
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
        )
        refund = self._create_reporting_move(
            'out_refund',
            self.b2bi_customer,
            amount=100.0,
            invoice_date='2025-09-03',
            tax_ids=self._get_tax_on_payment(),
        )

        (invoice.line_ids + refund.line_ids).filtered(
            lambda line: line.account_id.reconcile and line.account_id.account_type == 'asset_receivable',
        ).reconcile()
        self._refresh_pdp_fields(invoice | refund)

        reconciled_moves = invoice._get_reconciled_amls().move_id
        self.assertFalse(reconciled_moves.filtered(
            lambda move: move.l10n_fr_pdp_flow_10_report_type == 'payment',
        ))
        self.assertEqual(invoice.l10n_fr_pdp_flow_10_report_type, 'transaction')
        self.assertEqual(refund.l10n_fr_pdp_flow_10_report_type, 'transaction')

    def test_b2c_goods_only_payment_is_excluded_from_payment_flow(self):
        invoice = self._create_reporting_invoice(
            partner=self.b2c_customer,
            amount=120.0,
            invoice_date='2025-09-03',
            tax_ids=self._get_tax_sale_good_20_tax_included(),
        )

        payment = self._register_payment(invoice, '2025-09-09')
        payment_move = payment.move_id

        self.assertRecordValues(payment_move, [{
            'l10n_fr_pdp_flow_10_report_type': False,
            'l10n_fr_pdp_flow_10_operation_type': False,
            'l10n_fr_pdp_status': 'out_of_scope',
        }])
        self.assertFalse(payment_move.l10n_fr_pdp_last_flow_id)

    def test_b2c_mixed_goods_services_payment_reports_service_part_only(self):
        service_tax = self._get_tax_on_payment_20_tax_included()
        goods_tax = self._get_tax_sale_good_20_tax_included()
        invoice = self._create_reporting_invoice_with_lines(
            partner=self.b2c_customer,
            invoice_date='2025-09-03',
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
            'l10n_fr_pdp_flow_10_report_type': 'payment',
            'l10n_fr_pdp_flow_10_operation_type': 'sale',
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
            tax_ids=self._get_tax_sale_good_intra_0(),
        )

        payment = self._register_payment(invoice, '2025-09-09')
        payment_move = payment.move_id

        self.assertRecordValues(payment_move, [{
            'l10n_fr_pdp_flow_10_report_type': False,
            'l10n_fr_pdp_flow_10_operation_type': False,
            'l10n_fr_pdp_status': 'out_of_scope',
        }])
        self.assertFalse(payment_move.l10n_fr_pdp_last_flow_id)

    def test_b2bi_mixed_goods_services_payment_reports_service_part_only(self):
        service_tax = self._get_tax_on_payment_20()
        goods_tax = self._get_tax_sale_good_intra_0()
        invoice = self._create_reporting_invoice_with_lines(
            partner=self.b2bi_customer,
            invoice_date='2025-09-03',
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
            'l10n_fr_pdp_flow_10_report_type': 'payment',
            'l10n_fr_pdp_flow_10_operation_type': 'sale',
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
            tax_ids=self._get_tax_on_payment(),
        )

        self.assertRecordValues(refund, [{
            'l10n_fr_pdp_flow_10_report_type': 'transaction',
            'l10n_fr_pdp_flow_10_operation_type': 'sale',
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
        )

        payment = self._register_payment(bill, '2025-09-03')
        payment_move = payment.move_id

        self.assertRecordValues(payment_move, [{
            'l10n_fr_pdp_flow_10_report_type': 'payment',
            'l10n_fr_pdp_flow_10_operation_type': 'purchase',
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
        )
        invalid_invoice = self._create_reporting_invoice(
            partner=self.b2bi_invalid_customer,
            invoice_date='2025-09-03',
        )
        flow = valid_invoice.l10n_fr_pdp_last_flow_id
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
        )
        invalid_invoice = self._create_reporting_invoice(
            partner=self.b2bi_invalid_customer,
            invoice_date='2025-09-03',
        )
        flow = valid_invoice.l10n_fr_pdp_last_flow_id
        self.assertEqual(flow.error_moves_count, 1)
        self._run_send_cron('2025-09-20', identifier='FLOW-CRON-DUE-DAY')
        flow.invalidate_recordset(['state', 'payload_id'])
        valid_invoice.invalidate_recordset(['l10n_fr_pdp_sent_in_flow_ids'])
        invalid_invoice.invalidate_recordset(['l10n_fr_pdp_status', 'l10n_fr_pdp_sent_in_flow_ids'])

        xml = etree.fromstring(flow.payload_id.raw.content)
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
        )
        initial_flow = first_invoice.l10n_fr_pdp_last_flow_id

        self._run_send_cron('2025-09-20', identifier='FLOW-INITIAL-SENT')
        initial_flow.invalidate_recordset(['state'])
        self.assertRecordValues(initial_flow, [{'state': 'sent'}])

        second_invoice = self._create_reporting_invoice(
            partner=self.b2c_customer,
            invoice_date='2025-09-10',
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
        )
        invalid_invoice = self._create_reporting_invoice(
            partner=self.b2bi_invalid_customer,
            invoice_date='2025-09-03',
        )
        initial_flow = valid_invoice.l10n_fr_pdp_last_flow_id
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

        self._correct_partner(invalid_invoice)

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
        self.assertIn(invalid_invoice, rectificative_flow._get_moves())

    def test_rectificative_flow_is_sent_when_error_moves_become_ready(self):
        valid_invoice = self._create_reporting_invoice(
            partner=self.b2bi_customer,
            invoice_date='2025-09-03',
        )
        invalid_invoice = self._create_reporting_invoice(
            partner=self.b2bi_invalid_customer,
            invoice_date='2025-09-03',
        )
        initial_flow = valid_invoice.l10n_fr_pdp_last_flow_id

        self._run_send_cron('2025-09-20', identifier='FLOW-ERRORS-BEFORE-RE')
        invalid_invoice.invalidate_recordset(['l10n_fr_pdp_last_flow_id'])
        rectificative_flow = invalid_invoice.l10n_fr_pdp_last_flow_id
        self.assertNotEqual(initial_flow, rectificative_flow)

        self._correct_partner(invalid_invoice)
        self._refresh_pdp_fields(invalid_invoice)
        invalid_invoice._compute_l10n_fr_pdp_status()
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
        initial_invoice = self._create_reporting_invoice(
            partner=self.b2c_customer,
            amount=120.0,
            invoice_date='2025-09-16',
            tax_ids=self._get_tax_on_payment_20_tax_included(),
        )
        initial_payment = self._register_payment(initial_invoice, '2025-09-16')
        initial_flow = initial_payment.move_id.l10n_fr_pdp_last_flow_id

        self._run_send_cron('2025-10-10', identifier='FLOW-PAYMENT-INITIAL-SENT')
        initial_flow.invalidate_recordset(['state'])
        self.assertRecordValues(initial_flow, [{'state': 'sent'}])

        invoice = self._create_reporting_invoice(
            partner=self.b2c_customer,
            amount=120.0,
            invoice_date='2025-09-22',
            tax_ids=self._get_tax_on_payment_20_tax_included(),
        )
        payment = self._register_payment(invoice, '2025-09-22')
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
        self.assertIn(payment_move, rectificative_flow._get_moves())

    def test_invoice_corrected_before_initial_flow_is_sent_stays_in_initial_flow(self):
        invoice = self._create_reporting_invoice(
            partner=self.b2c_customer,
            amount=100.0,
            invoice_date='2025-09-03',
        )
        initial_flow = invoice.l10n_fr_pdp_last_flow_id

        invoice.with_context(l10n_fr_pdp_bypass_draft_check=True).button_draft()
        invoice.invoice_line_ids.price_unit = 150.0
        invoice.action_post()
        invoice.is_move_sent = True
        self._refresh_pdp_fields(invoice)
        initial_flow.invalidate_recordset(['rectificative_flow_ids'])

        self.assertEqual(invoice.l10n_fr_pdp_last_flow_id, initial_flow)
        self.assertEqual(initial_flow.transmission_type, 'initial')
        self.assertFalse(initial_flow.rectificative_flow_ids)
        self.assertIn(invoice, initial_flow._get_moves())

    def test_payment_corrected_before_payment_flow_is_sent_stays_in_initial_payment_flow(self):
        invoice = self._create_reporting_invoice(
            partner=self.b2c_customer,
            amount=120.0,
            invoice_date='2025-09-16',
            tax_ids=self._get_tax_on_payment_20_tax_included(),
        )
        first_payment = self._register_payment(invoice, '2025-09-16', amount=40.0)
        initial_flow = first_payment.move_id.l10n_fr_pdp_last_flow_id

        second_payment = self._register_payment(invoice, '2025-09-18', amount=80.0)
        second_payment_move = second_payment.move_id
        initial_flow.invalidate_recordset(['rectificative_flow_ids'])

        self.assertEqual(second_payment_move.l10n_fr_pdp_last_flow_id, initial_flow)
        self.assertEqual(initial_flow.transmission_type, 'initial')
        self.assertFalse(initial_flow.rectificative_flow_ids)
        self.assertIn(first_payment.move_id, initial_flow._get_moves())
        self.assertIn(second_payment_move, initial_flow._get_moves())

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
        )
        b2c_invoice_2 = self._create_reporting_invoice(
            partner=self.b2c_customer,
            amount=20000.0,
            invoice_date='2025-09-22',
            name='B2C_PAYMENT_2',
            tax_ids=self._get_tax_on_payment_20_tax_included(),
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
        )
        b2c_invoice_2 = self._create_reporting_invoice(
            partner=self.b2c_customer,
            amount=30000.0,
            invoice_date='2025-09-22',
            name='B2C_PAYMENT_2',
            tax_ids=self._get_tax_on_payment_20_tax_included(),
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

    def test_single_payment_reconciled_with_two_invoices_reports_both_invoice_payments(self):
        invoices = self._create_reporting_invoice(
            partner=self.b2bi_customer,
            amount=30.0,
            invoice_date='2025-09-03',
        ) | self._create_reporting_invoice(
            partner=self.b2bi_customer,
            amount=70.0,
            invoice_date='2025-09-03',
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

    def test_transaction_moves_from_different_periods_create_distinct_flows(self):
        first_invoice = self._create_reporting_invoice(
            partner=self.b2bi_customer,
            invoice_date='2025-09-03',
        )
        second_invoice = self._create_reporting_invoice(
            partner=self.b2bi_customer,
            invoice_date='2025-09-13',
        )
        first_flow = first_invoice.l10n_fr_pdp_last_flow_id
        second_flow = second_invoice.l10n_fr_pdp_last_flow_id

        self.assertNotEqual(first_flow, second_flow)
        self.assertRecordValues(first_flow, [{
            'report_type': 'transaction',
            'operation_type': 'sale',
            'period_start': fields.Date.to_date('2025-09-01'),
            'period_end': fields.Date.to_date('2025-09-10'),
        }])
        self.assertRecordValues(second_flow, [{
            'report_type': 'transaction',
            'operation_type': 'sale',
            'period_start': fields.Date.to_date('2025-09-11'),
            'period_end': fields.Date.to_date('2025-09-20'),
        }])

        first_xml = self._build_flow_xml(first_flow)
        second_xml = self._build_flow_xml(second_flow)
        self.assertEqual(
            [node.findtext('ID') for node in first_xml.findall('./TransactionsReport/Invoice')],
            [first_invoice.name],
        )
        self.assertEqual(
            [node.findtext('ID') for node in second_xml.findall('./TransactionsReport/Invoice')],
            [second_invoice.name],
        )

    def test_payment_flow_is_not_auto_sent_before_due_date(self):
        invoice = self._create_reporting_invoice(
            partner=self.b2bi_customer,
            amount=100.0,
            invoice_date='2025-09-03',
            tax_ids=self._get_tax_on_payment_20(),
        )
        payment = self._register_payment(invoice, '2025-09-09')
        flow = payment.move_id.l10n_fr_pdp_last_flow_id

        self._run_send_cron('2025-10-09')
        flow.invalidate_recordset(['state', 'payload_id'])

        self.assertRecordValues(flow, [{
            'report_type': 'payment',
            'operation_type': 'sale',
            'state': 'ready',
        }])
        self.assertFalse(flow.payload_id)

    def test_payment_flow_is_auto_sent_on_due_date(self):
        invoice = self._create_reporting_invoice(
            partner=self.b2bi_customer,
            amount=100.0,
            invoice_date='2025-09-03',
            tax_ids=self._get_tax_on_payment_20(),
        )
        payment = self._register_payment(invoice, '2025-09-09')
        payment_move = payment.move_id
        flow = payment_move.l10n_fr_pdp_last_flow_id

        self._run_send_cron('2025-10-10', identifier='FLOW-PAYMENT-CRON-DUE')
        flow.invalidate_recordset(['state', 'payload_id'])
        payment_move.invalidate_recordset(['l10n_fr_pdp_sent_in_flow_ids'])

        self.assertRecordValues(flow, [{
            'report_type': 'payment',
            'operation_type': 'sale',
            'state': 'sent',
        }])
        self.assertTrue(flow.payload_id)
        self.assertIn(flow, payment_move.l10n_fr_pdp_sent_in_flow_ids)

    def test_b2c_service_invoice_then_payment_creates_transaction_and_payment_flows(self):
        invoice = self._create_reporting_invoice(
            partner=self.b2c_customer,
            amount=120.0,
            invoice_date='2025-09-03',
            tax_ids=self._get_tax_on_payment_20_tax_included(),
        )
        payment = self._register_payment(invoice, '2025-09-09')
        transaction_flow = invoice.l10n_fr_pdp_last_flow_id
        payment_flow = payment.move_id.l10n_fr_pdp_last_flow_id

        self.assertNotEqual(transaction_flow, payment_flow)
        self.assertRecordValues(transaction_flow | payment_flow, [
            {'report_type': 'transaction', 'operation_type': 'sale'},
            {'report_type': 'payment', 'operation_type': 'sale'},
        ])
        transaction_xml = self._build_flow_xml(transaction_flow)
        payment_xml = self._build_flow_xml(payment_flow)
        transaction = transaction_xml.find('./TransactionsReport/Transactions')
        payment_subtotal = payment_xml.find('./PaymentsReport/Transactions/Payment/SubTotals')

        self.assertEqual(transaction.findtext('CategoryCode'), 'TPS1')
        self.assertIsNotNone(payment_subtotal)
        self.assertAlmostEqual(float(payment_subtotal.findtext('Amount')), payment.amount, places=2)

    def test_b2bi_service_invoice_then_payment_creates_transaction_and_payment_flows(self):
        invoice = self._create_reporting_invoice(
            partner=self.b2bi_customer,
            amount=100.0,
            invoice_date='2025-09-03',
            tax_ids=self._get_tax_on_payment_20(),
        )
        payment = self._register_payment(invoice, '2025-09-09')
        transaction_flow = invoice.l10n_fr_pdp_last_flow_id
        payment_flow = payment.move_id.l10n_fr_pdp_last_flow_id

        self.assertNotEqual(transaction_flow, payment_flow)
        transaction_xml = self._build_flow_xml(transaction_flow)
        payment_xml = self._build_flow_xml(payment_flow)
        invoice_node = transaction_xml.find('./TransactionsReport/Invoice')
        payment_invoice_node = payment_xml.find('./PaymentsReport/Invoice')

        self.assertEqual(invoice_node.findtext('ID'), invoice.name)
        self.assertEqual(payment_invoice_node.findtext('InvoiceID'), invoice.name)
        self.assertAlmostEqual(
            float(payment_invoice_node.findtext('Payment/SubTotals/Amount')),
            payment.amount,
            places=2,
        )

    def test_vendor_bill_then_payment_creates_purchase_transaction_and_payment_flows(self):
        bill = self._create_reporting_vendor_bill(
            partner=self.b2bi_customer,
            amount=100.0,
            invoice_date='2025-09-03',
        )
        payment = self._register_payment(bill, '2025-09-09')
        transaction_flow = bill.l10n_fr_pdp_last_flow_id
        payment_flow = payment.move_id.l10n_fr_pdp_last_flow_id

        self.assertNotEqual(transaction_flow, payment_flow)
        self.assertRecordValues(transaction_flow | payment_flow, [
            {'report_type': 'transaction', 'operation_type': 'purchase'},
            {'report_type': 'payment', 'operation_type': 'purchase'},
        ])
        transaction_xml = self._build_flow_xml(transaction_flow)
        payment_xml = self._build_flow_xml(payment_flow)

        self.assertEqual(transaction_xml.findtext('./ReportDocument/Issuer/RoleCode'), 'BY')
        self.assertEqual(payment_xml.findtext('./ReportDocument/Issuer/RoleCode'), 'BY')
        self.assertEqual(transaction_xml.findtext('./TransactionsReport/Invoice/ID'), bill.name)
        self.assertEqual(payment_xml.findtext('./PaymentsReport/Invoice/InvoiceID'), bill.name)

    def test_b2c_mixed_goods_services_invoice_reports_distinct_transaction_categories(self):
        goods_tax = self._get_tax_sale_good_20_tax_included()
        service_tax = self._get_tax_on_payment_20_tax_included()
        invoice = self._create_reporting_invoice_with_lines(
            partner=self.b2c_customer,
            invoice_date='2025-09-03',
            lines=[
                {'price_unit': 120.0, 'tax_ids': goods_tax},
                {'price_unit': 60.0, 'tax_ids': service_tax},
            ],
        )
        goods_line = invoice.invoice_line_ids.filtered(lambda line: goods_tax in line.tax_ids)
        service_line = invoice.invoice_line_ids.filtered(lambda line: service_tax in line.tax_ids)

        xml = self._build_flow_xml(invoice.l10n_fr_pdp_last_flow_id)
        transactions = {
            node.findtext('CategoryCode'): node
            for node in xml.findall('./TransactionsReport/Transactions')
        }

        self.assertEqual(set(transactions), {'TLB1', 'TPS1'})
        self.assertAlmostEqual(
            float(transactions['TLB1'].findtext('TaxExclusiveAmount')),
            goods_line.price_subtotal,
            places=2,
        )
        self.assertAlmostEqual(
            float(transactions['TLB1'].findtext('TaxTotal')),
            goods_line.price_total - goods_line.price_subtotal,
            places=2,
        )
        self.assertAlmostEqual(
            float(transactions['TPS1'].findtext('TaxExclusiveAmount')),
            service_line.price_subtotal,
            places=2,
        )
        self.assertAlmostEqual(
            float(transactions['TPS1'].findtext('TaxTotal')),
            service_line.price_total - service_line.price_subtotal,
            places=2,
        )

    def test_credit_note_after_sent_invoice_creates_rectificative_transaction_flow(self):
        invoice = self._create_reporting_invoice(
            partner=self.b2bi_customer,
            invoice_date='2025-09-03',
        )
        initial_flow = invoice.l10n_fr_pdp_last_flow_id

        self._run_send_cron('2025-09-20', identifier='FLOW-CREDIT-ORIGIN-SENT')
        invoice.invalidate_recordset(['l10n_fr_pdp_sent_in_flow_ids'])
        refund = self._create_reporting_credit_note(
            invoice,
            invoice_date='2025-09-04',
        )
        rectificative_flow = refund.l10n_fr_pdp_last_flow_id

        self.assertIn(initial_flow, invoice.l10n_fr_pdp_sent_in_flow_ids)
        self.assertNotEqual(initial_flow, rectificative_flow)
        self.assertRecordValues(rectificative_flow, [{
            'report_type': 'transaction',
            'operation_type': 'sale',
            'transmission_type': 'rectificative',
            'initial_flow_id': initial_flow.id,
        }])
        xml = self._build_flow_xml(rectificative_flow)
        reported_invoices = {
            node.findtext('ID'): node
            for node in xml.findall('./TransactionsReport/Invoice')
        }
        refund_node = reported_invoices[refund.name]
        self.assertEqual(xml.findtext('./ReportDocument/TypeCode'), 'RE')
        self.assertEqual(refund_node.findtext('TypeCode'), '381')
        self.assertEqual(refund_node.findtext('ReferencedDocument/ID'), invoice.name)

    def test_credit_note_before_flow_send_stays_in_initial_transaction_flow(self):
        invoice = self._create_reporting_invoice(
            partner=self.b2bi_customer,
            invoice_date='2025-09-03',
        )
        initial_flow = invoice.l10n_fr_pdp_last_flow_id
        refund = self._create_reporting_credit_note(
            invoice,
            invoice_date='2025-09-04',
        )
        self.assertEqual(refund.l10n_fr_pdp_last_flow_id, initial_flow)
        self.assertEqual(initial_flow.transmission_type, 'initial')
        xml = self._build_flow_xml(initial_flow)
        reported_invoices = {
            node.findtext('ID'): node
            for node in xml.findall('./TransactionsReport/Invoice')
        }
        refund_node = reported_invoices[refund.name]

        self.assertEqual(set(reported_invoices), {invoice.name, refund.name})
        self.assertEqual(refund_node.findtext('TypeCode'), '381')
        self.assertEqual(refund_node.findtext('ReferencedDocument/ID'), invoice.name)

    def test_repeated_recompute_does_not_create_duplicate_flow(self):
        invoice = self._create_reporting_invoice(
            partner=self.b2bi_customer,
            invoice_date='2025-09-03',
        )
        initial_flow = invoice.l10n_fr_pdp_last_flow_id

        self._refresh_pdp_fields(invoice)
        flows = self.env['l10n.fr.pdp.reports.flow'].search([
            ('company_id', '=', self.company.id),
            ('report_type', '=', 'transaction'),
            ('operation_type', '=', 'sale'),
            ('period_start', '=', fields.Date.to_date('2025-09-01')),
            ('period_end', '=', fields.Date.to_date('2025-09-10')),
        ])

        self.assertEqual(invoice.l10n_fr_pdp_last_flow_id, initial_flow)
        self.assertEqual(len(flows), 1)

    def test_repeated_cron_does_not_resend_sent_flow(self):
        invoice = self._create_reporting_invoice(
            partner=self.b2bi_customer,
            invoice_date='2025-09-03',
        )
        flow = invoice.l10n_fr_pdp_last_flow_id

        with patch('odoo.fields.Date.today', return_value=fields.Date.to_date('2025-09-20')):
            with patch(
                'odoo.addons.l10n_fr_pdp.models.pdp_flow.PdpFlow._send_to_proxy',
                return_value=self._proxy_success_response('FLOW-CRON-IDEMPOTENT'),
            ) as send_mock:
                self.env['l10n.fr.pdp.reports.flow']._cron_process_company(self.company)
                self.env['l10n.fr.pdp.reports.flow']._cron_process_company(self.company)

        flow.invalidate_recordset(['state'])
        invoice.invalidate_recordset(['l10n_fr_pdp_sent_in_flow_ids'])
        self.assertEqual(send_mock.call_count, 1)
        self.assertEqual(flow.state, 'sent')
        self.assertEqual(invoice.l10n_fr_pdp_sent_in_flow_ids, flow)

    def test_draft_and_cancelled_invoices_are_excluded_from_ready_payload(self):
        kept_invoice = self._create_reporting_invoice(
            partner=self.b2bi_customer,
            invoice_date='2025-09-03',
        )
        draft_invoice = self._create_reporting_invoice(
            partner=self.b2bi_customer,
            invoice_date='2025-09-03',
        )
        cancelled_invoice = self._create_reporting_invoice(
            partner=self.b2bi_customer,
            invoice_date='2025-09-03',
        )
        flow = kept_invoice.l10n_fr_pdp_last_flow_id

        draft_invoice.with_context(l10n_fr_pdp_bypass_draft_check=True).button_draft()
        cancelled_invoice.button_cancel()
        self._refresh_pdp_fields(draft_invoice | cancelled_invoice)
        xml = self._build_flow_xml(flow)
        reported_ids = [
            node.findtext('ID')
            for node in xml.findall('./TransactionsReport/Invoice')
        ]

        self.assertEqual(reported_ids, [kept_invoice.name])
        self.assertNotIn(draft_invoice, flow._get_moves())
        self.assertNotIn(cancelled_invoice, flow._get_moves())

    def test_multiple_b2c_transactions_same_day_and_category_are_aggregated(self):
        tax = self._get_tax_sale_good_20_tax_included()
        first_invoice = self._create_reporting_invoice(
            partner=self.b2c_customer,
            amount=120.0,
            invoice_date='2025-09-03',
            tax_ids=tax,
        )
        second_invoice = self._create_reporting_invoice(
            partner=self.b2c_customer,
            amount=240.0,
            invoice_date='2025-09-03',
            tax_ids=tax,
        )

        self.assertEqual(first_invoice.l10n_fr_pdp_last_flow_id, second_invoice.l10n_fr_pdp_last_flow_id)
        xml = self._build_flow_xml(first_invoice.l10n_fr_pdp_last_flow_id)
        transactions = xml.findall('./TransactionsReport/Transactions')

        self.assertEqual(len(transactions), 1)
        self.assertEqual(transactions[0].findtext('CategoryCode'), 'TLB1')
        self.assertAlmostEqual(
            float(transactions[0].findtext('TaxExclusiveAmount')),
            first_invoice.amount_untaxed + second_invoice.amount_untaxed,
            places=2,
        )
        self.assertAlmostEqual(
            float(transactions[0].findtext('TaxTotal')),
            first_invoice.amount_tax + second_invoice.amount_tax,
            places=2,
        )

    def test_multiple_b2bi_invoices_in_same_period_remain_individual_in_payload(self):
        invoices = self._create_reporting_invoice(
            partner=self.b2bi_customer,
            invoice_date='2025-09-03',
        ) | self._create_reporting_invoice(
            partner=self.b2bi_customer,
            invoice_date='2025-09-04',
        )
        flow = invoices[0].l10n_fr_pdp_last_flow_id

        self.assertEqual(flow, invoices[1].l10n_fr_pdp_last_flow_id)
        xml = self._build_flow_xml(flow)
        reported_ids = [
            node.findtext('ID')
            for node in xml.findall('./TransactionsReport/Invoice')
        ]

        self.assertEqual(Counter(reported_ids), Counter(invoices.mapped('name')))

    def test_partial_then_final_payment_reports_each_collection_once(self):
        invoice = self._create_reporting_invoice(
            partner=self.b2bi_customer,
            amount=100.0,
            invoice_date='2025-09-03',
            tax_ids=self._get_tax_on_payment_20(),
        )
        first_payment = self._register_payment(invoice, '2025-09-09', amount=40.0)
        second_payment = self._register_payment(invoice, '2025-09-10', amount=invoice.amount_residual)
        payment_flow = first_payment.move_id.l10n_fr_pdp_last_flow_id

        self.assertEqual(second_payment.move_id.l10n_fr_pdp_last_flow_id, payment_flow)
        xml = self._build_flow_xml(payment_flow)
        payment_invoices = xml.findall('./PaymentsReport/Invoice')
        amounts = [
            float(node.findtext('Payment/SubTotals/Amount'))
            for node in payment_invoices
        ]

        self.assertEqual(len(payment_invoices), 2)
        self.assertEqual(
            Counter(node.findtext('InvoiceID') for node in payment_invoices),
            Counter({invoice.name: 2}),
        )
        self.assertCountEqual(amounts, [first_payment.amount, second_payment.amount])
        self.assertAlmostEqual(sum(amounts), first_payment.amount + second_payment.amount, places=2)

    def test_report_header_issue_datetime_uses_required_format(self):
        invoice = self._create_reporting_invoice(
            partner=self.b2bi_customer,
            invoice_date='2025-09-03',
        )

        xml = self._build_flow_xml(invoice.l10n_fr_pdp_last_flow_id)
        issue_datetime = xml.find('./ReportDocument/IssueDateTime/DateTimeString')

        self.assertIsNotNone(issue_datetime)
        self.assertRegex(issue_datetime.text or '', r'^\d{14}$')

    def test_b2bi_invoice_line_reports_gross_price_without_discount(self):
        invoice = self._create_reporting_invoice(
            partner=self.b2bi_customer,
            amount=100.0,
            invoice_date='2025-09-03',
        )

        xml = self._build_flow_xml(invoice.l10n_fr_pdp_last_flow_id)
        price = xml.find('./TransactionsReport/Invoice/Line/Price')
        allowance_charge_amount = price.findtext('AllowanceChargeAmount')

        self.assertIsNotNone(price)
        if allowance_charge_amount:
            self.assertEqual(float(allowance_charge_amount), 0.0)
        self.assertEqual(
            float(price.findtext('PriceAmount')),
            float(price.findtext('AllowanceChargeBaseAmount')),
        )

    def test_b2bi_discounted_line_reports_consistent_net_gross_and_allowance(self):
        invoice = self._create_reporting_invoice_with_lines(
            partner=self.b2bi_customer,
            invoice_date='2025-09-03',
            lines=[{
                'price_unit': 125.0,
                'quantity': 2.0,
                'discount': 20.0,
                'tax_ids': self._get_tax_on_payment_20(),
            }],
        )

        xml = self._build_flow_xml(invoice.l10n_fr_pdp_last_flow_id)
        price = xml.find('./TransactionsReport/Invoice/Line/Price')
        net_price = float(price.findtext('PriceAmount'))
        discount = float(price.findtext('AllowanceChargeAmount'))
        gross_price = float(price.findtext('AllowanceChargeBaseAmount'))

        self.assertAlmostEqual(net_price, gross_price - discount, places=2)

    def test_b2bi_invoice_tax_totals_match_tax_subtotals(self):
        invoice = self._create_reporting_invoice_with_lines(
            partner=self.b2bi_customer,
            invoice_date='2025-09-03',
            lines=[
                {'price_unit': 100.0, 'tax_ids': self._get_tax_on_payment_20()},
                {'price_unit': 50.0, 'tax_ids': self._get_tax_on_payment()},
            ],
        )

        xml = self._build_flow_xml(invoice.l10n_fr_pdp_last_flow_id)
        invoice_node = xml.find('./TransactionsReport/Invoice')
        tax_subtotals = invoice_node.findall('TaxSubTotal')
        taxable_amount = sum(float(node.findtext('TaxableAmount')) for node in tax_subtotals)
        tax_amount = sum(float(node.findtext('TaxAmount')) for node in tax_subtotals)

        self.assertGreaterEqual(len(tax_subtotals), 2)
        self.assertAlmostEqual(
            taxable_amount,
            float(invoice_node.findtext('MonetaryTotal/TaxExclusiveAmount')),
            places=2,
        )
        self.assertAlmostEqual(
            tax_amount,
            float(invoice_node.findtext('MonetaryTotal/TaxAmount')),
            places=2,
        )

    def test_invalid_invoice_identifier_is_rejected_for_flow_reporting(self):
        invoice = self._create_reporting_invoice(
            partner=self.b2bi_customer,
            invoice_date='2025-09-03',
            name='INVALID_IDENTIFIER_123456789',
        )

        self.assertRecordValues(invoice, [{
            'l10n_fr_pdp_has_error': True,
            'l10n_fr_pdp_status': 'error',
        }])

    def test_b2c_transaction_flow_is_sent_by_cron_with_form(self):
        invoice = self._create_form_invoice(
            partner=self.b2c_customer,
            invoice_date='2025-09-03',
            lines=[{
                'price_unit': 120.0,
                'tax_ids': self._get_tax_on_payment_20_tax_included(),
            }],
        )
        flow = invoice.l10n_fr_pdp_last_flow_id

        self._run_send_cron('2025-09-20', identifier='FULL-FORM-B2C')

        self.assertRecordValues(flow, [{'state': 'sent'}])
        self.assertTrue(flow.payload_id)
        xml = etree.fromstring(flow.payload_id.raw.content)
        transactions = xml.findall('./TransactionsReport/Transactions')

        self.assertFalse(xml.findall('./TransactionsReport/Invoice'))
        self.assertEqual(len(transactions), 1)
        self.assertEqual(transactions[0].findtext('CategoryCode'), 'TPS1')
        self.assertIn(invoice, flow.sent_move_ids)

    def test_b2bi_transaction_flow_is_sent_by_cron_with_form(self):
        invoice = self._create_form_invoice(
            partner=self.b2bi_customer,
            invoice_date='2025-09-03',
            lines=[{
                'price_unit': 100.0,
                'tax_ids': self._get_tax_on_payment_20(),
            }],
        )
        flow = invoice.l10n_fr_pdp_last_flow_id

        self._run_send_cron('2025-09-20', identifier='FULL-FORM-B2BI')

        self.assertRecordValues(flow, [{'state': 'sent'}])
        self.assertTrue(flow.payload_id)
        xml = etree.fromstring(flow.payload_id.raw.content)
        invoice_nodes = xml.findall('./TransactionsReport/Invoice')

        self.assertEqual(len(invoice_nodes), 1)
        self.assertEqual(invoice_nodes[0].findtext('ID'), invoice.name)
        self.assertFalse(xml.findall('./TransactionsReport/Transactions'))
        self.assertIn(invoice, flow.sent_move_ids)

    def test_mixed_transaction_flow_aggregates_and_sends_with_form(self):
        goods_tax = self._get_tax_sale_good_20_tax_included()
        service_tax = self._get_tax_on_payment_20_tax_included()
        b2bi_invoice = self._create_form_invoice(
            partner=self.b2bi_customer,
            invoice_date='2025-09-03',
            lines=[{
                'price_unit': 100.0,
                'tax_ids': self._get_tax_on_payment_20(),
            }],
        )
        first_b2c_goods_invoice = self._create_form_invoice(
            partner=self.b2c_customer,
            invoice_date='2025-09-03',
            lines=[{
                'price_unit': 120.0,
                'tax_ids': goods_tax,
            }],
        )
        second_b2c_goods_invoice = self._create_form_invoice(
            partner=self.b2c_customer,
            invoice_date='2025-09-03',
            lines=[{
                'price_unit': 240.0,
                'tax_ids': goods_tax,
            }],
        )
        b2c_service_invoice = self._create_form_invoice(
            partner=self.b2c_customer,
            invoice_date='2025-09-03',
            lines=[{
                'price_unit': 60.0,
                'tax_ids': service_tax,
            }],
        )
        flow = b2bi_invoice.l10n_fr_pdp_last_flow_id

        self._run_send_cron('2025-09-20', identifier='FULL-FORM-MIXED')

        self.assertRecordValues(flow, [{'state': 'sent'}])
        self.assertTrue(flow.payload_id)
        xml = etree.fromstring(flow.payload_id.raw.content)
        invoice_nodes = xml.findall('./TransactionsReport/Invoice')
        transactions = {
            node.findtext('CategoryCode'): node
            for node in xml.findall('./TransactionsReport/Transactions')
        }

        self.assertEqual([node.findtext('ID') for node in invoice_nodes], [b2bi_invoice.name])
        self.assertEqual(set(transactions), {'TLB1', 'TPS1'})
        self.assertAlmostEqual(
            float(transactions['TLB1'].findtext('TaxExclusiveAmount')),
            first_b2c_goods_invoice.amount_untaxed + second_b2c_goods_invoice.amount_untaxed,
            places=2,
        )
        self.assertAlmostEqual(
            float(transactions['TPS1'].findtext('TaxExclusiveAmount')),
            b2c_service_invoice.amount_untaxed,
            places=2,
        )
        self.assertEqual(
            set(flow.sent_move_ids.ids),
            set((b2bi_invoice | first_b2c_goods_invoice | second_b2c_goods_invoice | b2c_service_invoice).ids),
        )

    def test_error_move_creates_and_sends_rectificative_flow_with_form(self):
        valid_invoice = self._create_form_invoice(
            partner=self.b2bi_customer,
            invoice_date='2025-09-03',
            lines=[{
                'price_unit': 100.0,
                'tax_ids': self._get_tax_on_payment_20(),
            }],
        )
        invalid_invoice = self._create_form_invoice(
            partner=self.b2bi_invalid_customer,
            invoice_date='2025-09-03',
            lines=[{
                'price_unit': 200.0,
                'tax_ids': self._get_tax_on_payment_20(),
            }],
        )
        initial_flow = valid_invoice.l10n_fr_pdp_last_flow_id

        self._run_send_cron('2025-09-20', identifier='FULL-FORM-RE-INITIAL')
        rectificative_flow = invalid_invoice.l10n_fr_pdp_last_flow_id

        self.assertRecordValues(initial_flow, [{'state': 'sent'}])
        self.assertIn(valid_invoice, initial_flow.sent_move_ids)
        self.assertNotIn(invalid_invoice, initial_flow.sent_move_ids)
        self.assertNotEqual(initial_flow, rectificative_flow)
        self.assertRecordValues(rectificative_flow, [{
            'state': 'ready',
            'transmission_type': 'rectificative',
            'initial_flow_id': initial_flow.id,
        }])

        self._correct_partner(invalid_invoice)
        self._run_send_cron('2025-09-21', identifier='FULL-FORM-RE-SENT')

        self.assertRecordValues(rectificative_flow, [{'state': 'sent'}])
        self.assertTrue(rectificative_flow.payload_id)
        xml = etree.fromstring(rectificative_flow.payload_id.raw.content)
        invoice_nodes = xml.findall('./TransactionsReport/Invoice')

        self.assertEqual(xml.findtext('./ReportDocument/TypeCode'), 'RE')
        self.assertIn(invalid_invoice.name, [node.findtext('ID') for node in invoice_nodes])
        self.assertIn(invalid_invoice, rectificative_flow.sent_move_ids)
