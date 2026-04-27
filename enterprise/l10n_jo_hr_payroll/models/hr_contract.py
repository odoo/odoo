# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields


class HRContract(models.Model):
    _inherit = 'hr.contract'

    l10n_jo_housing_allowance = fields.Monetary(string='Jordan Housing Allowance')
    l10n_jo_transportation_allowance = fields.Monetary(string='Jordan Transportation Allowance')
    l10n_jo_other_allowances = fields.Monetary(string='Jordan Other Allowances')
    l10n_jo_tax_exemption = fields.Monetary(string='Jordan Tax Exemption Amount')
