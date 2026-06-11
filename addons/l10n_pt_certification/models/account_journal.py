from odoo import models, fields


class AccountJournal(models.Model):
    _inherit = 'account.journal'

    l10n_pt_at_series_ids = fields.One2many('l10n_pt.at.series', 'journal_id', string="AT Series linked to this Journal")
