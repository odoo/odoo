# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api


class MailGuest(models.Model):
    _inherit = "mail.guest"

    visitor_id = fields.One2many(comodel_name="website.visitor", inverse_name="guest_id")

    website_name = fields.Char(related="visitor_id.website_id.name")
    lang_name = fields.Char(related="visitor_id.lang_id.name")
    is_connected = fields.Boolean(related="visitor_id.is_connected")
    history = fields.Char(compute="_compute_history")

    @api.depends("visitor_id")
    def _compute_history(self):
        for guest in self:
            guest.history = guest.visitor_id.sudo()._get_visitor_history() if guest.visitor_id else None

    def _to_store_defaults(self):
        return super()._to_store_defaults() + ["website_name", "history", "is_connected", "lang_name"]
