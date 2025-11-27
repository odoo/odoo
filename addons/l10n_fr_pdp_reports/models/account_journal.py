from odoo import fields, models, _
from odoo.tools.misc import format_date


class AccountJournal(models.Model):
    _inherit = 'account.journal'

    def _get_journal_dashboard_data_batched(self):
        dashboard_data = super()._get_journal_dashboard_data_batched()

        # Filter journals for PDP-enabled companies
        pdp_enabled_journals = self.filtered(
            lambda j: (
                j.type == 'sale'
                and j.company_id.country_code == 'FR'
                and j.company_id.l10n_fr_pdp_enabled
            ),
        )
        if not pdp_enabled_journals:
            return dashboard_data

        Flow = self.env['l10n.fr.pdp.flow']
        Move = self.env['account.move']
        today = fields.Date.context_today(self)

        # Group journals by company to avoid duplicate queries
        journals_by_company = {}
        for journal in pdp_enabled_journals:
            company_id = journal.company_id.id
            if company_id not in journals_by_company:
                journals_by_company[company_id] = []
            journals_by_company[company_id].append(journal)

        # Compute PDP data per company
        for company_id, journals in journals_by_company.items():

            # ---------- Next due dates ----------
            def _get_due(report_kind):
                flow = Flow.search(
                    [
                        ('company_id', '=', company_id),
                        ('report_kind', '=', report_kind),
                        ('state', 'in', ('pending', 'building', 'ready', 'error')),
                        ('next_deadline_end', '!=', False),
                    ],
                    limit=1,
                    order='next_deadline_end asc',
                )
                if not flow:
                    return None, None, False
                due = flow.next_deadline_end
                has_errors = flow.state == 'error' or bool(flow.error_move_ids)
                return due, format_date(self.env, due), has_errors

            tx_due_raw, tx_due_str, tx_has_errors = _get_due('transaction')
            pay_due_raw, pay_due_str, pay_has_errors = _get_due('payment')

            # ---------- Errors ----------
            error_domain = [
                ('company_id', '=', company_id),
                ('l10n_fr_pdp_status', '=', 'error'),
            ]
            error_count = Move.search_count(error_domain)

            has_warning = bool(error_count)
            has_danger = False
            if error_count:
                deadlines = [d for d in (tx_due_raw, pay_due_raw) if d]
                if deadlines:
                    min_deadline = min(deadlines)
                    if (min_deadline - today).days <= 3:
                        has_danger = True

            # Apply data to all journals in this company
            for journal in journals:
                data = dashboard_data[journal.id]

                # Mark EREP journal specifically
                if journal.code == 'EREP':
                    data['pdp_is_ereporting_journal'] = True
                    data['pdp_tx_due'] = tx_due_str or False
                    data['pdp_pay_due'] = pay_due_str or False
                    data['pdp_tx_has_errors'] = tx_has_errors
                    data['pdp_pay_has_errors'] = pay_has_errors

                # Add error info to ALL sale journals
                data['pdp_error_count'] = error_count
                data['pdp_has_warning'] = has_warning
                data['pdp_has_danger'] = has_danger

        return dashboard_data

    def _action_open_next_flow(self, report_kind):
        """Open the next flow with upcoming due date for given report kind.

        Args:
            report_kind: 'transaction' or 'payment'

        Returns:
            dict: Action to open flow form, or False if no flow found
        """
        self.ensure_one()
        flow = self.env['l10n.fr.pdp.flow'].search(
            [
                ('company_id', '=', self.company_id.id),
                ('report_kind', '=', report_kind),
                ('state', 'in', ('pending', 'building', 'ready', 'error')),
                ('next_deadline_end', '!=', False),
            ],
            limit=1,
            order='next_deadline_end asc',
        )
        if flow:
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'l10n.fr.pdp.flow',
                'res_id': flow.id,
                'view_mode': 'form',
                'target': 'current',
            }
        return False

    def action_open_next_transaction_flow(self):
        """Open the next transaction flow with upcoming due date."""
        return self._action_open_next_flow('transaction')

    def action_open_next_payment_flow(self):
        """Open the next payment flow with upcoming due date."""
        return self._action_open_next_flow('payment')

    def action_open_pdp_error_moves(self):
        """Open in-scope accounting documents currently in PDP error for this company."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _("E-Reporting Error Documents"),
            'res_model': 'account.move',
            'view_mode': 'list,form',
            'domain': [
                ('company_id', '=', self.company_id.id),
                ('l10n_fr_pdp_status', '=', 'error'),
            ],
            'context': {'search_default_group_by_move_type': 1},
            'target': 'current',
        }
