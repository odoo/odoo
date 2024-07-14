# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    l10n_au_kp_api_key = fields.Char(string='Employment Hero API Key', config_parameter='l10n_au_keypay.l10n_au_kp_api_key')
    l10n_au_kp_base_url = fields.Char(
        string='Payroll URL', config_parameter='l10n_au_keypay.l10n_au_kp_base_url',
        required=True, default='https://keypay.yourpayroll.com.au/')

    l10n_au_kp_enable = fields.Boolean(related='company_id.l10n_au_kp_enable', readonly=False)
    l10n_au_kp_identifier = fields.Char(related='company_id.l10n_au_kp_identifier', readonly=False)
    l10n_au_kp_lock_date = fields.Date(related='company_id.l10n_au_kp_lock_date', readonly=False)
    l10n_au_kp_journal_id = fields.Many2one(related='company_id.l10n_au_kp_journal_id', readonly=False)

    def action_kp_payroll_fetch_payrun(self):
        account_moves = self.company_id._kp_payroll_fetch_payrun()
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Payruns fetched',
                'message': _("%s Payruns were fetched and added to your accounting", len(account_moves)),
                'sticky': True,
            }
        }
