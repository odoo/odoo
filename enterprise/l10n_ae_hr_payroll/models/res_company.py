# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class Company(models.Model):
    _inherit = 'res.company'

    l10n_ae_employer_code = fields.Char(string="Employer Unique ID")
    l10n_ae_bank_account_id = fields.Many2one("res.partner.bank", domain="[('bank_id.country.code', '=', 'AE')]", string="Salaries Bank Account")

    _sql_constraints = [
        ('l10n_ae_unique_l10n_ae_employer_code', 'UNIQUE(l10n_ae_employer_code)',
         'UAE Employeer ID must be unique.')
    ]
