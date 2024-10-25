# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models, api, _


class AccountFiscalPosition(models.Model):

    _inherit = 'account.fiscal.position'

    l10n_ar_afip_responsibility_type_ids = fields.Many2many(
        'l10n_ar.afip.responsibility.type', 'l10n_ar_afip_reponsibility_type_fiscal_pos_rel',
        string='AFIP Responsibility Types', help='List of AFIP responsibilities where this fiscal position '
        'should be auto-detected')

    def _get_fpos_ranking_functions(self, partner):
        if self.env.company.country_id.code != "AR":
            return super()._get_fpos_ranking_functions(partner)
        return [
            ('l10n_ar_afip_responsibility_type_id', lambda fpos: (
                partner.l10n_ar_afip_responsibility_type_id in fpos.l10n_ar_afip_responsibility_type_ids
            ))
        ] + super()._get_fpos_ranking_functions(partner)
