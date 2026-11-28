# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import re

from odoo import api, fields, models

_logger = logging.getLogger(__name__)

# CSS custom properties to read for each color field, best source first.
THEME_COLOR_SOURCES = {
    "primary_color": ("o-color-1", "primary"),
    "secondary_color": ("o-color-2", "secondary"),
}
THEME_COLOR_DECLARATION_PATTERN = re.compile(
    r"--(" + "|".join(re.escape(name) for sources in THEME_COLOR_SOURCES.values() for name in sources) + r"):\s*([^;}]*)"
)
HEX_COLOR_PATTERN = re.compile(r"#([0-9a-f]{3}|[0-9a-f]{6})", re.IGNORECASE)


def normalize_hex_color(value):
    """Return the given color as lowercase #rrggbb, or None if it is not a hex color."""
    match = HEX_COLOR_PATTERN.fullmatch((value or "").strip())
    if not match:
        return None
    digits = match[1].lower()
    return "#" + (digits if len(digits) == 6 else "".join(digit * 2 for digit in digits))


class Im_LivechatChannel(models.Model):
    _inherit = 'im_livechat.channel'

    has_website = fields.Boolean(compute="_compute_has_website")
    follow_website_theme = fields.Boolean(
        default=True,
        help="Use the colors of the website theme. They are read when the live chat loads, "
             "so a theme change applies at once.",
    )
    # Shown in the form while the channel follows its website.
    website_primary_color = fields.Char(compute="_compute_website_colors")
    website_secondary_color = fields.Char(compute="_compute_website_colors")

    @api.depends()
    def _compute_has_website(self):
        for channel in self:
            channel.has_website = bool(channel._get_website())

    @api.depends("follow_website_theme")
    def _compute_website_colors(self):
        for channel in self:
            colors = channel._get_livechat_colors()
            channel.website_primary_color = colors["primary_color"]
            channel.website_secondary_color = colors["secondary_color"]

    @api.onchange("follow_website_theme")
    def _onchange_follow_website_theme(self):
        # Start the custom colors from the theme rather than from older values.
        if not self.follow_website_theme and (website := self._get_website()):
            self.update(self._get_website_theme_colors(website))

    def _get_livechat_colors(self):
        colors = super()._get_livechat_colors()
        if self.follow_website_theme and (website := self._get_website()):
            colors.update(self._get_website_theme_colors(website))
        return colors

    def _get_website(self):
        """The website whose theme this channel follows: the current one when
        it uses this channel, else the first website that uses it."""
        self.ensure_one()
        if not self._origin.id:
            return self.env["website"]
        if self.env.website.channel_id == self._origin:
            return self.env.website.sudo()
        return self.env["website"].sudo().search([("channel_id", "=", self._origin.id)], limit=1)

    def _has_default_colors(self):
        self.ensure_one()
        return all(
            normalize_hex_color(self[field]) == normalize_hex_color(value)
            for field, value in self._get_default_colors().items()
        )

    def _get_website_theme_colors(self, website):
        """Read the website's theme colors from its scss exports. The export is
        cached for each theme state (see website._get_scss_exports), and the
        <head> of each page reads it too, so this does not compile anything on
        a page view.

        o-color-1/o-color-2 come first because they are the slots the color
        picker writes to, for a whole preset palette as well as for a single
        swatch. The theme's global colors are the fallback, as a key left
        undefined comes through empty.

        Colors that are not opaque are skipped, the embed can only derive its
        colors from those. A failing export must not break the live chat, so
        it reads as no colors and the channel's own colors apply.
        """
        try:
            scss_exports = website.with_context(website_id=website.id)._get_scss_exports()
        except Exception:  # noqa: BLE001
            _logger.warning("Could not read the theme colors of website %s", website.id, exc_info=True)
            return {}
        colors_by_name = dict(THEME_COLOR_DECLARATION_PATTERN.findall(scss_exports))
        colors = {}
        for field, sources in THEME_COLOR_SOURCES.items():
            if color := next(filter(None, (normalize_hex_color(colors_by_name.get(name)) for name in sources)), None):
                colors[field] = color
        return colors

    def _get_livechat_discuss_channel_vals(self, /, *, chatbot_script=None, agent=None, operator_partner, operator_model, **kwargs):
        discuss_channel_vals = super()._get_livechat_discuss_channel_vals(
            agent=agent,
            chatbot_script=chatbot_script,
            operator_partner=operator_partner,
            operator_model=operator_model,
            **kwargs
        )
        if not discuss_channel_vals:
            return False
        visitor_sudo = self.env['ir.http']._get_visitor_from_request()
        if visitor_sudo:
            discuss_channel_vals['livechat_visitor_id'] = visitor_sudo.id
            # As chat requested by the visitor, delete the chat requested by an operator if any to avoid conflicts between two flows
            # TODO DBE : Move this into the proper method (open or init mail channel)
            pending_chats_domain = [
                ("is_pending_chat_request", "=", True),
                ("livechat_visitor_id", "=", visitor_sudo.id),
                ("livechat_end_dt", "=", False),
            ]
            for discuss_channel in self.env["discuss.channel"].sudo().search(pending_chats_domain):
                correspondents = (
                    discuss_channel.livechat_agent_partner_ids
                    or discuss_channel.livechat_bot_partner_ids
                )
                discuss_channel._close_livechat_session(
                    message=discuss_channel._get_visitor_leave_message(
                        cancel=True, correspondents=correspondents
                    )
                )
                discuss_channel.is_pending_chat_request = False

        return discuss_channel_vals

    @api.model_create_multi
    def create(self, vals_list):
        channels = super().create(vals_list)
        if self.env.context.get("create_from_website"):
            bot = self.env.ref("im_livechat.chatbot_script_welcome_bot", raise_if_not_found=False)
            self.env.website.channel_id = channels[0].id
            channel_rule_vals = []
            for channel in channels:
                if bot:
                    channel_rule_vals.append({
                        'channel_id': channel.id,
                        'action': 'display_button',
                        'chatbot_script_id': bot.id,
                        'chatbot_enabled_condition': 'always',
                    })
                self.env.user._bus_send(
                    "simple_notification",
                    {
                        "type": "success",
                        "message": self.env._("Channel created: %(name)s", name=channel.name),
                    },
                )
            if channel_rule_vals:
                self.env["im_livechat.channel.rule"].create(channel_rule_vals)
        return channels
