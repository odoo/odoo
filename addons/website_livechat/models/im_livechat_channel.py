# Part of Odoo. See LICENSE file for full copyright and licensing details.

import re

from odoo import api, fields, models

# CSS custom properties to read for each color field, best source first.
THEME_COLOR_SOURCES = {
    "primary_color": ("o-color-1", "o-cc1-btn-primary", "primary"),
    "secondary_color": ("o-color-2", "o-cc1-btn-secondary", "secondary"),
}
CSS_COMMENT_PATTERN = re.compile(r"/\*.*?\*/", re.DOTALL)
THEME_COLOR_DECLARATION_PATTERN = re.compile(
    r"--(" + "|".join(re.escape(name) for sources in THEME_COLOR_SOURCES.values() for name in sources) + r"):([^;]*)"
)
HEX_COLOR_PATTERN = re.compile(r"#([0-9a-f]{3}|[0-9a-f]{6})", re.IGNORECASE)
PENDING_SYNC_KEY = "website_livechat.pending_theme_colors_sync"


def normalize_hex_color(value):
    """Return the given color as lowercase #rrggbb, or None if it is not a hex color."""
    match = HEX_COLOR_PATTERN.fullmatch((value or "").strip())
    if not match:
        return None
    digits = match[1].lower()
    return "#" + (digits if len(digits) == 6 else "".join(digit * 2 for digit in digits))


class Im_LivechatChannel(models.Model):
    _name = "im_livechat.channel"
    _inherit = ["im_livechat.channel", "bus.listener.mixin"]

    website_theme_sync_url = fields.Char(compute="_compute_website_theme_sync_url")
    # Stored so that the theme changes know which channels to follow without
    # compiling the website's bundle first, and so that a channel keeps
    # following its website through the intermediate states of a theme change.
    theme_colors_synced = fields.Boolean(
        compute="_compute_theme_colors_synced", store=True, readonly=False,
        help="Whether this channel's colors follow its website's theme.",
    )

    @api.depends()
    def _compute_website_theme_sync_url(self):
        for channel in self:
            website = channel._get_website()
            channel.website_theme_sync_url = website.get_base_url() if website else False

    @api.depends(*THEME_COLOR_SOURCES)
    def _compute_theme_colors_synced(self):
        for channel in self:
            website = channel._get_website()
            theme_colors = channel._read_website_theme_colors(website) if website else {}
            channel.theme_colors_synced = bool(website) and all(
                normalize_hex_color(channel[field]) == value for field, value in theme_colors.items() if value
            )

    def get_website_theme_colors(self):
        """Colors to preview in the form when the user asks to fetch them."""
        self.ensure_one()
        website = self._get_website()
        if not website:
            return {}
        return {
            field: value
            for field, value in self._read_website_theme_colors(website).items()
            if value
        }

    def _get_website(self):
        """The website whose theme this channel follows. When several websites
        share the channel, the first one is the reference so that the palette
        of another one never overrides it."""
        self.ensure_one()
        if not self._origin.id:
            return self.env["website"]
        return self.env["website"].sudo().search([("channel_id", "=", self._origin.id)], limit=1)

    def _schedule_theme_colors_sync(self):
        """Sync the channels with their website's theme once the transaction
        is about to be committed, when the bundle has the new theme colors."""
        if not self:
            return
        pending_ids = self.env.cr.precommit.data.setdefault(PENDING_SYNC_KEY, set())
        if not pending_ids:
            self.env.cr.precommit.add(self._sync_theme_colors)
        pending_ids.update(self.ids)

    def _sync_theme_colors(self):
        channel_ids = self.env.cr.precommit.data.pop(PENDING_SYNC_KEY, set())
        channels = self.env["im_livechat.channel"].sudo().browse(channel_ids).exists()
        for channel in channels.filtered("theme_colors_synced"):
            colors = channel.get_website_theme_colors()
            if any(normalize_hex_color(channel[field]) != value for field, value in colors.items()):
                channel.write({**colors, "theme_colors_synced": True})
                channel._bus_send(
                    "im_livechat.channel/theme_colors_synced",
                    {"id": channel.id},
                    subchannel="THEME_SYNC",
                )

    def _has_default_colors(self):
        self.ensure_one()
        return all(
            normalize_hex_color(self[field]) == normalize_hex_color(value)
            for field, value in self._get_default_colors().items()
        )

    def _read_website_theme_colors(self, website):
        """Read the website's theme colors from its compiled frontend bundle,
        where Bootstrap prints them as resolved :root custom properties.

        o-color-1/o-color-2 come first because they are the slots the color
        picker writes to, for a whole preset palette as well as for a single
        swatch. The combination 1 button colors are only a fallback for a
        theme that does not define those slots, since a theme may point them
        at another slot or at a literal. The theme's global colors are the
        last resort, as a key left undefined comes through empty.

        Only :root rules count, other selectors scope the property to part of
        the page. Values that are not hex colors are skipped, the embed can
        only derive its colors from those.
        """
        bundle = self.env["ir.qweb"].with_context(website_id=website.id)._get_asset_bundle(
            "web.assets_frontend", css=True, js=False,
        )
        css_text = bundle.css().raw.decode("utf-8")
        colors_by_name = {}
        # Plain string search: running a regex over every rule of the ~1MB
        # bundle is about ten times slower.
        position = css_text.find(":root")
        while position != -1:
            selector_start = max(css_text.rfind("}", 0, position), css_text.rfind("{", 0, position)) + 1
            block_start = css_text.find("{", position)
            block_end = css_text.find("}", block_start)
            if block_start == -1 or block_end == -1:
                break
            selectors = CSS_COMMENT_PATTERN.sub("", css_text[selector_start:block_start]).split(",")
            if ":root" not in (selector.strip() for selector in selectors):
                position = css_text.find(":root", position + 1)
                continue
            for declaration in THEME_COLOR_DECLARATION_PATTERN.finditer(css_text, block_start, block_end):
                # Later declarations win the cascade, so overwrite earlier ones.
                colors_by_name[declaration[1]] = declaration[2].strip()
            position = css_text.find(":root", block_end)
        return {
            field: next(
                (color for name in sources if (color := normalize_hex_color(colors_by_name.get(name)))),
                None,
            )
            for field, sources in THEME_COLOR_SOURCES.items()
        }

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
