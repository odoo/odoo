# Part of Odoo. See LICENSE file for full copyright and licensing details.

import pytz
import uuid
from datetime import datetime, timedelta

from odoo.tools import consteq
from odoo import _, api, fields, models
from odoo.http import request
from odoo.addons.base.models.res_partner import _tz_get
from odoo.exceptions import UserError
from odoo.tools.misc import limited_field_access_token
from odoo.addons.mail.tools.discuss import Store


class MailGuest(models.Model):
    _name = 'mail.guest'
    _description = "Guest"
    _inherit = ["avatar.mixin", "bus.listener.mixin"]
    _avatar_name_field = "name"
    _cookie_name = 'dgid'
    _cookie_separator = '|'

    @api.model
    def _lang_get(self):
        return self.env['res.lang'].get_installed()

    name = fields.Char(string="Name", required=True)
    access_token = fields.Char(string="Access Token", default=lambda self: str(uuid.uuid4()), groups='base.group_system', required=True, readonly=True, copy=False)
    country_id = fields.Many2one(string="Country", comodel_name='res.country')
    lang = fields.Selection(string="Language", selection=_lang_get)
    timezone = fields.Selection(string="Timezone", selection=_tz_get)
    channel_ids = fields.Many2many(string="Channels", comodel_name='discuss.channel', relation='discuss_channel_member', column1='guest_id', column2='channel_id', copy=False)
    presence_ids = fields.One2many("mail.presence", "guest_id", groups="base.group_system")
    # sudo: mail.guest - can access presence of accessible guest
    im_status = fields.Char("IM Status", compute="_compute_im_status", compute_sudo=True)

    @api.depends("presence_ids.status")
    def _compute_im_status(self):
        for guest in self:
            guest.im_status = guest.presence_ids.status or "offline"

    def _get_guest_from_token(self, token=""):
        """Returns the guest record for the given token, if applicable."""
        guest = self.env["mail.guest"]
        parts = token.split(self._cookie_separator)
        if len(parts) == 2:
            guest_id, guest_access_token = parts
            # sudo: mail.guest: guests need sudo to read their access_token
            guest = self.browse(int(guest_id)).sudo().exists()
            if not guest or not guest.access_token or not consteq(guest.access_token, guest_access_token):
                guest = self.env["mail.guest"]
        return guest.sudo(False)

    def _get_guest_from_context(self):
        """Returns the current guest record from the context, if applicable."""
        guest = self.env.context.get('guest')
        if isinstance(guest, self.pool['mail.guest']):
            return guest.sudo(False).with_context(guest=guest)
        return self.env['mail.guest']

    def _get_timezone_from_request(self, request):
        timezone = request.cookies.get('tz')
        return timezone if timezone in pytz.all_timezones else False

    def _update_name(self, name):
        self.ensure_one()
        name = name.strip()
        if len(name) < 1:
            raise UserError(_("Guest's name cannot be empty."))
        if len(name) > 512:
            raise UserError(_("Guest's name is too long."))
        self.name = name
        store = Store(self, ["avatar_128", "name"])
        self.channel_ids._bus_send_store(store)
        self._bus_send_store(store)

    def _update_timezone(self, timezone):
        query = """
            UPDATE mail_guest
            SET timezone = %s
            WHERE id IN (
                SELECT id FROM mail_guest WHERE id = %s
                FOR NO KEY UPDATE SKIP LOCKED
            )
        """
        self.env.cr.execute(query, (timezone, self.id))

    def _field_store_repr(self, field_name):
        if field_name == "avatar_128":
            return [
                Store.Attr(
                    "avatar_128_access_token", lambda g: limited_field_access_token(g, "avatar_128")
                ),
                "write_date",
            ]
        return [field_name]

    def _to_store_defaults(self):
        return ["avatar_128", "im_status", "name"]

    def _set_auth_cookie(self):
        """Add a cookie to the response to identify the guest. Every route
        that expects a guest will make use of it to authenticate the guest
        through `add_guest_to_context`.
        """
        self.ensure_one()
        expiration_date = datetime.now() + timedelta(days=365)
        request.future_response.set_cookie(
            self._cookie_name,
            self._format_auth_cookie(),
            httponly=True,
            expires=expiration_date,
        )
        request.update_context(guest=self.sudo(False))

    def _format_auth_cookie(self):
        """Format the cookie value for the given guest.

        :param guest: guest to format the cookie value for
        :return str: formatted cookie value
        """
        self.ensure_one()
        return f"{self.id}{self._cookie_separator}{self.access_token}"
