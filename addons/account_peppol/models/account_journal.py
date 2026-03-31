# -*- coding:utf-8 -*-

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class AccountJournal(models.Model):
    _inherit = 'account.journal'

    account_peppol_proxy_state = fields.Selection(related='company_id.account_peppol_proxy_state')
    is_peppol_journal = fields.Boolean(string="Account used for Peppol", default=False)

    @api.constrains('type')
    def _check_type_for_peppol_journal(self):
        for journal in self:
            if journal.is_peppol_journal and journal.type != 'purchase':
                raise ValidationError(_("You can't change the type of a journal used for Peppol invoice reception to"
                                  "a type different than 'Purchase'.\nPlease change the journal used for Peppol"
                                  " reception before changing the type of this journal."))

    def peppol_get_new_documents(self):
        edi_users = self.env['account_edi_proxy_client.user'].search([
            ('company_id.account_peppol_proxy_state', '=', 'active'),
            ('company_id', 'in', self.company_id.ids),
            ('proxy_type', '=', 'peppol')
        ])
        edi_users._peppol_get_new_documents()

    def peppol_get_message_status(self):
        edi_users = self.env['account_edi_proxy_client.user'].search([
            ('company_id.account_peppol_proxy_state', '=', 'active'),
            ('company_id', 'in', self.company_id.ids),
            ('proxy_type', '=', 'peppol')
        ])
        edi_users._peppol_get_message_status()

    def action_peppol_ready_moves(self):
        return {
            'name': _("Peppol Ready invoices"),
            'type': 'ir.actions.act_window',
            'view_mode': 'list,form',
            'res_model': 'account.move',
            'context': {
                'search_default_peppol_ready': 1,
            }
        }
