# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import timedelta

from odoo import fields, models


class AccountJournal(models.Model):
    _inherit = 'account.journal'

    l10n_es_sii_pending_count = fields.Integer(compute='_compute_l10n_es_sii_pending_count')
    l10n_es_sii_kanban_state = fields.Selection(
        selection=[
            ('error', "Error"),
            ('urgent', "Urgent"),
        ],
        compute='_compute_l10n_es_sii_pending_count',
    )

    def _fill_sale_purchase_dashboard_data(self, dashboard_data):
        super()._fill_sale_purchase_dashboard_data(dashboard_data)
        for journal in self.filtered(lambda journal: journal.type in ('sale', 'purchase')):
            dashboard_data[journal.id].update({
                'l10n_es_sii_pending_count': journal.l10n_es_sii_pending_count,
                'l10n_es_sii_kanban_state': journal.l10n_es_sii_kanban_state,
                'l10n_es_sii_state_color': {
                    'urgent': 'danger',
                    'error': 'warning',
                }.get(journal.l10n_es_sii_kanban_state, 'muted'),
            })

    def _get_l10n_es_sii_pending_domain(self):
        return [
            *self.env['account.move']._check_company_domain(self.env.companies),
            ('journal_id', 'in', self.ids),
            ('invoice_date', '>=', fields.Date.today() - timedelta(days=60)),
            ('state', '=', 'posted'),
            ('move_type', 'in', ('out_invoice', 'out_refund', 'in_invoice', 'in_refund')),
            ('l10n_es_edi_sii_state', 'in', ('to_send', 'to_cancel')),
        ]

    def _compute_l10n_es_sii_pending_count(self):
        sii_journals = self.filtered(
            lambda journal: journal.type in ('sale', 'purchase')
            and journal.country_code == 'ES'
            and journal.company_id.l10n_es_sii_tax_agency
        )
        self.l10n_es_sii_pending_count = 0
        self.l10n_es_sii_kanban_state = False

        if not sii_journals:
            return

        urgency_date = (fields.Datetime.now() - timedelta(hours=36)).date()
        rg_result = self.env['account.move'].sudo()._read_group(
            domain=sii_journals._get_l10n_es_sii_pending_domain(),
            groupby=['journal_id'],
            aggregates=['__count', 'l10n_es_edi_sii_error:count', 'invoice_date:min'],
        )
        for journal, pending_count, error_count, date_min in rg_result:
            journal.l10n_es_sii_pending_count = pending_count
            if date_min and date_min <= urgency_date:
                journal.l10n_es_sii_kanban_state = 'urgent'
            elif error_count:
                journal.l10n_es_sii_kanban_state = 'error'

    def action_l10n_es_sii_open_pending(self):
        self.ensure_one()

        return {
            'type': 'ir.actions.act_window',
            'name': self.env._("Invoices to Send to SII"),
            'res_model': 'account.move',
            'view_mode': 'list,form',
            'domain': self._get_l10n_es_sii_pending_domain(),
            'context': {
                'create': False,
            },
        }
