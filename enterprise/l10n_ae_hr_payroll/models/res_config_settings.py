# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    l10n_ae_employer_code = fields.Char(related="company_id.l10n_ae_employer_code", readonly=False)
    l10n_ae_bank_account_id = fields.Many2one(related="company_id.l10n_ae_bank_account_id", readonly=False)
