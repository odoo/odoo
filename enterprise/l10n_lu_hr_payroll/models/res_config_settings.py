# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    l10n_lu_official_social_security = fields.Char(related='company_id.l10n_lu_official_social_security', readonly=False)
    l10n_lu_seculine = fields.Char(related='company_id.l10n_lu_seculine', readonly=False)

    l10n_lu_accident_insurance_factor = fields.Selection(related='company_id.l10n_lu_accident_insurance_factor', readonly=False, required=True)
    l10n_lu_accident_insurance_rate = fields.Float(related='company_id.l10n_lu_accident_insurance_rate')

    l10n_lu_mutuality_class = fields.Selection(related='company_id.l10n_lu_mutuality_class', readonly=False, required=True)
    l10n_lu_mutuality_rate = fields.Float(related='company_id.l10n_lu_mutuality_rate')
