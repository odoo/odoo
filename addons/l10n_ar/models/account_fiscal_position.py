# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models, api, _


class AccountFiscalPosition(models.Model):

    _inherit = 'account.fiscal.position'

    l10n_ar_afip_responsibility_type_ids = fields.Many2many(
        'l10n_ar.afip.responsibility.type', 'l10n_ar_afip_reponsibility_type_fiscal_pos_rel',
        string='AFIP Responsibility Types', help='List of AFIP responsibilities where this fiscal position '
        'should be auto-detected')

    @api.model
    def _get_fiscal_position(self, partner, delivery=None):
        if self.env.company.country_id.code != "AR":
            return super()._get_fiscal_position(partner, delivery=delivery)
        return super(AccountFiscalPosition, self.with_context(l10n_ar_afip_responsibility_type_id=partner.l10n_ar_afip_responsibility_type_id.id))._get_fiscal_position(partner, delivery=delivery)

    def _prepare_fpos_base_domain(self, vat_required):
        domain = super()._prepare_fpos_base_domain(vat_required)
        if self._context.get('l10n_ar_afip_responsibility_type_id'):
            domain += [('l10n_ar_afip_responsibility_type_ids', '=', self._context.get('l10n_ar_afip_responsibility_type_id'))]
        return domain
