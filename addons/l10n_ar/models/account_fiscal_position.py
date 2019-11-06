# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models, api, _


class AccountFiscalPosition(models.Model):

    _inherit = 'account.fiscal.position'

    l10n_ar_afip_responsibility_type_ids = fields.Many2many(
        'l10n_ar.afip.responsibility.type', 'l10n_ar_afip_reponsibility_type_fiscal_pos_rel',
        string='AFIP Responsibility Types', help='List of AFIP responsibilities where this fiscal position '
        'should be auto-detected')

    def get_fiscal_position(self, partner_id, delivery_id=None):
        """ Take into account the partner afip responsibility in order to auto-detect the fiscal position """
        company = self.env['res.company'].browse(self._context.get('force_company', self.env.company.id))
        if company.country_id == self.env.ref('base.ar'):
            domain = [
                ('auto_apply', '=', True),
                ('l10n_ar_afip_responsibility_type_ids', '=', self.env['res.partner'].browse(
                    partner_id).l10n_ar_afip_responsibility_type_id.id),
                ('company_id', '=', company.id)
            ]
            return self.search(domain, limit=1).id
        return super().get_fiscal_position(partner_id, delivery_id=delivery_id)

    @api.onchange('l10n_ar_afip_responsibility_type_ids', 'country_group_id', 'country_id', 'zip_from', 'zip_to')
    def _onchange_afip_responsibility(self):
        if self.company_id.country_id == self.env.ref('base.ar'):
            if self.l10n_ar_afip_responsibility_type_ids and any(['country_group_id', 'country_id', 'zip_from', 'zip_to']):
                return {'warning': {
                    'title': _("Warning"),
                    'message': _('If use AFIP Responsibility then the country / zip codes will be not take into account'),
                }}
