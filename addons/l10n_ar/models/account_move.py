# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models, api, fields
from odoo.addons.l10n_ar.models.res_partner import ResPartner


class AccountMove(models.Model):

    _inherit = 'account.move'

    l10n_ar_afip_responsability_type = fields.Selection(
        ResPartner._afip_responsabilities,
        'AFIP Responsability Type',
        index=True,
        help='Responsability type from journal entry where it is stored and '
        'it nevers change',
    )

    @api.constrains('partner_id')
    def set_l10n_ar_afip_responsability_type(self):
        for rec in self:
            commercial_partner = rec.partner_id.commercial_partner_id
            rec.l10n_ar_afip_responsability_type = (
                commercial_partner.l10n_ar_afip_responsability_type)
