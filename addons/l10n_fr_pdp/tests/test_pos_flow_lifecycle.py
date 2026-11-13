from unittest import SkipTest
from unittest.mock import patch

from lxml import etree

from odoo import Command, fields
from odoo.modules.registry import Registry
from odoo.tests import tagged
from odoo.tests.common import get_db_name

# POS is optional: setUpClass skips these integration tests when it is not installed.
from odoo.addons.point_of_sale.tests.common import TestPoSCommon  # noqa: OLS03003


@tagged('post_install_l10n', 'post_install', '-at_install', 'test_pos_flow_lifecycle')
class TestPdpPosFlowLifecycle(TestPoSCommon):
    @classmethod
    def setUpClass(cls):
        if 'pos.config' not in Registry(get_db_name()):
            raise SkipTest('Point of Sale is not installed')
        super().setUpClass()

        cls.company = cls.company_data['company']
        cls.env = cls.env(context=dict(cls.env.context, allowed_company_ids=[cls.company.id]))

        def compute_l10n_fr_f10_enable_reporting_for_pos_tests(companies):
            for company in companies:
                company.l10n_fr_f10_enable_reporting = True

        cls.startClassPatcher(patch.object(
            cls.env.registry['res.company'], '_compute_l10n_fr_f10_enable_reporting',
            compute_l10n_fr_f10_enable_reporting_for_pos_tests,
        ))

        cls.company.write({
            'account_fiscal_country_id': cls.env.ref('base.fr').id,
            'country_id': cls.env.ref('base.fr').id,
            'currency_id': cls.env.ref('base.EUR').id,
            'email': 'pos-company@example.com',
            'l10n_fr_pdp_annuaire_start_date': '2025-01-01',
            'l10n_fr_pdp_periodicity': 'normal_monthly',
            'l10n_fr_pdp_send_to_ppf': True,
            'name': 'PDP POS Company',
            'vat': 'FR23334175221',
        })
        cls.company.partner_id._set_additional_identifier('FR_SIRET', '34057796400026')
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
        cash_basis_transition_account = cls.tax_received_account.copy()
        cash_basis_transition_account.reconcile = True
        cls.pos_service_tax_20 = cls.pos_tax_20.copy({
            'name': 'POS Service VAT 20%',
            'tax_exigibility': 'on_payment',
            'cash_basis_transition_account_id': cash_basis_transition_account.id,
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

    def _create_closed_pos_session(self, orders, date='2025-09-03'):
        with self.mock_datetime_and_now(date + ' 12:00:00'):
            session = self.open_new_session()
            self.env['pos.order'].sync_from_ui([  # noqa: OLS03001
                self.create_ui_order_data(**order_vals)
                for order_vals in orders
            ])
            session.close_session_from_ui()
        return session

    def _create_pos_order_data(self, lines, payments=None):
        order_data = {
            'pos_order_lines_ui_args': lines,
        }
        if payments:
            order_data['payments'] = payments
        return order_data

    def _build_flow_xml(self, flow):
        flow._build_payload()
        self.assertTrue(flow.payload_id)
        return etree.fromstring(flow.payload_id.raw.content)

    def _transaction_nodes(self, flow):
        return self._build_flow_xml(flow).findall('./TransactionsReport/Transactions')

    def test_pos_closing_invoice_is_reportable_b2c_transaction(self):
        """Session closing invoices use the regular sale scope and transaction query."""
        session = self._create_closed_pos_session([
            self._create_pos_order_data([(self.pos_product, 1)]),
        ])

        pos_moves = session.sale_move_ids
        self.assertTrue(pos_moves)
        self.assertTrue(pos_moves.is_sale_document(include_receipts=True))
        self.assertRecordValues(pos_moves, [{
            'move_type': 'out_invoice',
            'l10n_fr_pdp_flow_10_operation_type': 'sale',
            'l10n_fr_pdp_flow_10_report_type': 'transaction',
            'l10n_fr_pdp_status': 'pending',
        }])
        self.assertRecordValues(pos_moves.l10n_fr_pdp_last_flow_id, [{
            'operation_type': 'sale',
            'report_type': 'transaction',
            'period_start': fields.Date.to_date('2025-09-01'),
            'period_end': fields.Date.to_date('2025-09-10'),
        }])

        self.company._force_update_l10n_fr_f10_moves()
        self.assertEqual(pos_moves.l10n_fr_pdp_flow_10_report_type, 'transaction')
        xml = self._build_flow_xml(session.sale_move_ids.l10n_fr_pdp_last_flow_id)
        self.assertFalse(xml.findall('./TransactionsReport/Invoice'))
        transaction = xml.find('./TransactionsReport/Transactions')
        self.assertEqual(transaction.findtext('CategoryCode'), 'TLB1')
        self.assertAlmostEqual(float(transaction.findtext('TaxExclusiveAmount')), 100.0, places=2)
        self.assertAlmostEqual(float(transaction.findtext('TaxTotal')), 20.0, places=2)

    def test_pos_goods_only_closing_invoice_does_not_create_payment_flow(self):
        """A paid goods ticket must not produce a service payment report."""
        session = self._create_closed_pos_session([
            self._create_pos_order_data([(self.pos_product, 1)]),
        ])

        self.assertFalse(session.sale_move_ids._l10n_fr_pdp_get_matched_transactions())
        payment_flows = self.env['l10n.fr.pdp.reports.flow'].search([
            ('company_id', '=', self.company.id),
            ('operation_type', '=', 'sale'),
            ('report_type', '=', 'payment'),
        ])
        self.assertFalse(payment_flows)

    def test_pos_goods_and_services_paid_cash_and_card_create_transaction_and_service_payment_flows(self):
        """Keep goods and services distinct, and report reconciled service collections."""
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

        transaction_flows = session.sale_move_ids.l10n_fr_pdp_last_flow_id
        self.assertEqual(len(session.order_ids), 5)
        self.assertEqual(transaction_flows._get_moves(), session.sale_move_ids)

        transactions = {
            node.findtext('CategoryCode'): node
            for node in self._transaction_nodes(transaction_flows)
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

    def test_pos_closing_refund_is_reportable_transaction(self):
        """Session refunds must use the regular credit note scope without a POS override."""
        session = self._create_closed_pos_session([
            self._create_pos_order_data([(self.pos_product, 2)]),
            self._create_pos_order_data([(self.pos_product, -1)]),
        ])
        self.assertEqual(session.refund_move_ids.move_type, 'out_refund')
        self.assertAlmostEqual(session.refund_move_ids.amount_untaxed, 100.0, places=2)
        self.assertEqual(session.refund_move_ids.l10n_fr_pdp_flow_10_report_type, 'transaction')
        flow = session.sale_move_ids.l10n_fr_pdp_last_flow_id
        self.assertEqual(session.refund_move_ids.l10n_fr_pdp_last_flow_id, flow)
        self.company._force_update_l10n_fr_f10_moves()
        self.assertIn(session.refund_move_ids, flow._get_moves())

    def test_ubl_21_fr_invoice_pdf_with_incomplete_edi_data(self):
        """
        Tests that requesting an invoice for a client with ubl_21_fr set but
        incomplete e-invoicing information still produces a regular invoice PDF
        instead of falling back to a Pro-Forma one.
        """
        bad_partner = self.env['res.partner'].create({
            'name': 'Error',
            'country_id': self.env.ref('base.fr').id,
            'is_company': True,
            'invoice_edi_format': 'ubl_21_fr',
        })

        with self.mock_datetime_and_now('2025-09-03 12:00:00'):
            session = self.open_new_session()
            order_data = self.create_ui_order_data([(self.pos_product, 1)])
            order_data['partner_id'] = bad_partner.id
            order_data['to_invoice'] = True
            self.env['pos.order'].sync_from_ui([order_data])  # noqa: OLS03001
            session.close_session_from_ui()

        order = self.env['pos.order'].search([('session_id', '=', session.id)], limit=1)  # noqa: OLS03001
        # An invoiced ticket is reported through its invoice, not a second closing sale.
        self.assertFalse(session.sale_move_ids)
        self.assertEqual(order.account_move.l10n_fr_pdp_last_flow_id._get_moves(), order.account_move)
        self.assertFalse(order.account_move.with_context(sending_method=['email'])._need_ubl_cii_xml('ubl_21_fr'))
        self.env['account.move.send']._generate_and_send_invoices(
            order.account_move, allow_fallback_pdf=True, sending_methods=['email'],
        )
        self.assertTrue(order.account_move.invoice_pdf_report_file)
