# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models


class AccountJournal(models.Model):
    _inherit = 'account.journal'

    l10n_in_edi_to_send_count = fields.Integer(compute='_compute_l10n_in_edi_to_send_count')

    def _compute_l10n_in_edi_to_send_count(self):
        self.l10n_in_edi_to_send_count = 0

        sale_journals = self.filtered(lambda journal: journal.company_id.l10n_in_edi_feature and journal.type == 'sale')
        if not sale_journals:
            return

        for journal, count in self.env['account.move']._read_group(
            [
                ("journal_id", "in", sale_journals.ids),
                ("l10n_in_edi_status", "=", "to_send"),
                ("l10n_in_edi_error", "not like", "[2150]"),  # Avoid considering already sent invoices (error - 2150)
            ],
            ['journal_id'],
            ['__count'],
        ):
            journal.l10n_in_edi_to_send_count = count

    def action_l10n_in_einvoice_open_pending(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': self.env._('Invoices to send for E-Invoicing'),
            'res_model': 'account.move',
            'view_mode': 'list,form',
            'domain': [
                ('journal_id', '=', self.id),
                ('l10n_in_edi_status', '=', 'to_send'),
                ("l10n_in_edi_error", "not like", "[2150]"),  # Avoid considering already sent invoices (error - 2150)
            ],
            'context': {'create': False},
        }
