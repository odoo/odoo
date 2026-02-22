import calendar
from unittest.mock import patch

from odoo import fields
from odoo.tools.misc import format_date
from odoo.tests.common import tagged
from .common import PdpTestCommon


@tagged('post_install', 'post_install_l10n', '-at_install')
class TestPdpDashboardTile(PdpTestCommon):
    def test_dashboard_tile_visibility_flags(self):
        """Tile only appears for FR PDP companies; hidden otherwise."""
        journal = self.env['account.journal'].search([
            ('code', '=', 'EREP'),
            ('company_id', '=', self.company.id),
        ], limit=1)
        base_data = journal._get_journal_dashboard_data_batched()[journal.id]
        self.assertTrue(base_data.get('pdp_is_ereporting_journal'))

        self.company.l10n_fr_pdp_enabled = False
        disabled_data = journal._get_journal_dashboard_data_batched()[journal.id]
        self.assertFalse(disabled_data.get('pdp_is_ereporting_journal'))

        self.company.partner_id.country_id = self.env.ref('base.be')
        non_fr_data = journal._get_journal_dashboard_data_batched()[journal.id]
        self.assertFalse(non_fr_data.get('pdp_is_ereporting_journal'))

    def test_dashboard_warning_and_danger_thresholds(self):
        """Warning when deadline >3 days, danger when <=3 days with errors present."""
        error_invoice = self._create_invoice(sent=False)
        flow = self._aggregate_company().filtered(lambda f: f.report_kind == 'transaction')[:1]
        error_invoice.invalidate_recordset(['l10n_fr_pdp_status'])
        journal = self.env['account.journal'].search([
            ('code', '=', 'EREP'),
            ('company_id', '=', self.company.id),
        ], limit=1)

        # Grace period: after reporting period end and before due date.
        base_today = fields.Date.from_string('2025-02-15')
        with patch('odoo.fields.Date.context_today', return_value=base_today):
            far_day = min(base_today.day + 5, calendar.monthrange(base_today.year, base_today.month)[1])
            self.company.write({
                'l10n_fr_pdp_deadline_override_start': far_day,
                'l10n_fr_pdp_deadline_override_end': far_day,
            })
            flow.invalidate_recordset(['next_deadline_start', 'next_deadline_end', 'period_status'])
            flow._compute_deadline_preview()
            flow._compute_period_status()
            error_invoice.invalidate_recordset(['l10n_fr_pdp_status'])
            error_invoice._compute_l10n_fr_pdp_status()
            data = journal._get_journal_dashboard_data_batched()[journal.id]
            self.assertTrue(data.get('pdp_has_warning'), 'Grace period should surface errors as warnings')
            self.assertFalse(data.get('pdp_has_danger'), 'Danger only triggers when the deadline is close')

            near_day = min(base_today.day + 1, calendar.monthrange(base_today.year, base_today.month)[1])
            self.company.write({
                'l10n_fr_pdp_deadline_override_start': near_day,
                'l10n_fr_pdp_deadline_override_end': near_day,
            })
            flow.invalidate_recordset(['next_deadline_start', 'next_deadline_end', 'period_status'])
            flow._compute_deadline_preview()
            flow._compute_period_status()
            error_invoice.invalidate_recordset(['l10n_fr_pdp_status'])
            error_invoice._compute_l10n_fr_pdp_status()
            data = journal._get_journal_dashboard_data_batched()[journal.id]
            self.assertTrue(data.get('pdp_has_warning'))
            self.assertTrue(data.get('pdp_has_danger'))

    def test_dashboard_next_deadlines_from_flows(self):
        """Next tx/pay dates should reflect earliest deadline across open flows."""
        journal = self.env['account.journal'].search([
            ('code', '=', 'EREP'),
            ('company_id', '=', self.company.id),
        ], limit=1)
        tx_flow = self.env['l10n.fr.pdp.flow'].create({
            'company_id': self.company.id,
            'report_kind': 'transaction',
            'currency_id': self.company.currency_id.id,
            'reporting_date': fields.Date.from_string('2025-01-01'),
            'period_start': fields.Date.from_string('2025-01-01'),
            'period_end': fields.Date.from_string('2025-01-31'),
            'periodicity_code': 'M',
            'state': 'ready',
            'next_deadline_start': fields.Date.from_string('2025-02-09'),
            'next_deadline_end': fields.Date.from_string('2025-02-10'),
            'transaction_type': 'mixed',
        })
        pay_flow = self.env['l10n.fr.pdp.flow'].create({
            'company_id': self.company.id,
            'report_kind': 'payment',
            'currency_id': self.company.currency_id.id,
            'reporting_date': fields.Date.from_string('2025-01-01'),
            'period_start': fields.Date.from_string('2025-01-01'),
            'period_end': fields.Date.from_string('2025-01-31'),
            'periodicity_code': 'M',
            'state': 'ready',
            'next_deadline_start': fields.Date.from_string('2025-02-19'),
            'next_deadline_end': fields.Date.from_string('2025-02-20'),
            'transaction_type': 'mixed',
            'document_type': 'sale',
        })

        data = journal._get_journal_dashboard_data_batched()[journal.id]
        expected_tx = format_date(self.env, tx_flow.next_deadline_end)
        expected_pay = format_date(self.env, pay_flow.next_deadline_end)
        self.assertEqual(data.get('pdp_tx_due'), expected_tx)
        self.assertEqual(data.get('pdp_pay_due'), expected_pay)
