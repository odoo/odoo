# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models, api, fields


class AccountMove(models.Model):

    _inherit = 'account.move'

    l10n_ar_afip_responsability_type = fields.Selection(
        selection='_get_afip_responsabilities',
        string='AFIP Responsability Type',
    )

    @api.constrains('partner_id')
    def set_l10n_ar_afip_responsability_type(self):
        for rec in self:
            commercial_partner = rec.partner_id.commercial_partner_id
            rec.l10n_ar_afip_responsability_type = (
                commercial_partner.l10n_ar_afip_responsability_type)

    def _get_afip_responsabilities(self):
        """ Return the list of values of the selection field """
        return self.env['res.partner']._get_afip_responsabilities()
