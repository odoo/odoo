# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    def write(self, vals):
        """ Archive all SDD tokens if the commercial partner is updated.

        Those tokens cannot be kept active because the partner wouldn't be able to use them anymore.
        """
        # Remember all the current commercial partners
        commercial_partners = {}
        for partner in self:
            commercial_partners[partner.id] = partner.commercial_partner_id

        # Apply the updates
        res = super().write(vals)

        # Find all updated commercial partners
        partners_with_new_commercial = self.env['res.partner']
        for partner in self:
            if commercial_partners[partner.id] != partner.commercial_partner_id:
                partners_with_new_commercial |= partner

        # Archive related tokens
        if partners_with_new_commercial:
            linked_tokens_sudo = self.env['payment.token'].sudo().search([
                ('partner_id', 'in', partners_with_new_commercial.ids),
                ('provider_id.code', '=', 'custom'),
                ('provider_id.custom_mode', '=', 'sepa_direct_debit'),
            ])
            linked_tokens_sudo.active = False

        return res
