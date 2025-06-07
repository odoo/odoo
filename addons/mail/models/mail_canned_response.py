# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api
from odoo.addons.mail.tools.discuss import Store


class MailCannedResponse(models.Model):
    """
    Canned Response: content that will automatically replace the shortcut of your choosing. This content can still be adapted before sending your message.
    """

    _name = "mail.canned.response"
    _description = "Canned Response"
    _order = "id desc"
    _rec_name = "source"

    source = fields.Char(
        "Shortcut", required=True, index="trigram",
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
    group_ids = fields.Many2many("res.groups", string="Authorized Groups")
    is_shared = fields.Boolean(
        string="Determines if the canned_response is currently shared with other users",
        compute="_compute_is_shared",
        store=True,
    )
    is_editable = fields.Boolean(
        string="Determines if the canned response can be edited by the current user",
        compute="_compute_is_editable"
    )

    @api.depends("group_ids")
    def _compute_is_shared(self):
        for canned_response in self:
            canned_response.is_shared = bool(canned_response.group_ids)

    @api.depends_context('uid')
    @api.depends("create_uid")
    def _compute_is_editable(self):
        creating = self.filtered(lambda c: not c.id)
        updating = self - creating
        editable = creating._filtered_access("create") + updating._filtered_access("write")
        editable.is_editable = True
        (self - editable).is_editable = False

    @api.model_create_multi
    def create(self, vals_list):
        res = super().create(vals_list)
        res._broadcast()
        return res

    def write(self, vals):
        res = super().write(vals)
        self._broadcast()
        return res

    def unlink(self):
        self._broadcast(delete=True)
        return super().unlink()

    def _broadcast(self, /, *, delete=False):
        for canned_response in self:
            store = Store(canned_response, delete=delete)
            (self.env.user | canned_response.create_uid)._bus_send_store(store)
            canned_response.group_ids._bus_send_store(store)

    def _to_store(self, store: Store, /, *, fields=None):
        if fields is None:
            fields = ["source", "substitution"]
        store.add(self._name, self._read_format(fields))
