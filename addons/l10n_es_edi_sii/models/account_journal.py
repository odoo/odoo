from odoo import fields, models
from datetime import timedelta


class AccountJournal(models.Model):
    _inherit = 'account.journal'

    def _fill_sale_purchase_dashboard_data(self, dashboard_data):
        super()._fill_sale_purchase_dashboard_data(dashboard_data)

        es_journals = self.filtered(
            lambda j: j.type in ('sale', 'purchase') and j.company_id.account_fiscal_country_id.code == 'ES'
        )
        if not es_journals:
            return

        subquery_str, subquery_params = self.env['account.move']._get_l10n_es_sii_state_query_parts('to_send')
        combined_params = subquery_params + (tuple(es_journals.ids),)

        self.env.cr.execute(f"""
            SELECT DISTINCT am.journal_id
            FROM account_move am
            JOIN l10n_es_edi_sii_document d ON d.move_id = am.id
            WHERE am.id IN ({subquery_str})
            AND am.journal_id IN %s
            AND am.state = 'posted'
            AND d.response_message IS NOT NULL
        """, combined_params)
        errored_journal_ids = {row[0] for row in self.env.cr.fetchall()}

        self.env.cr.execute(f"""
            SELECT am.journal_id, COUNT(*) as count, MAX(am.create_date) as max_date
            FROM account_move am
            WHERE am.id IN ({subquery_str})
            AND am.journal_id IN %s
            AND am.state = 'posted'
            GROUP BY am.journal_id
        """, combined_params)

        limit_time = fields.Datetime.now() - timedelta(hours=36)

        for journal_id, count, max_date in self.env.cr.fetchall():
            color = 'danger' if max_date and max_date < limit_time else ('warning' if journal_id in errored_journal_ids else 'primary')

            dashboard_data[journal_id].update({
                'l10n_es_sii_to_send_count': count,
                'l10n_es_sii_state_color': color,
            })

    def action_open_l10n_es_sii_to_send(self):
        self.ensure_one()
        return {
            'name': self.env._('Invoices to Send to SII'),
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'view_mode': 'list,form',
            'domain': [
                ('journal_id', '=', self.id),
                ('state', '=', 'posted'),
                ('l10n_es_edi_sii_state', '=', 'to_send')
            ],
            'context': {
                'default_journal_id': self.id,
            }
        }
