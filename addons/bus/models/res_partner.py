# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ResPartner(models.Model):
    _name = "res.partner"
    _inherit = ["res.partner", "bus.listener.mixin"]

    im_status = fields.Char('IM Status', compute='_compute_im_status')

    def _compute_im_status(self):
        status_by_partner = {}
        for presence in self.env["bus.presence"].search([("user_id", "in", self.user_ids.ids)]):
            partner = presence.user_id.partner_id
            if (
                status_by_partner.get(partner, "offline") == "offline"
                or presence.status == "online"
            ):
                status_by_partner[partner] = presence.status
        for partner in self:
            default_status = "offline" if partner.user_ids else "im_partner"
            partner.im_status = status_by_partner.get(partner, default_status)
