# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models


class ConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    l10n_cl_factoring_journal_id = fields.Many2one(
        'account.journal', related='company_id.l10n_cl_factoring_journal_id', readonly=False)
    l10n_cl_factoring_counterpart_account_id = fields.Many2one(
        'account.account', related='company_id.l10n_cl_factoring_counterpart_account_id', readonly=False)
