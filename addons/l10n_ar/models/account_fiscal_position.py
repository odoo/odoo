# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models, api, _


class AccountFiscalPosition(models.Model):
    _inherit = 'account.fiscal.position'

    l10n_ar_afip_responsibility_type_ids = fields.Many2many(
        'l10n_ar.afip.responsibility.type', 'l10n_ar_afip_reponsibility_type_fiscal_pos_rel',
        string='ARCA Responsibility Types', help='List of ARCA responsibilities where this fiscal position '
        'should be auto-detected')

    def _get_fpos_validation_functions(self, partner):
        functions = super()._get_fpos_validation_functions(partner)
        if self.env.company.country_id.code != "AR":
            return functions
        return [
            lambda fpos: partner.l10n_ar_afip_responsibility_type_id in fpos.l10n_ar_afip_responsibility_type_ids,
        ] + functions
