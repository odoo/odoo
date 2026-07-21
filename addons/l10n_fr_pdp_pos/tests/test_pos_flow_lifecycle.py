from contextlib import contextmanager
from lxml import etree
from unittest.mock import patch

from odoo import Command, fields
from odoo.tests import tagged

from odoo.addons.point_of_sale.tests.common import TestPoSCommon


@tagged('post_install_l10n', 'post_install', '-at_install', 'test_pos_flow_lifecycle')
class TestPdpPosFlowLifecycle(TestPoSCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.company = cls.company_data['company']
        cls.env = cls.env(context=dict(cls.env.context, allowed_company_ids=[cls.company.id]))

        def compute_l10n_fr_f10_enable_reporting_for_pos_tests(companies):
            for company in companies:
                company.l10n_fr_f10_enable_reporting = True

        cls.startClassPatcher(patch(
            'odoo.addons.l10n_fr_pdp.models.res_company.ResCompany._compute_l10n_fr_f10_enable_reporting',
            compute_l10n_fr_f10_enable_reporting_for_pos_tests,
        ))

        cls.company.write({
            'account_fiscal_country_id': cls.env.ref('base.fr').id,
            'country_id': cls.env.ref('base.fr').id,
            'currency_id': cls.env.ref('base.EUR').id,
            'email': 'pos-company@example.com',
            'l10n_fr_pdp_annuaire_start_date': '2025-01-01',
            'l10n_fr_pdp_periodicity': 'normal_monthly',
            'l10n_fr_pdp_pilot_phase': True,
            'l10n_fr_pdp_send_to_ppf': True,
            'name': 'PDP POS Company',
            'siret': '34057796400024',
            'vat': 'FR23334175221',
        })
        cls.company.partner_id.write({
            'country_id': cls.env.ref('base.fr').id,
            'street': '1 rue du POS',
            'zip': '75001',
            'city': 'Paris',
            'vat': 'FR23334175221',
        })
        cls.currency_pricelist.currency_id = cls.company.currency_id

        cls.company._compute_l10n_fr_f10_enable_reporting()

        tax_group = cls.env['account.tax.group'].search([
            ('country_id', '=', cls.env.ref('base.fr').id),
        ], limit=1) or cls.env['account.tax.group'].create({
            'name': 'France VAT',
            'country_id': cls.env.ref('base.fr').id,
        })
        cls.pos_tax_20 = cls.env['account.tax'].create({
            'name': 'POS VAT 20%',
            'amount': 20.0,
            'amount_type': 'percent',
            'type_tax_use': 'sale',
            'company_id': cls.company.id,
            'tax_group_id': tax_group.id,
            'tax_scope': 'consu',
            'invoice_repartition_line_ids': [
                Command.create({'repartition_type': 'base'}),
                Command.create({
                    'repartition_type': 'tax',
                    'account_id': cls.tax_received_account.id,
                }),
            ],
            'refund_repartition_line_ids': [
                Command.create({'repartition_type': 'base'}),
                Command.create({
                    'repartition_type': 'tax',
                    'account_id': cls.tax_received_account.id,
                }),
            ],
        })
        cls.pos_service_tax_20 = cls.pos_tax_20.copy({
            'name': 'POS Service VAT 20%',
            'tax_exigibility': 'on_payment',
            'tax_scope': 'service',
        })
        cls.pos_product = cls.create_product(
            'PDP POS Product',
            cls.categ_basic,
            100.0,
            tax_ids=cls.pos_tax_20.ids,
            sale_account=cls.sale_account,
        )
        cls.pos_service = cls.create_product(
            'PDP POS Service',
            cls.categ_basic,
            150.0,
            tax_ids=cls.pos_service_tax_20.ids,
            sale_account=cls.sale_account,
        )

    def setUp(self):
        super().setUp()
        self.config = self.basic_config

    @contextmanager
    def _patch_pos_date(self, date):
        date = fields.Date.to_date(date)
        datetime_value = fields.Datetime.to_datetime(f'{date} 12:00:00')
        with (
            patch('odoo.fields.Date.context_today', return_value=date),
            patch('odoo.fields.Date.today', return_value=date),
            patch('odoo.fields.Datetime.now', return_value=datetime_value),
        ):
            yield

    def _create_closed_pos_session(self, orders, date='2025-09-03'):
        with self._patch_pos_date(date):
            session = self.open_new_session()
            self.env['pos.order'].sync_from_ui([
                self.create_ui_order_data(**order_vals)
                for order_vals in orders
            ])
            session.action_pos_session_validate()
        return session

    def _create_pos_order_data(self, lines, payments=None):
        order_data = {
            'pos_order_lines_ui_args': lines,
        }
        if payments:
            order_data['payments'] = payments
        return order_data

    def _proxy_success_response(self, identifier='POS-FLOW-TEST-001'):
        return {
            'id': identifier,
            'uid': identifier,
            'uuid': identifier,
            'flow_id': identifier,
            'status': 'DRAFT',
            'message': '',
            'acknowledgement': [],
        }

    def _run_send_cron(self, date, identifier='POS-FLOW-TEST-001'):
        with (
            patch('odoo.fields.Date.today', return_value=fields.Date.to_date(date)),
            patch(
                'odoo.addons.l10n_fr_pdp.models.pdp_flow.PdpFlow._send_to_proxy',
                return_value=self._proxy_success_response(identifier),
            ),
        ):
            self.env['l10n.fr.pdp.reports.flow']._cron_update_and_send_flows()

    def _build_flow_xml(self, flow):
        flow._build_payload()
        self.assertTrue(flow.payload_id)
        return etree.fromstring(flow.payload_id.raw)

    def _transaction_nodes(self, flow):
        return self._build_flow_xml(flow).findall('./TransactionsReport/Transactions')

    def test_pos_closing_entry_is_reportable_b2c_transaction(self):
        session = self._create_closed_pos_session([
            self._create_pos_order_data([(self.pos_product, 1)]),
        ])

        pos_move = session.move_id
        self.assertTrue(pos_move)
        self.assertTrue(pos_move._l10n_fr_pdp_reports_pos_is_transaction_entry())
        self.assertRecordValues(pos_move, [{
            'move_type': 'entry',
            'l10n_fr_pdp_flow_10_operation_type': 'sale',
            'l10n_fr_pdp_flow_10_report_type': 'transaction',
            'l10n_fr_pdp_status': 'ready',
        }])
        self.assertRecordValues(pos_move.l10n_fr_pdp_last_flow_id, [{
            'operation_type': 'sale',
            'report_type': 'transaction',
            'period_start': fields.Date.to_date('2025-09-01'),
            'period_end': fields.Date.to_date('2025-09-10'),
        }])

    def test_pos_closing_entry_creates_b2c_transaction_payload(self):
        session = self._create_closed_pos_session([
            self._create_pos_order_data([(self.pos_product, 1)]),
        ])

        xml = self._build_flow_xml(session.move_id.l10n_fr_pdp_last_flow_id)
        self.assertFalse(xml.findall('./TransactionsReport/Invoice'))
        transaction = xml.find('./TransactionsReport/Transactions')
        self.assertEqual(transaction.findtext('CategoryCode'), 'TLB1')
        self.assertAlmostEqual(float(transaction.findtext('TaxExclusiveAmount')), 100.0, places=2)
        self.assertAlmostEqual(float(transaction.findtext('TaxTotal')), 20.0, places=2)

    def test_pos_mixed_ticket_goods_and_services_create_distinct_aggregates(self):
        session = self._create_closed_pos_session([
            self._create_pos_order_data([(self.pos_product, 1), (self.pos_service, 1)]),
        ])

        transactions = self._transaction_nodes(session.move_id.l10n_fr_pdp_last_flow_id)
        amounts_by_category = {
            transaction.findtext('CategoryCode'): float(transaction.findtext('TaxExclusiveAmount'))
            for transaction in transactions
        }
        self.assertEqual(amounts_by_category, {
            'TLB1': 100.0,
            'TPS1': 150.0,
        })

    def test_pos_multiple_sessions_same_day_are_aggregated_in_same_flow(self):
        first_session = self._create_closed_pos_session([
            self._create_pos_order_data([(self.pos_product, 1)]),
        ])
        second_session = self._create_closed_pos_session([
            self._create_pos_order_data([(self.pos_product, 2)]),
        ])

        flow = first_session.move_id.l10n_fr_pdp_last_flow_id
        self.assertEqual(second_session.move_id.l10n_fr_pdp_last_flow_id, flow)
        transaction = self._transaction_nodes(flow)[0]
        self.assertAlmostEqual(float(transaction.findtext('TaxExclusiveAmount')), 300.0, places=2)
        self.assertAlmostEqual(float(transaction.findtext('TaxTotal')), 60.0, places=2)

    def test_pos_goods_only_closing_entry_does_not_create_payment_flow(self):
        session = self._create_closed_pos_session([
            self._create_pos_order_data([(self.pos_product, 1)]),
        ])

        self.assertFalse(session.move_id._l10n_fr_pdp_get_matched_transactions())
        payment_flows = self.env['l10n.fr.pdp.reports.flow'].search([
            ('company_id', '=', self.company.id),
            ('operation_type', '=', 'sale'),
            ('report_type', '=', 'payment'),
        ])
        self.assertFalse(payment_flows)

    def test_pos_goods_and_services_paid_cash_and_card_create_transaction_and_service_payment_flows(self):
        session = self._create_closed_pos_session([
            self._create_pos_order_data(
                [(self.pos_product, 1)],
                payments=[(self.cash_pm1, 120.0)],
            ),
            self._create_pos_order_data(
                [(self.pos_product, 2)],
                payments=[(self.bank_pm1, 240.0)],
            ),
            self._create_pos_order_data(
                [(self.pos_service, 1)],
                payments=[(self.cash_pm1, 180.0)],
            ),
            self._create_pos_order_data(
                [(self.pos_service, 2)],
                payments=[(self.bank_pm1, 360.0)],
            ),
            self._create_pos_order_data(
                [(self.pos_product, 1), (self.pos_service, 1)],
                payments=[(self.cash_pm1, 120.0), (self.bank_pm1, 180.0)],
            ),
        ])

        transaction_flow = session.move_id.l10n_fr_pdp_last_flow_id
        self.assertEqual(len(session.order_ids), 5)
        self.assertEqual(transaction_flow._get_moves(), session.move_id)

        transactions = {
            node.findtext('CategoryCode'): node
            for node in self._transaction_nodes(transaction_flow)
        }
        self.assertEqual(set(transactions), {'TLB1', 'TPS1'})
        self.assertAlmostEqual(float(transactions['TLB1'].findtext('TaxExclusiveAmount')), 400.0, places=2)
        self.assertAlmostEqual(float(transactions['TLB1'].findtext('TaxTotal')), 80.0, places=2)
        self.assertAlmostEqual(float(transactions['TPS1'].findtext('TaxExclusiveAmount')), 600.0, places=2)
        self.assertAlmostEqual(float(transactions['TPS1'].findtext('TaxTotal')), 120.0, places=2)

        payment_flows = self.env['l10n.fr.pdp.reports.flow'].search([
            ('company_id', '=', self.company.id),
            ('operation_type', '=', 'sale'),
            ('report_type', '=', 'payment'),
        ])
        self.assertTrue(payment_flows)

        payment_amount = sum(
            float(subtotal.findtext('Amount'))
            for flow in payment_flows
            for subtotal in self._build_flow_xml(flow).findall('./PaymentsReport/Transactions/Payment/SubTotals')
        )
        self.assertAlmostEqual(payment_amount, 720.0, places=2)

    def test_pos_transaction_flow_is_sent_by_cron(self):
        session = self._create_closed_pos_session([
            self._create_pos_order_data([(self.pos_product, 1)]),
        ])
        flow = session.move_id.l10n_fr_pdp_last_flow_id

        self._run_send_cron('2025-09-20', identifier='POS-FLOW-SENT')

        flow.invalidate_recordset(['state', 'payload_id', 'sent_move_ids'])
        self.assertRecordValues(flow, [{
            'state': 'sent',
        }])
        self.assertTrue(flow.payload_id)
        self.assertIn(session.move_id, flow.sent_move_ids)

    def test_pos_closing_entry_uses_correct_flow_period(self):
        session = self._create_closed_pos_session([
            self._create_pos_order_data([(self.pos_product, 1)]),
        ], date='2025-09-13')

        self.assertRecordValues(session.move_id.l10n_fr_pdp_last_flow_id, [{
            'period_start': fields.Date.to_date('2025-09-11'),
            'period_end': fields.Date.to_date('2025-09-20'),
            'due_period_start': fields.Date.to_date('2025-09-30'),
            'due_period_end': fields.Date.to_date('2025-09-30'),
        }])

    def test_regular_misc_entry_is_not_reported_as_pos_sale(self):
        move = self.env['account.move'].create({
            'journal_id': self.company_data['default_journal_misc'].id,
            'date': fields.Date.to_date('2025-09-03'),
            'line_ids': [
                Command.create({
                    'name': 'Debit',
                    'account_id': self.sales_account.id,
                    'debit': 100.0,
                }),
                Command.create({
                    'name': 'Credit',
                    'account_id': self.pos_receivable_account.id,
                    'credit': 100.0,
                }),
            ],
        })
        move.action_post()

        self.assertFalse(move._l10n_fr_pdp_reports_pos_is_transaction_entry())
        self.assertRecordValues(move, [{
            'l10n_fr_pdp_flow_10_operation_type': False,
            'l10n_fr_pdp_flow_10_report_type': False,
            'l10n_fr_pdp_status': 'out_of_scope',
        }])
