# -*- coding:utf-8 -*-

from odoo import fields, models


class AccountJournal(models.Model):
    _inherit = 'account.journal'

    account_peppol_proxy_state = fields.Selection(related='company_id.account_peppol_proxy_state')
    is_peppol_journal = fields.Boolean(string="Account used for Peppol", default=False)

    def peppol_get_new_documents(self):
        edi_users = self.env['account_edi_proxy_client.user'].search([
            ('company_id.account_peppol_proxy_state', '=', 'active'),
            ('company_id', 'in', self.company_id.ids),
        ])
        edi_users._peppol_get_new_documents()

    def peppol_get_message_status(self):
        edi_users = self.env['account_edi_proxy_client.user'].search([
            ('company_id.account_peppol_proxy_state', '=', 'active'),
            ('company_id', 'in', self.company_id.ids),
        ])
        edi_users._peppol_get_message_status()
