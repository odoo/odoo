# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models


class Company(models.Model):
    _inherit = 'res.company'

    l10n_cl_factoring_journal_id = fields.Many2one(
        'account.journal', domain=[('type', '=', 'general')], string='Counterpart Factoring Journal')
    l10n_cl_factoring_counterpart_account_id = fields.Many2one(
        'account.account', domain=[('account_type', '=', 'asset_receivable'), ('reconcile', '=', True)],
        string='Counterpart Factoring Account')
