# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    l10n_in_dearness_allowance = fields.Boolean(
        string="Dearness Allowance", related='company_id.l10n_in_dearness_allowance', readonly=False)
    l10n_in_epf_employer_id = fields.Char(related='company_id.l10n_in_epf_employer_id', readonly=False)
    l10n_in_esic_ip_number = fields.Char(related='company_id.l10n_in_esic_ip_number', readonly=False)
    l10n_in_pt_number = fields.Char(related='company_id.l10n_in_pt_number', readonly=False)
    l10n_in_is_statutory_compliance = fields.Boolean(related='company_id.l10n_in_is_statutory_compliance', readonly=False)
