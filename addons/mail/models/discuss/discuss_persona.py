# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, fields, tools


class DiscussPersona(models.Model):
    _name = "discuss.persona"
    _description = ""
    _auto = False
    _order = False

    partner_id = fields.Many2one("res.partner")
    guest_id = fields.Many2one("mail.guest")

    channel_ids = fields.Many2many("discuss.channel", compute="_compute_channel_ids")
    def _compute_channel_ids(self):
        for persona in self:
            if persona.partner_id:
                persona.channel_ids = persona.partner_id.channel_ids
            else:
                persona.channel_ids = persona.guest_id.channel_ids

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        # Reference contract is the one with the latest start_date.
        self.env.cr.execute("""CREATE or REPLACE VIEW %s AS (
        SELECT id, id as partner_id, NULL as guest_id, 'partner' as type FROM res_partner
        UNION
        SELECT id, NULL as partner_id, id as guest_id, 'guest' as type from mail_guest
        )""" % (self._table))

    @api.model
    def _get_current_persona(self):
        if not self.env.user or self.env.user._is_public():
            guest = self.env["mail.guest"]._get_guest_from_context()
            return self.sudo().search([["guest_id.id", "=", guest.id]])
        return self.sudo().search([["partner_id.id", "=", self.env.user.partner_id.id]])
