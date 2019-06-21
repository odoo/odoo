# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models, api


class AccountFiscalPosition(models.Model):

    _inherit = 'account.fiscal.position'

    l10n_ar_afip_responsability_type_ids = fields.Many2many(
        'l10n_ar.afip.responsability.type',
        'l10n_ar_afip_reponsability_type_fiscal_pos_rel',
        string='AFIP Responsability Types',
        help='List of AFIP responsabilities where this fiscal position '
        'should be auto-detected',
    )

    def get_fiscal_position(self, partner_id, delivery_id=None):
        """ Take into account the partner afip responsability in order to
        auto-detect the fiscal position """
        company = self.env['res.company'].browse(self._context.get(
            'force_company', self.env.user.company_id.id))
        if company.country_id == self.env.ref('base.ar'):
            domain = [
                ('auto_apply', '=', True),
                ('l10n_ar_afip_responsability_type_ids', '=', self.env['res.partner'].browse(
                    partner_id).l10n_ar_afip_responsability_type_id.id),
            ]
            if self.env.context.get('force_company'):
                domain.append(
                    ('company_id', '=', self.env.context.get('force_company')))
            return self.search(domain, limit=1)
        return super().get_fiscal_position(partner_id, delivery_id=delivery_id)
