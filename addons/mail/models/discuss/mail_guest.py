# Part of Odoo. See LICENSE file for full copyright and licensing details.

import pytz
import uuid
from datetime import datetime, timedelta
from functools import wraps
from inspect import Parameter, signature
from werkzeug.exceptions import NotFound

from odoo.tools import consteq, get_lang
from odoo import _, api, fields, models
from odoo.http import request
from odoo.addons.base.models.res_partner import _tz_get
from odoo.exceptions import UserError
from odoo.addons.bus.models.bus_presence import AWAY_TIMER, DISCONNECTION_TIMER
from odoo.addons.bus.websocket import wsrequest


def add_guest_to_context(func):
    """ Decorate a function to extract the guest from the request.
    The guest is then available on the context of the current
    request.
    """
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        req = request or wsrequest
        token = (
            req.httprequest.cookies.get(req.env["mail.guest"]._cookie_name)
            or req.env.context.get("guest_token", "")
        )
        guest = req.env["mail.guest"]._get_guest_from_token(token)
        if guest and not guest.timezone:
            timezone = req.env["mail.guest"]._get_timezone_from_request(req)
            if timezone:
                guest._update_timezone(timezone)
        if guest:
            req.update_context(guest=guest)
            if hasattr(self, "env"):
                self.env.context = {**self.env.context, "guest": guest}
        return func(self, *args, **kwargs)

    return wrapper


class MailGuest(models.Model):
    _name = 'mail.guest'
    _description = "Guest"
    _inherit = ['avatar.mixin']
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
    im_status = fields.Char('IM Status', compute='_compute_im_status')

    def _compute_im_status(self):
        self.env.cr.execute("""
            SELECT
                guest_id as id,
                CASE WHEN age(now() AT TIME ZONE 'UTC', last_poll) > interval %s THEN 'offline'
                     WHEN age(now() AT TIME ZONE 'UTC', last_presence) > interval %s THEN 'away'
                     ELSE 'online'
                END as status
            FROM bus_presence
            WHERE guest_id IN %s
        """, ("%s seconds" % DISCONNECTION_TIMER, "%s seconds" % AWAY_TIMER, tuple(self.ids)))
        res = dict(((status['id'], status['status']) for status in self.env.cr.dictfetchall()))
        for guest in self:
            guest.im_status = res.get(guest.id, 'offline')

    def _get_guest_from_token(self, token=""):
        """Returns the guest record for the given token, if applicable."""
        guest = self.env["mail.guest"]
        parts = token.split(self._cookie_separator)
        if len(parts) == 2:
            guest_id, guest_access_token = parts
            guest = self.browse(int(guest_id)).sudo().exists()
            if not guest or not guest.access_token or not consteq(guest.access_token, guest_access_token):
                guest = self.env["mail.guest"]
        return guest.sudo(False)

    def _get_guest_from_context(self):
        """Returns the current guest record from the context, if applicable."""
        guest = self.env.context.get('guest')
        if isinstance(guest, self.pool['mail.guest']):
            return guest.with_context(guest=guest)
        return self.env['mail.guest']

    def _get_timezone_from_request(self, request):
        timezone = request.httprequest.cookies.get('tz')
        return timezone if timezone in pytz.all_timezones else False

    def _update_name(self, name):
        self.ensure_one()
        name = name.strip()
        if len(name) < 1:
            raise UserError(_("Guest's name cannot be empty."))
        if len(name) > 512:
            raise UserError(_("Guest's name is too long."))
        self.name = name
        guest_data = {
            'id': self.id,
            'name': self.name
        }
        bus_notifs = [(channel, 'mail.record/insert', {'Guest': guest_data}) for channel in self.channel_ids]
        bus_notifs.append((self, 'mail.record/insert', {'Guest': guest_data}))
        self.env['bus.bus']._sendmany(bus_notifs)

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

    def _init_messaging(self):
        self.ensure_one()
        odoobot = self.env.ref('base.partner_root')
        return {
            'channels': self.channel_ids._channel_info(),
            'companyName': self.env.company.name,
            'currentGuest': {
                'id': self.id,
                'name': self.name,
                'type': "guest",
            },
            'current_partner': False,
            'current_user_id': False,
            'current_user_settings': False,
            'hasGifPickerFeature': bool(self.env["ir.config_parameter"].sudo().get_param("discuss.tenor_api_key")),
            'hasLinkPreviewFeature': self.env['mail.link.preview']._is_link_preview_enabled(),
            'initBusId': self.env['bus.bus'].sudo()._bus_last_id(),
            'menu_id': False,
            'needaction_inbox_counter': False,
            'odoobot': {
                'id': odoobot.id,
                'name': odoobot.name,
                'type': "partner",
            },
            'shortcodes': [],
            'starred_counter': False,
        }

    def _guest_format(self, fields=None):
        if not fields:
            fields = {'id': True, 'name': True, 'im_status': True}
        guests_formatted_data = {}
        for guest in self:
            data = {}
            if 'id' in fields:
                data['id'] = guest.id
            if 'name' in fields:
                data['name'] = guest.name
            if 'im_status' in fields:
                data['im_status'] = guest.im_status
            data['type'] = "guest"
            guests_formatted_data[guest] = data
        return guests_formatted_data

    def _find_or_create_for_channel(self, channel, name, country_id, timezone, add_as_member=True, post_joined_message=False):
        """Get a guest for the given channel. If there is no guest yet,
        create one.

        :param channel: channel to add the guest to
        :param guest_name: name of the guest
        :param country_id: country of the guest
        :param timezone: timezone of the guest
        :param add_as_member: whether to add the guest as a member of the channel
        :param post_joined_message: whether to post a message to the channel
            to notify that the guest joined
        """
        if channel.group_public_id:
            raise NotFound()
        guest = self._get_guest_from_context()
        if not guest:
            guest = self.create(
                {
                    "country_id": country_id,
                    "lang": get_lang(channel.env).code,
                    "name": name,
                    "timezone": timezone,
                }
            )
        if add_as_member:
            channel = channel.with_context(guest=guest)
            try:
                channel.add_members(guest_ids=[guest.id], post_joined_message=post_joined_message)
            except UserError:
                raise NotFound()
        return guest

    def _set_auth_cookie(self):
        """Add a cookie to the response to identify the guest. Every route
        that expects a guest will make use of it to authenticate the guest
        through `_get_as_sudo_from_context` or `_get_as_sudo_from_context_or_raise`.
        """
        self.ensure_one()
        expiration_date = datetime.now() + timedelta(days=365)
        request.future_response.set_cookie(
            self._cookie_name,
            self._format_auth_cookie(),
            httponly=True,
            expires=expiration_date,
        )

    def _format_auth_cookie(self):
        """Format the cookie value for the given guest.

        :param guest: guest to format the cookie value for
        :return str: formatted cookie value
        """
        self.ensure_one()
        return f"{self.id}{self._cookie_separator}{self.access_token}"
