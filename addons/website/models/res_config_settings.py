from urllib.parse import parse_qs, urlsplit

from odoo import api, fields, models
from odoo.libs.debug_log import DebugLog
from odoo.tools.translate import _

_debug = DebugLog(__name__)


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    def _default_website_id(self):
        return self.env["website"].search(
            [("company_id", "=", self.env.company.id)], limit=1
        )

    website_id = fields.Many2one(
        comodel_name="website",
        string="website",
        default=_default_website_id,
        ondelete="cascade",
    )
    website_name = fields.Char(
        related="website_id.name",
        string="Website Name",
        readonly=False,
    )
    website_domain = fields.Char(
        related="website_id.domain",
        string="Website Domain",
        readonly=False,
    )
    website_homepage_url = fields.Char(
        related="website_id.homepage_url",
        readonly=False,
    )
    website_company_id = fields.Many2one(
        related="website_id.company_id",
        string="Website Company",
        readonly=False,
    )
    website_logo = fields.Binary(
        related="website_id.logo",
        readonly=False,
    )
    language_ids = fields.Many2many(
        related="website_id.language_ids",
        readonly=False,
    )
    website_language_count = fields.Integer(
        related="website_id.language_count",
        string="Number of languages",
        readonly=True,
    )
    website_default_lang_id = fields.Many2one(
        related="website_id.default_lang_id",
        string="Default language",
        readonly=False,
    )
    website_default_lang_code = fields.Char(
        related="website_id.default_lang_id.code",
        string="Default language code",
        readonly=False,
    )
    shared_user_account = fields.Boolean(
        string="Shared Customer Accounts",
        compute="_compute_shared_user_account",
        inverse="_inverse_shared_user_account",
    )
    website_cookies_bar = fields.Boolean(
        related="website_id.cookies_bar",
        readonly=False,
    )
    website_block_third_party_domains = fields.Boolean(
        related="website_id.block_third_party_domains",
        string="Block 3rd-party domains",
        readonly=False,
    )
    google_analytics_key = fields.Char(
        related="website_id.google_analytics_key",
        string="Google Analytics Key",
        readonly=False,
    )
    google_search_console = fields.Char(
        related="website_id.google_search_console",
        string="Google Search Console Key",
        readonly=False,
    )
    plausible_shared_key = fields.Char(
        related="website_id.plausible_shared_key",
        string="Plausible auth Key",
        readonly=False,
    )
    plausible_site = fields.Char(
        related="website_id.plausible_site",
        string="Plausible Site (e.g. domain.com)",
        readonly=False,
    )
    cdn_activated = fields.Boolean(
        related="website_id.cdn_activated",
        readonly=False,
    )
    cdn_url = fields.Char(
        related="website_id.cdn_url",
        readonly=False,
    )
    cdn_filters = fields.Text(
        related="website_id.cdn_filters",
        readonly=False,
    )
    auth_signup_uninvited = fields.Selection(
        compute="_compute_auth_signup_uninvited",
        inverse="_inverse_auth_signup_uninvited",
        default=None,
        config_parameter=False,
    )

    favicon = fields.Binary(
        related="website_id.favicon",
        string="Favicon",
        readonly=False,
    )
    social_default_image = fields.Binary(
        related="website_id.social_default_image",
        string="Default Social Share Image",
        readonly=False,
    )

    group_multi_website = fields.Boolean(
        string="Multi-website",
        implied_group="website.group_multi_website",
    )
    has_google_analytics = fields.Boolean(
        string="Google Analytics",
        compute="_compute_has_google_analytics",
        inverse="_inverse_has_google_analytics",
    )
    has_google_search_console = fields.Boolean(
        string="Google Search Console",
        compute="_compute_has_google_search_console",
        inverse="_inverse_has_google_search_console",
    )
    has_default_share_image = fields.Boolean(
        string="Use a image by default for sharing",
        compute="_compute_has_default_share_image",
        inverse="_inverse_has_default_share_image",
    )
    has_plausible_shared_key = fields.Boolean(
        string="Plausible Analytics",
        compute="_compute_has_plausible_shared_key",
        inverse="_inverse_has_plausible_shared_key",
    )
    module_website_livechat = fields.Boolean()

    @api.depends("website_id")
    def _compute_shared_user_account(self):
        for config in self:
            config.shared_user_account = not config.website_id.specific_user_account

    @api.onchange("plausible_shared_key")
    def _onchange_shared_key(self):
        for config in self:
            value = config.plausible_shared_key
            if value and value.startswith("http"):
                try:
                    url = urlsplit(value)
                    config.plausible_shared_key = parse_qs(url.query).get("auth", [""])[
                        0
                    ]
                    config.plausible_site = url.path.split("/")[-1]
                    _debug.logic(
                        "plausible_key_parsed",
                        website=config.website_id.id,
                        site=config.plausible_site,
                    )
                except ValueError:
                    pass

    def _inverse_shared_user_account(self):
        for config in self:
            _debug.lifecycle(
                "shared_user_account",
                website=config.website_id.id,
                shared=config.shared_user_account,
            )
            config.website_id.specific_user_account = not config.shared_user_account

    @api.depends("website_id.auth_signup_uninvited")
    def _compute_auth_signup_uninvited(self):
        for config in self:
            config.auth_signup_uninvited = (
                config.website_id.auth_signup_uninvited or "b2b"
            )

    def _inverse_auth_signup_uninvited(self):
        for config in self:
            _debug.lifecycle(
                "signup_scope",
                website=config.website_id.id,
                scope=config.auth_signup_uninvited,
            )
            config.website_id.auth_signup_uninvited = config.auth_signup_uninvited

    @api.depends("website_id")
    def _compute_has_plausible_shared_key(self):
        for config in self:
            config.has_plausible_shared_key = bool(config.plausible_shared_key)

    def _inverse_has_plausible_shared_key(self):
        for config in self:
            if config.has_plausible_shared_key:
                continue
            _debug.lifecycle("plausible_cleared", website=config.website_id.id)
            config.plausible_shared_key = False
            config.plausible_site = False

    @api.depends("website_id")
    def _compute_has_google_analytics(self):
        for config in self:
            config.has_google_analytics = bool(config.google_analytics_key)

    def _inverse_has_google_analytics(self):
        for config in self:
            if config.has_google_analytics:
                continue
            _debug.lifecycle("google_analytics_cleared", website=config.website_id.id)
            config.google_analytics_key = False

    @api.depends("website_id")
    def _compute_has_google_search_console(self):
        for config in self:
            config.has_google_search_console = bool(config.google_search_console)

    def _inverse_has_google_search_console(self):
        for config in self:
            if not config.has_google_search_console:
                _debug.lifecycle("google_console_cleared", website=config.website_id.id)
                config.google_search_console = False

    @api.depends("website_id")
    def _compute_has_default_share_image(self):
        for config in self:
            config.has_default_share_image = bool(config.social_default_image)

    def _inverse_has_default_share_image(self):
        for config in self:
            if not config.has_default_share_image:
                _debug.lifecycle(
                    "default_share_image_cleared", website=config.website_id.id
                )
                config.social_default_image = False

    @api.onchange("language_ids")
    def _onchange_language_ids(self):
        language_ids = self.language_ids._origin
        if not language_ids:
            _debug.logic("default_lang_reset", reason="no_languages")
            self.website_default_lang_id = False
        elif self.website_default_lang_id not in language_ids:
            _debug.logic(
                "default_lang_reset",
                reason="no_longer_enabled",
                lang=language_ids[0].code,
            )
            self.website_default_lang_id = language_ids[0]

    def action_website_create_new(self):
        return {
            "name": _("Add Website"),
            "view_mode": "form",
            "view_id": self.env.ref("website.view_website_form_view_themes_modal").id,
            "res_model": "website",
            "type": "ir.actions.act_window",
            "target": "new",
            "res_id": False,
        }

    def action_view_robots(self):
        self.website_id._force()
        return {
            "name": _("Robots.txt"),
            "view_mode": "form",
            "res_model": "website.robots",
            "type": "ir.actions.act_window",
            "views": [[False, "form"]],
            "target": "new",
        }

    def action_view_blocked_third_party_domains(self):
        self.website_id._force()
        return {
            "name": _("Add external websites"),
            "view_mode": "form",
            "res_model": "website.custom_blocked_third_party_domains",
            "type": "ir.actions.act_window",
            "views": [[False, "form"]],
            "target": "new",
        }
