# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api


class MailCannedResponse(models.Model):
    """
    Canned Response: content that will automatically replace the shortcut of your choosing. This content can still be adapted before sending your message.
    """

    _name = "mail.canned_response"
    _description = "Canned Response"
    source = fields.Char(
        "Shortcut",
        required=True,
        index="trigram",
        help="Canned response that will automatically be substituted with longer content in your messages."
        " Type ':' followed by the name of your shortcut (e.g. :hello) to use in your messages.",
    )
    substitution = fields.Text(
        "Substitution",
        required=True,
        help="Content that will automatically replace the shortcut of your choosing. This content can still be adapted before sending your message.",
    )
    description = fields.Char("Description")
    last_used = fields.Datetime("Last Used", help="Last time this canned_response was used")
    group_ids = fields.Many2many("res.groups", string="Authorized Groups", groups="mail.canned_response_administrator")
    is_shared = fields.Boolean(
        string="Determines if the canned_response is currently shared with other users",
        compute="_compute_is_shared",
        store=True,
    )
    is_editable = fields.Boolean(
        string="Determines if the canned response can be edited by the current user", compute="_compute_is_editable"
    )

    @api.depends("create_uid")
    def _compute_is_editable(self):
        for canned_response in self:
            canned_response.is_editable = bool(
                self.env.is_admin() or canned_response.create_uid.id == self.env.uid or not canned_response.id
            )

    @api.depends("group_ids")
    def _compute_is_shared(self):
        for canned_response in self:
            canned_response.is_shared = bool(canned_response.group_ids or canned_response.user_ids)

    @api.model_create_multi
    def create(self, vals_list):
        res = super().create(vals_list)
        for canned_response in res:
            payload = {"CannedResponse": canned_response._read_format(["id", "source", "substitution"])}
            notifications = [(self.env.user.partner_id, "mail.record/insert", payload)]
            for group in canned_response.group_ids:
                notifications.append((group, "mail.record/insert", payload))
            self.env["bus.bus"]._sendmany(notifications)
        return res

    def write(self, vals):
        res = super().write(vals)
        payload = {"CannedResponse": self._read_format(["id", "source", "substitution"])}
        notifications = [(self.env.user.partner_id, "mail.record/insert", payload)]
        for group in self.group_ids:
            notifications.append((group, "mail.record/insert", payload))
        self.env["bus.bus"]._sendmany(notifications)
        return res

    def unlink(self):
        payload = self._read_format(["id"])
        notifications = [(self.env.user.partner_id, "mail.cannedResponse/delete", payload)]
        for group in self.group_ids:
            notifications.append((group, "mail.cannedReponse/delete", payload))
        self.env["bus.bus"]._sendmany(notifications)
        return super().unlink()
