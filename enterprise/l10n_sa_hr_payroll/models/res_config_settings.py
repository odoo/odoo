from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    l10n_sa_mol_establishment_code = fields.Char(related="company_id.l10n_sa_mol_establishment_code", readonly=False)
    l10n_sa_bank_account_id = fields.Many2one(related="company_id.l10n_sa_bank_account_id", readonly=False)
    l10n_sa_bank_id = fields.Many2one(related="l10n_sa_bank_account_id.bank_id", readonly=False)
    l10n_sa_bank_establishment_code = fields.Char(related="l10n_sa_bank_id.l10n_sa_bank_establishment_code", readonly=False)
    l10n_sa_sarie_code = fields.Char(related="l10n_sa_bank_id.l10n_sa_sarie_code", readonly=False)
    company_partner_id = fields.Many2one(related="company_id.partner_id")
