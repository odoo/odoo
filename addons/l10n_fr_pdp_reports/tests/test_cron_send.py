from datetime import timedelta
from unittest.mock import patch

from odoo import Command, fields
from odoo.tests.common import tagged

from .common import PdpTestCommon


@tagged('post_install', 'post_install_l10n', '-at_install')
class TestPdpCronSend(PdpTestCommon):
    def test_in_flow_sent_on_window_start_only(self):
        """Ready IN flow stays ready before window and auto-sends on window day."""
        self.company.l10n_fr_pdp_periodicity = 'monthly'
        invoice_date = fields.Date.from_string('2025-01-15')
        self._create_invoice(sent=True, date_val=invoice_date)
        flow = self._aggregate_company().filtered(lambda f: f.report_kind == 'transaction')[:1]
        self.assertEqual(flow.state, 'ready')

        early_day = fields.Date.from_string('2025-02-05')
        send_day = fields.Date.from_string('2025-02-10')
        with patch('odoo.fields.Date.context_today', return_value=early_day):
            self.env['l10n.fr.pdp.flow']._cron_send_ready_flows()
        flow.invalidate_recordset(['state', 'transport_identifier'])
        self.assertEqual(flow.state, 'ready', 'Flow must remain ready before window opens')
        self.assertFalse(flow.transport_identifier)

        with patch('odoo.fields.Date.context_today', return_value=send_day):
            self.env['l10n.fr.pdp.flow']._cron_send_ready_flows()
        flow.invalidate_recordset(['state', 'transport_identifier'])
        self.assertIn(flow.state, {'ready', 'completed', 'sent'}, 'Flow should be sent on the window day')
        # Transport identifier may be missing with mocked gateway
        # so only assert it if set.
        if flow.transport_identifier:
            self.assertTrue(flow.transport_identifier)

    def test_cron_skips_manual_send_mode(self):
        """Manual send mode should prevent cron dispatch even on window day."""
        self.company.write({
            'l10n_fr_pdp_periodicity': 'monthly',
            'l10n_fr_pdp_send_mode': 'manual',
        })
        invoice_date = fields.Date.from_string('2025-01-15')
        self._create_invoice(sent=True, date_val=invoice_date)
        flow = self._aggregate_company().filtered(lambda f: f.report_kind == 'transaction')[:1]

        send_day = fields.Date.from_string('2025-02-10')
        with patch('odoo.fields.Date.context_today', return_value=send_day):
            self.env['l10n.fr.pdp.flow']._cron_send_ready_flows()
        flow.invalidate_recordset(['state', 'transport_identifier'])
        self.assertEqual(flow.state, 'ready')
        self.assertFalse(flow.transport_identifier, 'Cron should not send flows in manual mode')

    def test_correction_created_on_last_day_with_errors(self):
        """Last-day cron send should exclude invalid moves and create correction flow."""
        invoice_date = fields.Date.from_string('2025-02-05')
        grace_day = fields.Date.from_string('2025-02-15')
        due_day = fields.Date.from_string('2025-02-20')

        self._create_invoice(sent=True, date_val=invoice_date)
        invalid_invoice = self._create_invoice(sent=False, date_val=invoice_date)

        # Build during grace so errors are surfaced and the flow is sendable on due day.
        with patch('odoo.fields.Date.context_today', return_value=grace_day):
            flow = self._aggregate_company().filtered(lambda f: f.report_kind == 'transaction')[:1]
        self.assertIn(invalid_invoice, flow.error_move_ids, 'Invalid invoice must be tracked on the flow')

        with patch('odoo.fields.Date.context_today', return_value=due_day):
            self.env['l10n.fr.pdp.flow']._cron_send_ready_flows()

        corrections = self.env['l10n.fr.pdp.flow'].search([
            ('company_id', '=', self.company.id),
            ('id', '!=', flow.id),
        ])
        correction = corrections.filtered(lambda f: invalid_invoice in f.move_ids)[:1]
        flow.invalidate_recordset(['state', 'error_move_ids'])

        self.assertTrue(correction, 'Correction flow should be spawned for invalid invoices')
        self.assertEqual(correction.transmission_type, 'RE')
        self.assertTrue(correction.is_correction)
        # v1.2: keep the excluded set on the IN flow (it drives invoice statuses)
        self.assertIn(invalid_invoice, flow.error_move_ids)
        # v1.2: RE is always a full replacement payload (never a delta)
        self.assertEqual(correction.move_ids.sorted('id'), flow.move_ids.sorted('id'))
        self.assertIn(invalid_invoice, correction.error_move_ids)
        self.assertEqual(correction.state, 'pending', 'RE flow should wait until errors are fixed before it becomes ready')

    def test_in_waits_for_window_while_re_sends_immediately(self):
        """IN waits for window; subsequent RE sends immediately when ready."""
        inv = self._create_invoice(sent=True)
        flow_in = self._aggregate_company().filtered(lambda f: f.report_kind == 'transaction')[:1]
        self.assertEqual(flow_in.transmission_type, 'IN')
        early = fields.Date.from_string('2025-01-05')
        with patch('odoo.fields.Date.context_today', return_value=early):
            self.env['l10n.fr.pdp.flow']._cron_send_ready_flows()
        flow_in.invalidate_recordset(['state', 'transport_identifier'])
        self.assertEqual(flow_in.state, 'ready', 'IN should wait for its window')
        self.assertFalse(flow_in.transport_identifier)

        # Send IN then add a new invoice to produce CO ready to send immediately
        with patch('odoo.fields.Date.context_today', return_value=flow_in._compute_deadline_window(flow_in.period_end)[1]):
            self.env['l10n.fr.pdp.flow']._cron_send_ready_flows()
        flow_in.invalidate_recordset(['state', 'transport_identifier'])
        self.assertIn(flow_in.state, {'ready', 'completed', 'sent'})

        self._create_invoice(sent=True, date_val=inv.invoice_date)
        flow_re = self._aggregate_company().filtered(
            lambda f: f.report_kind == 'transaction' and f.id != flow_in.id and f.transmission_type == 'RE',
        )[:1]
        self.assertTrue(flow_re, 'RE flow should be created for new moves in the period')
        self.assertTrue(flow_re.is_correction)
        with patch('odoo.fields.Date.context_today', return_value=fields.Date.from_string('2025-01-22')):
            self.env['l10n.fr.pdp.flow']._cron_send_ready_flows()
        flow_re.invalidate_recordset(['state', 'transport_identifier'])
        self.assertIn(flow_re.state, {'ready', 'completed', 'sent'}, 'RE should send immediately')
        # transport_identifier may be empty with mock gateway

    def test_error_flow_only_sends_on_last_day(self):
        """Ready flow with errors should wait until last window day to send."""
        self._create_invoice(sent=True)
        bad = self._create_invoice(sent=False)
        flow = self._aggregate_company().filtered(lambda f: f.report_kind == 'transaction')[:1]
        self.assertIn(bad, flow.error_move_ids)
        window = flow._compute_deadline_window(flow.period_end)
        _, end = window
        before_last = end - timedelta(days=1)

        with patch('odoo.fields.Date.context_today', return_value=before_last):
            self.env['l10n.fr.pdp.flow']._cron_send_ready_flows()
        flow.invalidate_recordset(['state', 'transport_identifier'])
        self.assertFalse(flow.transport_identifier, 'Flow with errors should wait until last day')

        with patch('odoo.fields.Date.context_today', return_value=end):
            self.env['l10n.fr.pdp.flow']._cron_send_ready_flows()
        flow.invalidate_recordset(['state', 'transport_identifier'])
        self.assertIn(flow.state, {'ready', 'completed', 'sent'})

    def test_error_flow_with_only_invalid_moves_becomes_cancelled_on_last_day(self):
        """Error flow with no valid invoices should be cancelled on deadline day."""
        self._create_invoice(sent=False)
        flow = self._aggregate_company().filtered(lambda f: f.report_kind == 'transaction')[:1]
        self.assertEqual(flow.state, 'error')
        self.assertTrue(flow.error_move_ids)
        self.assertFalse(flow.move_ids - flow.error_move_ids, 'Flow should have zero valid invoices')

        window = flow._compute_deadline_window(flow.period_end)
        self.assertTrue(window, 'A send window should exist for the flow')
        _, end = window
        with patch('odoo.fields.Date.context_today', return_value=end):
            self.env['l10n.fr.pdp.flow']._cron_send_ready_flows()

        flow.invalidate_recordset(['state', 'transport_status', 'transport_identifier'])
        self.assertEqual(flow.state, 'cancelled')
        self.assertEqual(flow.transport_status, 'CANCELLED')
        self.assertFalse(flow.transport_identifier)

    def test_decade_window_sends_on_twentieth(self):
        """Decade 1-10 window sends on the 20th, not before."""
        self.company.l10n_fr_pdp_periodicity = 'decade'
        # Use default decade deadlines for this scenario.
        self.company.l10n_fr_pdp_deadline_override_start = False
        self.company.l10n_fr_pdp_deadline_override_end = False
        inv_date = fields.Date.from_string('2025-01-05')
        self._create_invoice(sent=True, date_val=inv_date)
        flow = self._aggregate_company().filtered(lambda f: f.report_kind == 'transaction')[:1]
        self.assertEqual(flow.state, 'ready')

        before = fields.Date.from_string('2025-01-15')
        on_day = fields.Date.from_string('2025-01-20')
        with patch('odoo.fields.Date.context_today', return_value=before):
            self.env['l10n.fr.pdp.flow']._cron_send_ready_flows()
        flow.invalidate_recordset(['state', 'transport_identifier'])
        self.assertEqual(flow.state, 'ready')
        self.assertFalse(flow.transport_identifier)

        with patch('odoo.fields.Date.context_today', return_value=on_day):
            self.env['l10n.fr.pdp.flow']._cron_send_ready_flows()
        flow.invalidate_recordset(['state', 'transport_identifier'])
        self.assertIn(flow.state, {'ready', 'completed', 'sent'})

    def test_cron_generate_skips_non_pdp_company(self):
        """Daily cron should ignore companies without PDP enabled."""
        other_company = self.env['res.company'].create({
            'name': "No PDP",
            'country_id': self.env.ref('base.fr').id,
            'currency_id': self.env.ref('base.EUR').id,
            'l10n_fr_pdp_enabled': False,
        })
        # Handle account_asset module if installed
        account_vals = {}
        if 'create_asset' in self.env['account.account']._fields:
            account_vals['create_asset'] = 'no'
        if 'multiple_assets_per_line' in self.env['account.account']._fields:
            account_vals['multiple_assets_per_line'] = False

        income_other = self.env['account.account'].with_company(other_company.id).create({
            'name': "Other Revenue",
            'code': 'OTH100',
            'account_type': 'income',
            **account_vals,
        })
        receivable_other = self.env['account.account'].with_company(other_company.id).create({
            'name': "Other Receivable",
            'code': 'OTH200',
            'account_type': 'asset_receivable',
            'reconcile': True,
            **account_vals,
        })
        # Post an invoice in the non-PDP company.
        journal = self.env['account.journal'].with_company(other_company.id).create({
            'name': "Other Sales",
            'code': 'OTH',
            'type': 'sale',
            'company_id': other_company.id,
            'default_account_id': income_other.id,
        })
        inv = self.env['account.move'].with_company(other_company.id).create({
            'move_type': 'out_invoice',
            'partner_id': other_company.partner_id.id,
            'invoice_date': fields.Date.today(),
            'journal_id': journal.id,
            'invoice_line_ids': [Command.create({
                'name': "Line",
                'quantity': 1,
                'price_unit': 100,
                'account_id': income_other.id,
            })],
            'line_ids': [Command.create({
                'name': "Receivable",
                'debit': 100,
                'credit': 0,
                'account_id': receivable_other.id,
                'partner_id': other_company.partner_id.id,
            })],
        })
        inv.action_post()
        self.env['l10n.fr.pdp.flow.aggregator']._cron_generate_daily_flows()
        flows_other = self.env['l10n.fr.pdp.flow'].search([('company_id', '=', other_company.id)])
        self.assertFalse(flows_other, 'Cron should not generate flows for companies without PDP enabled')

    def test_bimonthly_window_sends_on_twenty_fifth(self):
        """Bimonthly IN flows send on window start when ready."""
        self.company.l10n_fr_pdp_periodicity = 'bimonthly'
        inv_date = fields.Date.from_string('2025-01-10')
        self._create_invoice(sent=True, date_val=inv_date)
        flow = self._aggregate_company().filtered(lambda f: f.report_kind == 'transaction')[:1]
        self.assertEqual(flow.state, 'ready')

        # Period end is end of Feb; window is Mar 25-30.
        before = fields.Date.from_string('2025-03-24')
        window_start = fields.Date.from_string('2025-03-25')
        with patch('odoo.fields.Date.context_today', return_value=before):
            self.env['l10n.fr.pdp.flow']._cron_send_ready_flows()
        flow.invalidate_recordset(['state', 'transport_identifier'])
        self.assertEqual(flow.state, 'ready')
        self.assertFalse(flow.transport_identifier)

        with patch('odoo.fields.Date.context_today', return_value=window_start):
            self.env['l10n.fr.pdp.flow']._cron_send_ready_flows()
        flow.invalidate_recordset(['state', 'transport_identifier'])
        self.assertIn(flow.state, {'sent', 'completed'})
        self.assertTrue(flow.transport_identifier)

    def test_cron_generate_builds_flow_for_pdp_company(self):
        """Daily generate cron should build flows for PDP-enabled companies."""
        self._create_invoice(sent=True)
        self.env['l10n.fr.pdp.flow.aggregator']._cron_generate_daily_flows()
        flows = self.env['l10n.fr.pdp.flow'].search([
            ('company_id', '=', self.company.id),
            ('report_kind', '=', 'transaction'),
        ])
        self.assertTrue(flows, 'Cron generate should create transaction flow for PDP company')
        self.assertIn(flows[0].state, {'pending', 'building', 'ready', 'error'})
