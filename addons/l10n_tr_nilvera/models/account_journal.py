from odoo import fields, models


class AccountJournal(models.Model):
    _inherit = 'account.journal'

    l10n_tr_nilvera_api_key = fields.Char(related='company_id.l10n_tr_nilvera_api_key')
    is_nilvera_journal = fields.Boolean(string="Journal used for Nilvera")
