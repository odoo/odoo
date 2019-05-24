# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models, api


class AccountFiscalPosition(models.Model):

    _inherit = 'account.fiscal.position'

    l10n_ar_afip_code = fields.Char(
        'AFIP Code',
        help='This code will be used on electronic invoice and citi '
        'reports',
    )

    def get_fiscal_position(self, partner_id, delivery_id=None):
        """ Fiscal position does not depends on the partner vat, it depends on
        the partner AFIP responsability
        """
        company_id = self._context.get(
            'force_company', self.env.user.company_id.id)
        if self.env['res.company'].browse(company_id).country_id == self.env.ref('base.ar'):
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
        now if it is vat required or not
        """
        if 'partner_afip_responsability' in self._context:
            vat_required = self._context.get(
                'partner_afip_responsability') not in [
                    '6', '4', '8', '3', '13']

        return super()._get_fpos_by_region(
            country_id=country_id, state_id=state_id, zipcode=zipcode,
            vat_required=vat_required)
