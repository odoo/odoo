# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models, api


class AccountFiscalPosition(models.Model):

    _inherit = 'account.fiscal.position'

    l10n_ar_afip_responsability_type_codes = fields.Char(
        'AFIP Responsability Type Codes',
        help='List of AFIP responsability codes where this fiscal positon '
        'should be auto-detected',
    )

    def get_fiscal_position(self, partner_id, delivery_id=None):
        """ Send this afip_responsability of the partner to _get_fpos_by_region
        """
        company = self.env['res.company'].browse(self._context.get(
            'force_company', self.env.user.company_id.id))
        if company.country_id == self.env.ref('base.ar'):
            partner = self.env['res.partner'].browse(partner_id)
            afip_responsability = \
                partner.commercial_partner_id.l10n_ar_afip_responsability_type
            self = self.with_context(
                partner_afip_responsability=afip_responsability)
        return super().get_fiscal_position(partner_id, delivery_id=delivery_id)

    @api.model
    def _get_fpos_by_region(
        self, country_id=False, state_id=False, zipcode=False,
        vat_required=False):
        """ Take into account the partner afip responsability in order to
        auto-detect the fiscal position """
        if 'partner_afip_responsability' in self._context:
            res = self.search(
                [('auto_apply', '=', True),
                 ('l10n_ar_afip_responsability_type_codes', 'like',
                  "'%s'" % self._context.get('partner_afip_responsability')),
                ], limit=1)
            return res

        return super()._get_fpos_by_region(
            country_id=country_id, state_id=state_id, zipcode=zipcode,
            vat_required=vat_required)
