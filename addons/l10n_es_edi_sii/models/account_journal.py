# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models
from odoo.tools import SQL


class AccountJournal(models.Model):
    _inherit = 'account.journal'

    l10n_es_sii_pending_count = fields.Integer(compute='_compute_l10n_es_sii_pending_count')
    l10n_es_sii_kanban_state = fields.Selection(
        selection=[('error', 'Error'), ('urgent', 'Urgent')],
        compute='_compute_l10n_es_sii_pending_count'
    )

    def _get_sii_pending_move_query(self, extra_domain):
        """ Helper method to build the SQL query for pending SII moves, ensuring we only evaluate the latest document. """
        query = self.env['account.move']._search([
            ('state', '=', 'posted'),
            ('move_type', 'in', ('out_invoice', 'out_refund', 'in_invoice', 'in_refund')),
            ('company_id.l10n_es_sii_tax_agency', '!=', False),
        ] + extra_domain)

        move_table = query.table

        lateral_query = SQL(
            "(SELECT id, state, response_message FROM l10n_es_edi_sii_document WHERE move_id = %s ORDER BY id DESC LIMIT 1)",
            move_table.id
        )

        query.add_join('LEFT JOIN LATERAL', 'doc', lateral_query, SQL("TRUE"))

        doc_state = SQL.identifier('doc', 'state')
        doc_message = SQL.identifier('doc', 'response_message')

        query.add_where(SQL("%s IS NULL OR %s IN ('to_send', 'to_cancel')", doc_state, doc_state))

        return query, move_table, doc_state, doc_message

    def _compute_l10n_es_sii_pending_count(self):
        es_journals = self.filtered(
            lambda j: j.company_id.account_fiscal_country_id.code == 'ES'
            and j.type in ('sale', 'purchase')
            and j.company_id.l10n_es_sii_tax_agency
        )
        (self - es_journals).l10n_es_sii_pending_count = 0
        (self - es_journals).l10n_es_sii_kanban_state = False

        if not es_journals:
            return

        query, move_table, doc_state, doc_message = self._get_sii_pending_move_query([('journal_id', 'in', es_journals.ids)])
        query.groupby = move_table.journal_id

        sql = query.select(
            move_table.journal_id,
            SQL("COUNT(%s) as pending_count", move_table.id),
            SQL("MAX(CASE WHEN %s IN ('to_send', 'to_cancel') AND %s IS NOT NULL THEN 1 ELSE 0 END) as has_error", doc_state, doc_message),
            SQL("MAX(CASE WHEN %s <= (NOW() - INTERVAL '36 hours') THEN 1 ELSE 0 END) as has_urgent", move_table.date)
        )

        rows = self.env.execute_query(sql)
        results = {
            row[0]: {
                'pending_count': row[1],
                'has_error': row[2],
                'has_urgent': row[3]
            } for row in rows
        }

        for journal in es_journals:
            res = results.get(journal.id)
            if not res:
                journal.l10n_es_sii_pending_count = 0
                journal.l10n_es_sii_kanban_state = False
                continue

            journal.l10n_es_sii_pending_count = res['pending_count']

            if res['has_urgent']:
                journal.l10n_es_sii_kanban_state = 'urgent'
            elif res['has_error']:
                journal.l10n_es_sii_kanban_state = 'error'
            else:
                journal.l10n_es_sii_kanban_state = False

    def action_l10n_es_sii_open_pending(self):
        self.ensure_one()

        query, move_table, _doc_state, _doc_message = self._get_sii_pending_move_query([('journal_id', '=', self.id)])

        sql = query.select(move_table.id)
        move_ids = [row[0] for row in self.env.execute_query(sql)]

        return {
            'type': 'ir.actions.act_window',
            'name': self.env._('Invoices to send to SII'),
            'res_model': 'account.move',
            'view_mode': 'list,form',
            'domain': [('id', 'in', move_ids)],
            'context': {'create': False},
        }
