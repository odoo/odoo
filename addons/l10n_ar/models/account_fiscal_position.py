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
        company = self.env.company
        if company.country_id.code == "AR":
            self = self.with_context(l10n_ar_afip_responsibility_type_id=partner.l10n_ar_afip_responsibility_type_id.id)
        return super()._get_fiscal_position(partner, delivery=delivery)

    @api.model
    def _search(self, args, offset=0, limit=None, order=None, count=False, access_rights_uid=None):
        """ Take into account the partner afip responsibility in order to auto-detect the fiscal position """
        if 'l10n_ar_afip_responsibility_type_id' in self._context:
            args += [
                '|',
                ('l10n_ar_afip_responsibility_type_ids', '=', False),
                ('l10n_ar_afip_responsibility_type_ids', '=', self._context.get('l10n_ar_afip_responsibility_type_id'))]
        return super()._search(args, offset, limit, order, count=count, access_rights_uid=access_rights_uid)
