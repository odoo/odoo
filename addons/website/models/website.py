import base64
import fnmatch
import functools
import hashlib
import inspect
import logging
import re
import threading
import types
from urllib.parse import urlencode, urlparse, urlunparse

import werkzeug.routing
from lxml import etree, html

from odoo import api, fields, models, tools
from odoo.exceptions import AccessError, MissingError, UserError, ValidationError
from odoo.fields import Domain
from odoo.http import request
from odoo.libs.debug_log import DebugLog
from odoo.libs.sql import escape_psql
from odoo.libs.web import contains_dot_segments
from odoo.tools import SQL
from odoo.tools.image import image_process
from odoo.tools.translate import _

from odoo.addons.portal.controllers.portal import pager
from odoo.addons.website.models.ir_http import sitemap_qs2dom
from odoo.addons.website.tools import get_base_hostname

logger = logging.getLogger(__name__)
_debug = DebugLog(__name__)


DEFAULT_CDN_FILTERS = [
    "^/[^/]+/static/",
    "^/web/(css|js)/",
    "^/web/image",
    "^/web/content",
    "^/web/assets",
    "^/website/image/",
]

TEMPLATE_AFFECTING_FIELDS = frozenset(
    {
        "cdn_activated",
        "cdn_url",
        "cdn_filters",
        "cookies_bar",
        "block_third_party_domains",
        "custom_blocked_third_party_domains",
    }
)


DEFAULT_BLOCKED_THIRD_PARTY_DOMAINS = "youtu.be\nyoutube.com\nyoutube-nocookie.com\ninstagram.com\ninstagr.am\nig.me\nvimeo.com\ndailymotion.com\ndai.ly\nyouku.com\ntudou.com\nfacebook.com\nfacebook.net\nfb.com\nfb.me\nfb.watch\ntiktok.com\nx.com\ntwitter.com\nt.co\ngoogletagmanager.com\ngoogle-analytics.com\ngoogle.com\ngoogle.ad\ngoogle.ae\ngoogle.com.af\ngoogle.com.ag\ngoogle.al\ngoogle.am\ngoogle.co.ao\ngoogle.com.ar\ngoogle.as\ngoogle.at\ngoogle.com.au\ngoogle.az\ngoogle.ba\ngoogle.com.bd\ngoogle.be\ngoogle.bf\ngoogle.bg\ngoogle.com.bh\ngoogle.bi\ngoogle.bj\ngoogle.com.bn\ngoogle.com.bo\ngoogle.com.br\ngoogle.bs\ngoogle.bt\ngoogle.co.bw\ngoogle.by\ngoogle.com.bz\ngoogle.ca\ngoogle.cd\ngoogle.cf\ngoogle.cg\ngoogle.ch\ngoogle.ci\ngoogle.co.ck\ngoogle.cl\ngoogle.cm\ngoogle.cn\ngoogle.com.co\ngoogle.co.cr\ngoogle.com.cu\ngoogle.cv\ngoogle.com.cy\ngoogle.cz\ngoogle.de\ngoogle.dj\ngoogle.dk\ngoogle.dm\ngoogle.com.do\ngoogle.dz\ngoogle.com.ec\ngoogle.ee\ngoogle.com.eg\ngoogle.es\ngoogle.com.et\ngoogle.fi\ngoogle.com.fj\ngoogle.fm\ngoogle.fr\ngoogle.ga\ngoogle.ge\ngoogle.gg\ngoogle.com.gh\ngoogle.com.gi\ngoogle.gl\ngoogle.gm\ngoogle.gr\ngoogle.com.gt\ngoogle.gy\ngoogle.com.hk\ngoogle.hn\ngoogle.hr\ngoogle.ht\ngoogle.hu\ngoogle.co.id\ngoogle.ie\ngoogle.co.il\ngoogle.im\ngoogle.co.in\ngoogle.iq\ngoogle.is\ngoogle.it\ngoogle.je\ngoogle.com.jm\ngoogle.jo\ngoogle.co.jp\ngoogle.co.ke\ngoogle.com.kh\ngoogle.ki\ngoogle.kg\ngoogle.co.kr\ngoogle.com.kw\ngoogle.kz\ngoogle.la\ngoogle.com.lb\ngoogle.li\ngoogle.lk\ngoogle.co.ls\ngoogle.lt\ngoogle.lu\ngoogle.lv\ngoogle.com.ly\ngoogle.co.ma\ngoogle.md\ngoogle.me\ngoogle.mg\ngoogle.mk\ngoogle.ml\ngoogle.com.mm\ngoogle.mn\ngoogle.com.mt\ngoogle.mu\ngoogle.mv\ngoogle.mw\ngoogle.com.mx\ngoogle.com.my\ngoogle.co.mz\ngoogle.com.na\ngoogle.com.ng\ngoogle.com.ni\ngoogle.ne\ngoogle.nl\ngoogle.no\ngoogle.com.np\ngoogle.nr\ngoogle.nu\ngoogle.co.nz\ngoogle.com.om\ngoogle.com.pa\ngoogle.com.pe\ngoogle.com.pg\ngoogle.com.ph\ngoogle.com.pk\ngoogle.pl\ngoogle.pn\ngoogle.com.pr\ngoogle.ps\ngoogle.pt\ngoogle.com.py\ngoogle.com.qa\ngoogle.ro\ngoogle.ru\ngoogle.rw\ngoogle.com.sa\ngoogle.com.sb\ngoogle.sc\ngoogle.se\ngoogle.com.sg\ngoogle.sh\ngoogle.si\ngoogle.sk\ngoogle.com.sl\ngoogle.sn\ngoogle.so\ngoogle.sm\ngoogle.sr\ngoogle.st\ngoogle.com.sv\ngoogle.td\ngoogle.tg\ngoogle.co.th\ngoogle.com.tj\ngoogle.tl\ngoogle.tm\ngoogle.tn\ngoogle.to\ngoogle.com.tr\ngoogle.tt\ngoogle.com.tw\ngoogle.co.tz\ngoogle.com.ua\ngoogle.co.ug\ngoogle.co.uk\ngoogle.com.uy\ngoogle.co.uz\ngoogle.com.vc\ngoogle.co.ve\ngoogle.co.vi\ngoogle.com.vn\ngoogle.vu\ngoogle.ws\ngoogle.rs\ngoogle.co.za\ngoogle.co.zm\ngoogle.co.zw\ngoogle.cat"


def normalize_sitemap_url(url):
    return "/" if url == "/" else url.rstrip("/")


def get_underlying_function(f):
    if isinstance(f, functools.partial):
        f = f.func
    if isinstance(f, types.MethodType):
        return f.__func__
    return f


def to_punycode(host):
    try:
        return host.encode("idna").decode("ascii")
    except UnicodeError:
        return host


def from_punycode(host):
    try:
        return host.encode("ascii").decode("idna")
    except UnicodeError:
        return host


class Website(models.Model):
    _name = "website"
    _inherit = ["mixin.credential.holder"]
    _description = "Website"
    _order = "sequence, id"
    _credential_holder_field = "website_credential_id"
    _credential_purpose = "website:settings"
    _CREDENTIAL_FIELDS = {"plausible_shared_key": "plausible_shared_key"}

    def website_domain(self):
        return Domain("website_id", "in", [False, *self.ids])

    def _get_active_lang_ids(self):
        return self.env["res.lang"].search([]).ids

    def _default_language_ids(self):
        return self._get_active_lang_ids()

    def _default_default_lang_id(self):
        lang_code = self.env["ir.default"]._get("res.partner", "lang")
        def_lang_id = self.env["res.lang"]._get_data(code=lang_code).id
        return def_lang_id or self._get_active_lang_ids()[0]

    name = fields.Char(
        string="Website Name",
        required=True,
    )
    sequence = fields.Integer(default=10)
    domain = fields.Char(
        string="Website Domain",
        help="E.g. https://www.mydomain.com",
    )
    domain_punycode = fields.Char(
        string="Punycode Domain",
        compute="_compute_domain_punycode",
        store=False,
        readonly=True,
    )
    company_id = fields.Many2one(
        comodel_name="res.company",
        default=lambda self: self.env.company,
        required=True,
    )
    language_ids = fields.Many2many(
        comodel_name="res.lang",
        relation="website_lang_rel",
        column1="website_id",
        column2="lang_id",
        string="Languages",
        default=_default_language_ids,
        required=True,
    )
    language_count = fields.Count(
        count_of="language_ids",
        string="Number of languages",
    )
    default_lang_id = fields.Many2one(
        comodel_name="res.lang",
        string="Default Language",
        default=_default_default_lang_id,
        required=True,
    )
    auto_redirect_lang = fields.Boolean(
        string="Autoredirect Language",
        default=True,
        help="Should users be redirected to their browser's language",
    )
    cookies_bar = fields.Boolean(
        help="Display a customizable cookies bar on your website."
    )
    configurator_done = fields.Boolean(
        help="True if configurator has been completed or ignored"
    )
    block_third_party_domains = fields.Boolean(
        string="Block 3rd-party domains",
        default=True,
        help="Block 3rd-party domains that may track users (YouTube, Google Maps, etc.).",
    )
    custom_blocked_third_party_domains = fields.Text(
        string="User list of blocked 3rd-party domains",
        translate=False,
        groups="website.group_website_designer",
    )
    blocked_third_party_domains = fields.Text(
        string="List of blocked 3rd-party domains",
        compute="_compute_blocked_third_party_domains",
    )

    def _default_social(self, network):
        return self.env.ref("base.main_company")[f"social_{network}"]

    def _default_logo(self):
        with tools.file_open("website/static/src/img/website_logo.svg", "rb") as f:
            return base64.b64encode(f.read())

    logo = fields.Binary(
        string="Website Logo",
        default=_default_logo,
        help="Display this logo on the website.",
    )
    social_twitter = fields.Char(
        string="X Account",
        default=lambda self: self._default_social("twitter"),
    )
    social_facebook = fields.Char(
        string="Facebook Account",
        default=lambda self: self._default_social("facebook"),
    )
    social_github = fields.Char(
        string="GitHub Account",
        default=lambda self: self._default_social("github"),
    )
    social_linkedin = fields.Char(
        string="LinkedIn Account",
        default=lambda self: self._default_social("linkedin"),
    )
    social_youtube = fields.Char(
        string="Youtube Account",
        default=lambda self: self._default_social("youtube"),
    )
    social_instagram = fields.Char(
        string="Instagram Account",
        default=lambda self: self._default_social("instagram"),
    )
    social_tiktok = fields.Char(
        string="TikTok Account",
        default=lambda self: self._default_social("tiktok"),
    )
    social_discord = fields.Char(
        string="Discord Account",
        default=lambda self: self._default_social("discord"),
    )
    social_default_image = fields.Binary(
        string="Default Social Share Image",
        help="If set, replaces the website logo as the default social share image.",
    )
    has_social_default_image = fields.Boolean(
        compute="_compute_has_social_default_image",
        store=True,
    )

    google_analytics_key = fields.Char()
    google_search_console = fields.Char(
        help="Google key, or Enable to access first reply"
    )

    google_maps_api_key = fields.Char(string="Google Maps API Key")

    plausible_shared_key = fields.Char(
        compute="_compute_credential_doors",
        inverse="_inverse_credential_doors",
        copy=True,
    )
    plausible_shared_key_set = fields.Boolean(
        copy=True,
        readonly=True,
    )
    plausible_site = fields.Char()
    website_credential_id = fields.Many2one(
        comodel_name="credential.credential",
        string="Credential",
        copy=False,
        ondelete="restrict",
        groups="base.group_system",
        help="Holds this website's integration secrets.",
    )

    user_id = fields.Many2one(
        comodel_name="res.users",
        string="Public User",
        required=True,
    )
    cdn_activated = fields.Boolean(string="Content Delivery Network (CDN)")
    cdn_url = fields.Char(
        string="CDN Base URL",
        default="",
    )
    cdn_filters = fields.Text(
        string="CDN Filters",
        default=lambda s: "\n".join(DEFAULT_CDN_FILTERS),
        help="URL matching those filters will be rewritten using the CDN Base URL",
    )
    partner_id = fields.Many2one(
        related="user_id.partner_id",
        string="Public Partner",
        readonly=False,
    )
    menu_id = fields.Many2one(
        comodel_name="website.menu",
        string="Main Menu",
        compute="_compute_menu_id",
    )
    homepage_url = fields.Char(help="E.g. /contactus or /shop")
    custom_code_head = fields.Html(
        string="Custom <head> code",
        sanitize=False,
    )
    custom_code_footer = fields.Html(
        string="Custom end of <body> code",
        sanitize=False,
    )

    robots_txt = fields.Html(
        string="Robots.txt",
        translate=False,
        sanitize=False,
        groups="website.group_website_designer",
    )

    def _default_favicon(self):
        with tools.file_open("web/static/img/favicon.ico", "rb") as f:
            return base64.b64encode(f.read())

    favicon = fields.Binary(
        string="Website Favicon",
        default=_default_favicon,
        help="This field holds the image used to display a favicon on the website.",
    )
    theme_id = fields.Many2one(
        comodel_name="ir.module.module",
        help="Installed theme",
    )

    specific_user_account = fields.Boolean(
        help="If True, new accounts will be associated to the current website"
    )
    auth_signup_uninvited = fields.Selection(
        selection=[
            ("b2b", "On invitation"),
            ("b2c", "Free sign up"),
        ],
        string="Customer Account",
        default="b2b",
    )

    _domain_unique = models.Constraint(
        "unique(domain)",
        "Website Domain should be unique.",
    )

    @api.onchange("language_ids")
    def _onchange_language_ids(self):
        language_ids = self.language_ids._origin
        if language_ids and self.default_lang_id not in language_ids:
            self.default_lang_id = language_ids[0]

    @api.depends("domain")
    def _compute_domain_punycode(self):
        for website in self:
            website_domain = website.domain or ""
            parsed = urlparse(website_domain)
            hostname = parsed.hostname or ""
            if hostname:
                netloc = parsed.netloc.replace(hostname, to_punycode(hostname), 1)
                website.domain_punycode = urlunparse(parsed._replace(netloc=netloc))
            else:
                website.domain_punycode = website_domain

    @api.depends("social_default_image")
    def _compute_has_social_default_image(self):
        for website in self:
            website.has_social_default_image = bool(website.social_default_image)

    def _compute_menu_id(self):
        all_menus = self.env["website.menu"].search_fetch(
            Domain("website_id", "in", self.ids)
        )

        for website in self:
            menus = all_menus.filtered(
                lambda m, website=website: m.website_id == website
            )

            children = dict.fromkeys(menus, ())
            for menu in menus:
                if menu.parent_id and menu.parent_id in menus:
                    children[menu.parent_id] += (menu.id,)
            for menu, child_items in children.items():
                menu._fields["child_id"]._update_cache(menu, child_items)

            menus.mapped("is_visible")

            top_menus = menus.filtered(lambda m: not m.parent_id)
            website.menu_id = top_menus[:1].id

    @api.depends("custom_blocked_third_party_domains")
    def _compute_blocked_third_party_domains(self):
        for website in self:
            custom_list = website.sudo().custom_blocked_third_party_domains

            full_list = DEFAULT_BLOCKED_THIRD_PARTY_DOMAINS
            if custom_list:
                lines = custom_list.splitlines()
                custom_domains = "\n".join(
                    line for line in lines if line and line[0] != "#"
                )
                if lines and lines[0].startswith("#ignore_default"):
                    full_list = custom_domains
                else:
                    full_list += f"\n{custom_domains}"

            website.blocked_third_party_domains = full_list

    @tools.ormcache("self.id", cache="templates")
    def _get_blocked_third_party_domains_tuple(self):
        # Split once per website rather than once per rendered element: qweb
        # calls _post_processing_att for every element it compiles, and for
        # every element carrying a dynamic attribute on every render, and the
        # default blocklist is ~200 lines. Cached in the "templates" group,
        # which `write` already clears for `custom_blocked_third_party_domains`
        # (TEMPLATE_AFFECTING_FIELDS). Cached as a tuple: an ormcache must not
        # hand out a mutable object for a caller to mutate in place.
        return tuple(
            domain
            for line in (self.blocked_third_party_domains or "").split("\n")
            if (domain := line.strip().lower())
        )

    def _get_blocked_third_party_domains_list(self):
        return list(self._get_blocked_third_party_domains_tuple())

    _BLOCKED_IFRAME_CONTAINER_CLASSES = frozenset(
        {
            "s_map",
            "s_instagram_page",
            "o_facebook_page",
            "o_background_video",
            "media_iframe_video",
        }
    )

    def _get_blocked_iframe_containers_classes(self):
        return self._BLOCKED_IFRAME_CONTAINER_CLASSES

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            self._update_vals(vals)

            if "user_id" not in vals:
                company = (
                    self.env["res.company"].browse(vals.get("company_id"))
                    or self.env.company
                )
                vals["user_id"] = company._get_public_user().id

        websites = super().create(vals_list)
        _debug.lifecycle("create", websites=websites, count=len(websites))
        self.env.registry.clear_cache()
        websites.company_id._compute_website_id()
        for website in websites:
            website._bootstrap_homepage()

        if (
            not self.env.user.has_group("website.group_multi_website")
            and self.search_count([]) > 1
        ):
            all_user_groups = "base.group_portal,base.group_user,base.group_public"
            groups = self.env["res.groups"].concat(
                *(self.env.ref(it) for it in all_user_groups.split(","))
            )
            _debug.lifecycle("multi_website_group_implied", groups=groups)
            groups.write(
                {"implied_ids": [(4, self.env.ref("website.group_multi_website").id)]}
            )

        return websites

    def write(self, vals):
        public_user_to_change_websites = self.env["website"]
        original_company = self.company_id
        values = vals
        self._update_vals(values)

        _debug.lifecycle("write", websites=self, count=len(self), fields=sorted(values))
        self.env.registry.clear_cache()

        if "company_id" in values and "user_id" not in values:
            public_user_to_change_websites = self.filtered(
                lambda w: w.sudo().user_id.company_id.id != values["company_id"]
            )
            if public_user_to_change_websites:
                company = self.env["res.company"].browse(values["company_id"])
                _debug.lifecycle(
                    "public_user_moved",
                    websites=public_user_to_change_websites,
                    company=values["company_id"],
                )
                super(Website, public_user_to_change_websites).write(
                    dict(values, user_id=company and company._get_public_user().id)
                )

        result = super(Website, self - public_user_to_change_websites).write(values)

        if not TEMPLATE_AFFECTING_FIELDS.isdisjoint(values):
            _debug.lifecycle(
                "templates_cache_cleared",
                by=sorted(TEMPLATE_AFFECTING_FIELDS.intersection(values)),
            )
            self.env.registry.clear_cache("templates")

        if "sequence" in values or "company_id" in values:
            (original_company | self.company_id)._compute_website_id()

        if "cookies_bar" in values:
            policy_pages_by_website = (
                self.env["website.page"]
                .search(
                    [
                        ("website_id", "in", self.ids),
                        ("url", "=", "/cookie-policy"),
                    ]
                )
                .grouped("website_id")
            )
            for website in self:
                existing_policy_page = policy_pages_by_website.get(
                    website, self.env["website.page"]
                )
                if not values["cookies_bar"]:
                    _debug.lifecycle(
                        "cookie_policy_page_removed",
                        website=website.id,
                        pages=existing_policy_page,
                    )
                    existing_policy_page.unlink()
                elif not existing_policy_page:
                    cookies_view = self.env.ref(
                        "website.cookie_policy", raise_if_not_found=False
                    )
                    if cookies_view:
                        cookies_view.with_context(website_id=website.id).write(
                            {"website_id": website.id}
                        )
                        specific_cook_view = website.with_context(
                            website_id=website.id
                        ).viewref("website.cookie_policy")
                        _debug.lifecycle(
                            "cookie_policy_page_created", website=website.id
                        )
                        self.env["website.page"].create(
                            {
                                "is_published": True,
                                "website_indexed": False,
                                "url": "/cookie-policy",
                                "website_id": website.id,
                                "view_id": specific_cook_view.id,
                            }
                        )

        return result

    @api.model
    def _update_vals(self, vals):
        if "plausible_shared_key" in vals:
            vals["plausible_shared_key_set"] = bool(vals["plausible_shared_key"])
        self._update_vals_favicon(vals)
        self._update_vals_domain(vals)
        self._update_vals_homepage_url(vals)

    @api.model
    def _update_vals_favicon(self, vals):
        if vals.get("favicon"):
            vals["favicon"] = base64.b64encode(
                image_process(
                    base64.b64decode(vals["favicon"]),
                    size=(256, 256),
                    crop="center",
                    output_format="ICO",
                )
            )

    @api.model
    def _update_vals_domain(self, vals):
        if vals.get("domain"):
            vals["domain"] = self._normalize_domain_url(vals["domain"])

    def _normalize_domain_url(self, url):
        normalized_url = url
        if not normalized_url.startswith(("http://", "https://")):
            normalized_url = "https://%s" % normalized_url
        return normalized_url.rstrip("/")

    @api.model
    def _update_vals_homepage_url(self, vals):
        homepage_url = vals.get("homepage_url")
        if homepage_url:
            vals["homepage_url"] = homepage_url.rstrip("/")

    @api.constrains("domain")
    def _check_domain(self):
        for record in self:
            if not record.domain:
                continue

            try:
                parsed = urlparse(record.domain)
            except ValueError:
                raise ValidationError(
                    _("The provided website domain is not a valid URL.")
                ) from None

            if contains_dot_segments(parsed.path):
                _debug.logic("domain_refused", reason="dot_segments", website=record.id)
                raise ValidationError(
                    _(
                        "The domain path cannot contain relative path segments like '/./' or '/../'."
                    )
                )

    @api.constrains("cdn_filters")
    def _check_cdn_filters(self):
        for website in self.filtered("cdn_filters"):
            for line in website.cdn_filters.splitlines():
                if not line:
                    continue
                try:
                    re.compile(line)
                except re.error as e:
                    _debug.logic("cdn_filter_refused", website=website.id, filter=line)
                    raise ValidationError(
                        _(
                            "The CDN filter %(filter)s is not a valid regular expression: %(error)s",
                            filter=line,
                            error=e,
                        )
                    ) from None

    @api.constrains("homepage_url")
    def _check_homepage_url(self):
        for website in self.filtered("homepage_url"):
            if not website.homepage_url.startswith("/"):
                _debug.logic(
                    "homepage_url_refused",
                    reason="not_relative",
                    website=website.id,
                )
                raise ValidationError(
                    _("The homepage URL should be relative and start with '/'.")
                )

    @api.ondelete(at_uninstall=False)
    def _unlink_except_default_website(self):
        default_website = self.env.ref(
            "website.default_website", raise_if_not_found=False
        )
        if default_website and default_website in self:
            _debug.logic("unlink_refused", reason="default_website")
            raise UserError(
                _(
                    "You cannot delete default website %s. Try to change its settings instead",
                    default_website.name,
                )
            )

    def unlink(self):
        _debug.lifecycle("unlink", websites=self, count=len(self))
        self._remove_attachments_on_website_unlink()

        self.env["website.page"].search([("website_id", "in", self.ids)]).unlink()
        self.env["ir.ui.view"].search([("website_id", "in", self.ids)]).unlink()
        self.env["website.menu"].search([("website_id", "in", self.ids)]).unlink()

        companies = self.company_id
        res = super().unlink()
        self.env.registry.clear_cache()
        companies._compute_website_id()
        return res

    def _remove_attachments_on_website_unlink(self):
        attachments_to_unlink = self.env["ir.attachment"].search(
            [
                ("website_id", "in", self.ids),
                "|",
                "|",
                ("key", "!=", False),
                ("url", "=like", "/_custom/%"),
                ("url", "ilike", ".assets\\_"),
            ]
        )
        _debug.lifecycle(
            "website_attachments_removed",
            websites=self,
            attachments=len(attachments_to_unlink),
        )
        attachments_to_unlink.unlink()

    def _idna_url(self, url):
        return get_base_hostname(url.lower(), True).encode("idna").decode("ascii")

    def _is_indexable_url(self, url):
        return self._idna_url(url) == self._idna_url(self.domain)

    def _bootstrap_homepage(self):
        Page = self.env["website.page"]
        standard_homepage = self.env.ref("website.homepage", raise_if_not_found=False)
        if not standard_homepage:
            _debug.logic("bootstrap_homepage_skipped", reason="no_standard_homepage")
            return

        new_homepage_view = """<t name="Homepage" t-name="website.homepage">
    <t t-call="website.layout" pageName.f="homepage">
        <div id="wrap" class="oe_structure oe_empty"/>
    </t>
</t>"""
        standard_homepage.with_context(website_id=self.id).arch_db = new_homepage_view

        homepage_page = Page.search(
            [
                ("website_id", "=", self.id),
                ("key", "=", standard_homepage.key),
            ],
            limit=1,
        )
        if not homepage_page:
            homepage_page = Page.create(
                {
                    "website_published": True,
                    "url": "/",
                    "view_id": self.with_context(website_id=self.id)
                    .viewref("website.homepage")
                    .id,
                }
            )
        homepage_page.url = "/"

        default_menu = self.env.ref("website.main_menu")
        self.copy_menu_hierarchy(default_menu)
        home_menu = self.env["website.menu"].search(
            [("website_id", "=", self.id), ("url", "=", "/")]
        )
        home_menu.page_id = homepage_page
        _debug.lifecycle(
            "homepage_bootstrapped",
            website=self.id,
            page=homepage_page.id,
            menu=home_menu.id,
        )

    def copy_menu_hierarchy(self, top_menu):
        def copy_menu(menu, t_menu):
            new_menu = menu.copy(
                {
                    "parent_id": t_menu.id,
                    "website_id": self.id,
                }
            )
            for submenu in menu.child_id:
                copy_menu(submenu, new_menu)

        for website in self:
            new_top_menu = top_menu.copy(
                {
                    "name": _("Top Menu for Website %s", website.id),
                    "website_id": website.id,
                }
            )
            for submenu in top_menu.child_id:
                copy_menu(submenu, new_top_menu)
            _debug.lifecycle(
                "menu_hierarchy_copied",
                website=website.id,
                source=top_menu.id,
                top_menu=new_top_menu.id,
            )

    @api.model
    def new_page(
        self,
        name=False,
        add_menu=False,
        template="website.default_page",
        ispage=True,
        namespace=None,
        page_values=None,
        menu_values=None,
        sections_arch=None,
        page_title=None,
    ):
        template_record = self.env.ref(template, raise_if_not_found=False)
        if not template_record:
            _debug.logic(
                "new_page_refused", reason="unknown_template", template=template
            )
            raise UserError(_("'%s' is not a valid template reference.", template))
        if namespace:
            template_module = namespace
        else:
            template_module = template.partition(".")[0]
        page_url = "/" + self.env["ir.http"]._slugify(name, max_length=1024, path=True)
        page_url = self.get_unique_path(page_url)
        page_key = self.env["ir.http"]._slugify(name)
        result = {"url": page_url}

        if not name:
            name = "Home"
            page_key = "home"

        arch = template_record.arch
        if sections_arch:
            tree = html.fromstring(arch)
            wrap = tree.xpath('//div[@id="wrap"]')[0]
            for section in html.fromstring(f"<wrap>{sections_arch}</wrap>"):
                wrap.append(section)
            arch = etree.tostring(tree, encoding="unicode")
        website_id = self.env.context.get("website_id")
        key = self.get_unique_key(page_key, template_module)
        view = template_record.copy({"website_id": website_id, "key": key})

        view.with_context(lang=None).write(
            {
                "arch": arch.replace(template, key),
                "name": page_title or name,
            }
        )
        result["view_id"] = view.id

        if view.arch_fs:
            view.arch_fs = False

        website = self.get_current_website()
        if ispage:
            default_page_values = {
                "url": page_url,
                "website_id": website.id,
                "view_id": view.id,
                "track": True,
            }
            if page_values:
                default_page_values.update(page_values)
            page = self.env["website.page"].create(default_page_values)
            result["page_id"] = page.id
        if add_menu:
            menu = self.env["website.menu"].search(
                [
                    ("url", "=", page_url),
                    ("website_id", "=", website.id),
                ],
                limit=1,
            )
            if not menu:
                default_menu_values = {
                    "name": name,
                    "url": page_url,
                    "parent_id": website.menu_id.id,
                    "page_id": page.id if ispage else False,
                    "website_id": website.id,
                }
                if menu_values:
                    default_menu_values.update(menu_values)
                menu = self.env["website.menu"].create(default_menu_values)
            result["menu_id"] = menu.id
        _debug.lifecycle("new_page", url=page_url, key=key, keys=sorted(result))
        return result

    def get_unique_path(self, page_url):
        inc = 0
        website_id = (
            self.env.context.get("website_id", False) or self.get_current_website().id
        )
        domain_static = [("website_id", "=", website_id)]
        page_temp = page_url
        while (
            self.env["website.page"]
            .with_context(active_test=False)
            .sudo()
            .search([("url", "=", page_temp)] + domain_static)
        ):
            inc += 1
            page_temp = page_url + ((inc and "-%s" % inc) or "")
        if _debug.logic.enabled and inc:
            _debug.logic("page_url_deduplicated", wanted=page_url, used=page_temp)
        return page_temp

    def _get_plausible_script_url(self):
        return (
            self.env["ir.config_parameter"]
            .sudo()
            .get_param(
                "website.plausible_script", "https://plausible.io/js/plausible.js"
            )
        )

    def _get_plausible_server(self):
        return (
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("website.plausible_server", "https://plausible.io")
        )

    def _get_plausible_share_url(self):
        embed_url = f"/share/{self.plausible_site}?auth={self.plausible_shared_key}&embed=true&theme=system"
        return (
            self.plausible_shared_key
            and tools.urls.urljoin(self._get_plausible_server(), embed_url)
        ) or ""

    def get_unique_key(self, string, template_module=False):
        if template_module:
            string = template_module + "." + string
        elif not string.startswith("website."):
            string = "website." + string

        key_copy = string
        inc = 0
        website_id = self.env.context.get("website_id", False)
        if website_id:
            domain_static = Domain("website_id", "in", (False, website_id))
        else:
            domain_static = self.get_current_website().website_domain()
        while (
            self.env["ir.ui.view"]
            .with_context(active_test=False)
            .sudo()
            .search(Domain("key", "=", key_copy) & domain_static)
        ):
            inc += 1
            key_copy = string + ((inc and "-%s" % inc) or "")
        if _debug.logic.enabled and inc:
            _debug.logic("view_key_deduplicated", wanted=string, used=key_copy)
        return key_copy

    @api.model
    def search_url_dependencies(self, res_model, res_ids):
        dependencies = {}
        current_website = self.get_current_website()
        page_model_name = "Page"

        def _handle_views_and_pages(views):
            page_views = views.filtered("page_ids")
            views -= page_views
            if page_views:
                dependencies.setdefault(page_model_name, [])
                dependencies[page_model_name] += [
                    {
                        "field_name": "Content",
                        "record_name": page.name,
                        "link": page.url,
                        "model_name": page_model_name,
                    }
                    for page in page_views.page_ids
                ]
            return views

        search_criteria = []
        for record in self.env[res_model].browse([int(res_id) for res_id in res_ids]):
            website = ("website_id" in record and record.website_id) or current_website
            url = ("website_url" in record and record.website_url) or record.url
            search_criteria.append((url, website.website_domain()))

        for model_name, field_name in self._get_fields_html():
            Model = self.env[model_name]
            if not Model.has_access("read"):
                _debug.logic("dependency_model_skipped", model=model_name)
                continue

            domains = []
            for url, website_domain in search_criteria:
                domains.append(
                    Domain.AND(
                        [
                            [(field_name, "ilike", escape_psql(url))],
                            website_domain if hasattr(Model, "website_id") else [],
                        ]
                    )
                )

            dependency_records = Model.search(Domain.OR(domains))  # noqa: E8507 - one query per dependent model, over every url at once
            if model_name == "ir.ui.view":
                dependency_records = _handle_views_and_pages(dependency_records)
            if dependency_records:
                model_label = self.env["ir.model"]._display_name_for([model_name])[0][
                    "display_name"
                ]
                field_string = Model.fields_get([field_name])[field_name]["string"]
                dependencies.setdefault(model_label, [])
                dependencies[model_label] += [
                    {
                        "field_name": field_string,
                        "record_name": rec.display_name,
                        "link": ("website_url" in rec and rec.website_url)
                        or f"/odoo/{model_name}/{rec.id}",
                        "model_name": model_label,
                    }
                    for rec in dependency_records
                ]

        _debug.pipeline(
            "url_dependencies",
            model=res_model,
            urls=len(search_criteria),
            groups=len(dependencies),
        )
        return dependencies

    @api.model
    def get_current_website(self, fallback=True):
        is_frontend_request = request and getattr(request, "is_frontend", False)
        if request and request.session.get("force_website_id"):
            forced_id = request.session["force_website_id"]
            if self._is_website_live(forced_id):
                _debug.logic("current_website", by="session_force", website=forced_id)
                return self.browse(forced_id)
            _debug.logic("forced_website_dropped", reason="gone", website=forced_id)
            request.session.pop("force_website_id")

        website_id = self.env.context.get("website_id")
        if website_id and self._is_website_live(website_id):
            _debug.logic("current_website", by="context", website=website_id)
            return self.browse(website_id)

        if not is_frontend_request and not fallback:
            return self.browse(False)

        domain_name = (
            (request and request.httprequest.host)
            or (
                hasattr(threading.current_thread(), "url")
                and threading.current_thread().url
            )
            or ""
        )
        website_id = self.sudo()._get_current_website_id(domain_name, fallback=fallback)
        _debug.logic(
            "current_website", by="domain", host=domain_name, website=website_id
        )
        return self.browse(website_id)

    @api.model
    @tools.ormcache("website_id")
    def _is_website_live(self, website_id):
        return bool(self.browse(website_id).exists())

    @api.model
    @tools.ormcache("domain_name", "fallback")
    def _get_current_website_id(self, domain_name, fallback=True):
        def remove_port(domain_name):
            return (domain_name or "").split(":")[0]

        def is_domain_matching(website, domain_name, ignore_port=False):
            website_domain = get_base_hostname(website.domain_punycode)
            if ignore_port:
                website_domain = remove_port(website_domain)
                domain_name = remove_port(domain_name)
            return website_domain.lower() == (domain_name or "").lower()

        domain_name = to_punycode(domain_name or "")
        domain_name_idna = from_punycode(domain_name)

        found_websites = self.search(
            [
                "|",
                ("domain", "ilike", escape_psql(remove_port(domain_name))),
                ("domain", "ilike", escape_psql(remove_port(domain_name_idna))),
            ]
        )
        websites = found_websites.filtered(lambda w: is_domain_matching(w, domain_name))
        websites = websites or found_websites.filtered(
            lambda w: is_domain_matching(w, domain_name, ignore_port=True)
        )

        if not websites:
            if not fallback:
                _debug.logic("website_by_domain", verdict="no_match", host=domain_name)
                return False
            _debug.logic(
                "website_by_domain", verdict="fallback_first", host=domain_name
            )
            return self.search([], limit=1).id

        _debug.logic(
            "website_by_domain",
            verdict="matched",
            host=domain_name,
            website=websites[0].id,
            candidates=len(found_websites),
        )
        return websites[0].id

    def _force(self):
        self._force_website(self.id)

    def _force_website(self, website_id):
        if request:
            _debug.lifecycle("website_forced", website=website_id)
            request.session["force_website_id"] = (
                website_id and str(website_id).isdigit() and int(website_id)
            )

    @api.model
    def is_public_user(self):
        return request.env.user.id == request.website._get_cached("user_id")

    @api.model
    def viewref(self, view_id, raise_if_not_found=True):
        if not isinstance(view_id, (int, str)):
            raise ValueError(
                "Expecting a string or an integer, not a %s." % (type(view_id))
            )

        return (
            self.env["ir.ui.view"]
            .sudo()
            .with_context(active_test=False)
            ._get_template_view(view_id, raise_if_not_found=raise_if_not_found)
        )

    @api.model
    def is_view_active(self, key):
        return (
            self.env["ir.ui.view"]
            .with_context(active_test=False)
            ._get_cached_template_info(key)
            .get("active")
        )

    @api.model
    def get_template(self, template):
        if isinstance(template, str) and "." not in template:
            template = "website.%s" % template
        return self.env["ir.ui.view"]._get_template_view(template).sudo()

    @api.model
    def pager(self, url, total, page=1, step=30, scope=5, url_args=None):
        return pager(url, total, page=page, step=step, scope=scope, url_args=url_args)

    def is_rule_enumerable(self, rule):
        endpoint = rule.endpoint
        methods = endpoint.routing.get("methods") or ["GET"]

        converters = list(rule._converters.values())
        if not (
            "GET" in methods
            and endpoint.routing["type"] == "http"
            and endpoint.routing["auth"] in ("none", "public")
            and endpoint.routing.get("website", False)
            and all(hasattr(converter, "generate") for converter in converters)
        ):
            return False

        sign = inspect.signature(endpoint.original_endpoint)
        params = list(sign.parameters.values())[1:]
        supported_kinds = (
            inspect.Parameter.POSITIONAL_ONLY,
            inspect.Parameter.POSITIONAL_OR_KEYWORD,
        )

        return all(
            p.name in rule._converters
            for p in params
            if p.kind in supported_kinds and p.default is inspect.Parameter.empty
        )

    def _enumerate_pages(self, query_string=None, force=False):
        domain = [("view_id", "!=", False), ("url", "!=", "/")]
        if not force:
            domain += [
                ("website_indexed", "=", True),
                ("website_published", "=", True),
                ("visibility", "=", False),
                "|",
                ("date_publish", "=", False),
                ("date_publish", "<=", fields.Datetime.now()),
            ]

        if query_string:
            domain += [("url", "like", query_string)]

        pages = self._get_website_pages(domain)

        for page in pages:
            record = {"loc": page["url"], "id": page["id"], "name": page["name"]}
            if page.view_id.priority != 16:
                record["priority"] = min(round(page.view_id.priority / 32.0, 1), 1)
            last_dates = [d for d in (page.write_date, page.view_write_date) if d]
            if last_dates:
                record["lastmod"] = max(last_dates).date()
            yield record

        router = self.env["ir.http"].routing_map()
        url_set = set()

        sitemap_endpoint_done = set()
        _debug.pipeline(
            "enumerate_pages",
            website=self.id,
            pages=len(pages),
            query=query_string or None,
            force=force,
        )

        for rule in router.iter_rules():
            sitemap_func = rule.endpoint.routing.get("sitemap")
            if sitemap_func is False:
                continue

            if callable(sitemap_func):
                func_key = get_underlying_function(sitemap_func)
                if func_key in sitemap_endpoint_done:
                    continue
                sitemap_endpoint_done.add(func_key)
                for loc in sitemap_func(
                    self.with_context(lang=self.default_lang_id.code).env,
                    rule,
                    query_string,
                ):
                    loc_norm = {**loc, "loc": normalize_sitemap_url(loc["loc"])}
                    url = loc_norm["loc"]
                    if url not in url_set:
                        yield loc_norm
                        url_set.add(url)
                continue

            if not self.is_rule_enumerable(rule):
                continue

            if "sitemap" not in rule.endpoint.routing:
                logger.warning(
                    "No Sitemap value provided for controller %s (%s)",
                    rule.endpoint.original_endpoint,
                    ",".join(rule.endpoint.routing["routes"]),
                )

            converters = rule._converters or {}
            if (
                query_string
                and not converters
                and (query_string not in rule.build({}, append_unknown=False)[1])
            ):
                continue

            values = [{}]
            convitems = sorted(
                converters.items(),
                key=lambda x: (
                    hasattr(x[1], "domain") and (x[1].domain != "[]"),
                    rule._trace.index((True, x[0])),
                ),
            )

            for i, (name, converter) in enumerate(convitems):
                website_domain = None
                if "website_id" in self.env[converter.model]._fields and (
                    not converter.domain or converter.domain == "[]"
                ):
                    website_domain = (
                        "[('website_id', 'in', (False, current_website_id))]"
                    )

                newval = []
                for val in values:
                    query = i == len(convitems) - 1 and query_string
                    if query:
                        r = "".join([x[1] for x in rule._trace[1:] if not x[0]])
                        query = sitemap_qs2dom(
                            query, r, self.env[converter.model]._rec_name
                        )
                        if query.is_false():
                            continue

                    for rec in converter.generate(
                        self.env, args=val, dom=query, domain=website_domain
                    ):
                        newval.append(val.copy())
                        newval[-1].update(
                            {name: rec.with_context(lang=self.default_lang_id.code)}
                        )
                values = newval

            for value in values:
                _domain_part, url = rule.build(value, append_unknown=False)
                url = normalize_sitemap_url(url)
                pattern = query_string and "*%s*" % "*".join(query_string.split("/"))
                if not query_string or fnmatch.fnmatch(url.lower(), pattern):
                    page = {"loc": url}
                    if url in url_set:
                        continue
                    url_set.add(url)

                    yield page

    def get_website_page_ids(self):
        if not self.env.user.has_group("website.group_website_restricted_editor"):
            _debug.logic(
                "page_ids_refused", reason="not_restricted_editor", user=self.env.uid
            )
            raise AccessError(_("Access Denied"))

        domain = Domain("url", "!=", False)
        pages_sudo = self.env["website.page"].sudo()

        if not self or not self.exists():
            pages = pages_sudo.search(domain)
            return {None: pages.ids}

        pages_by_website = {}
        for website in self:
            website_domain = Domain.AND((domain, website.website_domain()))
            pages = pages_sudo.search(website_domain)
            pages_for_website = pages.with_context(
                website_id=website.id
            )._get_most_specific_pages()
            pages_by_website[website.id] = pages_for_website.ids

        return pages_by_website

    def _get_website_pages(self, domain=None, order="name", limit=None):
        website = self.get_current_website()
        domain = Domain(domain or Domain.TRUE) & website.website_domain()
        # The limit is applied AFTER the shadowed generics are dropped. Applied
        # in SQL it cut the rows the dedup was about to choose between, so a url
        # carrying both a generic page and this website's override could lose
        # both: `_get_website_pages([("url", "=", u)], limit=1)` answered with
        # nothing for a url that serves, and `is_page_existing(u)` said False.
        with _debug.perf("website_pages", cr=self.env.cr, website=website.id) as span:
            pages = self.env["website.page"].sudo().search(domain, order=order)
            span.set(found=len(pages))
        pages = pages.with_context(website_id=website.id)._get_most_specific_pages()
        return pages[:limit] if limit else pages

    def search_pages(self, needle=None, limit=None):
        name = self.env["ir.http"]._slugify(needle, max_length=50, path=True)
        res = []
        for page in self._enumerate_pages(query_string=name, force=True):
            res.append(page)
            if len(res) == limit:
                break
        return res

    def is_page_existing(self, page):
        if (
            len(
                self._get_website_pages(
                    domain=[("url", "=", page), ("view_id", "!=", False)], limit=1
                )
            )
            > 0
        ):
            return True

        redirects_domain = self.get_current_website().website_domain() & Domain(
            [("url_from", "=", page), ("redirect_type", "in", ("301", "302"))]
        )
        if len(self.env["website.rewrite"].search(redirects_domain, limit=1)) > 0:
            return True

        router = (
            request.env["ir.http"]
            .routing_map()
            .bind_to_environ(request.httprequest.environ)
        )
        if not router.test(path_info=page, method="GET"):
            _debug.logic("page_existing", verdict="no_route", page=page)
            return False

        try:
            rule, args = router.match(page, method="GET", return_rule=True)
        except werkzeug.routing.RequestRedirect:
            _debug.logic("page_existing", verdict="route_redirect", page=page)
            return True

        try:
            for arg in args:
                if isinstance(args[arg], models.BaseModel):
                    args[arg] = args[arg].with_user(self.env.uid)
                    if (
                        hasattr(args[arg], "website_id")
                        and args[arg].website_id
                        and args[arg].website_id != self
                    ):
                        _debug.logic(
                            "page_existing", verdict="other_website", page=page
                        )
                        return False
            rule.build(args, append_unknown=False)
        except MissingError:
            _debug.logic("page_existing", verdict="missing_record", page=page)
            return False
        _debug.logic("page_existing", verdict="route", page=page)
        return True

    def get_suggested_controllers(self):
        return [
            (_("Homepage"), self.env["ir.http"]._url_for("/"), "website"),
            (
                _("Contact Us"),
                self.env["ir.http"]._url_for("/contactus"),
                "website_crm",
            ),
        ]

    @api.model
    def image_url(self, record, field, size=None):
        sudo_record = record.sudo()
        sha = hashlib.sha512(str(sudo_record.write_date).encode("utf-8")).hexdigest()[
            :7
        ]
        size = "" if size is None else "/%s" % size
        return "/web/image/%s/%s/%s%s?unique=%s" % (
            record._name,
            record.id,
            field,
            size,
            sha,
        )

    def get_cdn_url(self, uri):
        self.check_singleton()
        if not uri:
            return ""
        cdn_url = self.cdn_url
        cdn_filters = (self.cdn_filters or "").splitlines()
        for flt in cdn_filters:
            if flt and re.match(flt, uri):
                _debug.logic("cdn_url", uri=uri, filter=flt, cdn=cdn_url)
                return tools.urls.urljoin(cdn_url, uri)
        return uri

    @api.model
    def action_dashboard_redirect(self):
        if self.env.user.has_group("base.group_system") or self.env.user.has_group(
            "website.group_website_designer"
        ):
            return self.env["ir.actions.actions"]._get_action_dict_by_xml_id(
                "website.backend_dashboard"
            )
        _debug.logic("dashboard_refused", user=self.env.uid)
        raise AccessError(
            _("You don't have the necessary access rights to access this dashboard.")
        )

    def get_client_action_url(self, url, mode_edit=False, mode_debug=0):
        action_params = {
            "path": url,
        }
        if mode_edit:
            action_params["enable_editor"] = 1
        if mode_debug:
            action_params["debug"] = mode_debug
        return "/odoo/action-website.website_preview?" + urlencode(action_params)

    def get_client_action(self, url, mode_edit=False, website_id=False):
        action = self.env["ir.actions.actions"]._get_action_dict_by_xml_id(
            "website.website_preview"
        )
        action["params"] = {
            "path": url,
            "enable_editor": mode_edit,
            "website_id": website_id,
        }
        return action

    def button_go_website(self, path="/"):
        self._force()
        return self.get_client_action(path)

    def _get_canonical_url(self):
        self.check_singleton()
        return self.env["ir.http"]._url_localized(
            lang_code=request.lang.code, canonical_domain=self.get_base_url()
        )

    def _is_canonical_url(self):
        self.check_singleton()
        current_url = (
            request.httprequest.url_root[:-1]
            + request.httprequest.environ["REQUEST_URI"]
        )
        canonical_url = self._get_canonical_url()
        return current_url == canonical_url

    @tools.ormcache("self.id")
    def _get_cached_values(self):
        self.check_singleton()

        _debug.perf.count("cached_values_computed", website=self.id)
        self.fetch(
            ["user_id", "company_id", "default_lang_id", "homepage_url", "cookies_bar"]
        )
        return {
            "user_id": self.user_id.id,
            "company_id": self.company_id.id,
            "default_lang_id": self.default_lang_id.id,
            "homepage_url": self.homepage_url,
            "cookies_bar": self.cookies_bar,
        }

    def _get_cached(self, field):
        return self._get_cached_values()[field]

    def _get_fields_html_blacklist(self):
        return (
            "mail.message",
            "mail.activity",
            "digest.tip",
        )

    def _get_fields_html(self):
        html_fields = [("ir.ui.view", "arch_db")]
        cr = self.env.cr
        cr.execute(
            """
            SELECT f.model,
                   f.name
              FROM ir_model_fields f
              JOIN ir_model m
                ON m.id = f.model_id
             WHERE f.ttype = 'html'
               AND f.store = true
               AND m.transient = false
               AND f.model NOT LIKE 'ir.actions%%'
               AND f.model != ALL(%s)
        """,
            ([list(self._get_fields_html_blacklist())]),
        )
        for (
            model_name,
            field_name,
        ) in cr.fetchall():
            try:
                model = self.env[model_name]
                field = model._fields[field_name]
                if model._abstract or model._table_query or not field.store:
                    continue
            except KeyError:
                continue

            html_fields.append((model_name, field_name))
        _debug.perf.count("html_fields_computed", fields=len(html_fields))
        return html_fields

    def _get_snippet_occurrences(self, snippet_ids, html_fields):
        """Every stored element carrying one of `snippet_ids`, grouped by id.

        One scan for all of them. This used to be one `UNION` over every stored
        html field of every model *per snippet asset*, and the SQL depends only
        on the snippet id -- so a snippet with three versions in two flavours
        re-ran the identical scan six times. On a stock install that was 82
        scans over 22 fields, 1,804 `regexp_matches` branches, to answer a
        question that fits in one query.
        """
        occurrences = {snippet_id: [] for snippet_id in snippet_ids}
        if not snippet_ids or not html_fields:
            return occurrences
        models_and_fields = [
            (self.env[model_name], field_name) for model_name, field_name in html_fields
        ]
        alternation = "|".join(
            re.escape(snippet_id) for snippet_id in sorted(snippet_ids)
        )
        pattern = f'<([^>]*data-snippet="(?:{alternation})"[^>]*)>'
        rows = self.env.execute_query(
            SQL(" UNION ").join(
                SQL(
                    "SELECT regexp_matches(%s, %s, 'g') FROM %s",
                    model._field_to_sql(model._table, field_name),
                    pattern,
                    SQL.identifier(model._table),
                )
                for model, field_name in models_and_fields
            )
        )
        carried = re.compile(r'data-snippet="([^"]*)"')
        for (match,) in rows:
            element = match[0]
            found = carried.search(element)
            if found and found.group(1) in occurrences:
                occurrences[found.group(1)].append(element)
        _debug.perf.count(
            "snippet_occurrences_scanned",
            snippets=len(snippet_ids),
            models=len(models_and_fields),
            occurrences=sum(len(v) for v in occurrences.values()),
        )
        return occurrences

    def _get_snippet_template_occurrence(self, snippet_module, snippet_id):
        snippet_template_html = self.env["ir.qweb"]._render(
            f"{snippet_module}.{snippet_id}", raise_if_not_found=False
        )
        if snippet_template_html:
            match = re.search(r'<([^>]*class="[^>]*)>', snippet_template_html)
            if match:
                return [match.group()]
        return []

    def _is_snippet_used(
        self, snippet_module, snippet_id, asset_version, asset_type, html_fields
    ):
        if self._is_snippet_used_in_occurrences(
            self._get_snippet_template_occurrence(snippet_module, snippet_id),
            asset_type,
            asset_version,
        ):
            return True
        return self._is_snippet_used_in_occurrences(
            self._get_snippet_occurrences([snippet_id], html_fields)[snippet_id],
            asset_type,
            asset_version,
        )

    def _is_snippet_used_in_occurrences(
        self, snippet_occurences, asset_type, asset_version
    ):
        for snippet in snippet_occurences:
            if asset_version == "000":
                if f"data-v{asset_type}" not in snippet:
                    return True
            elif f'data-v{asset_type}="{asset_version}"' in snippet:
                return True
        return False

    def _check_access_to_modify(self, record):
        record.check_access("write")

    def _filter_modifiable(self, records):
        modifiable = records._filtered_access("write")
        _debug.logic(
            "website_modifiable_filtered",
            records=records,
            modifiable=len(modifiable),
        )
        return modifiable

    def _disable_unused_snippets_assets(self):
        _debug.pipeline("disable_unused_snippets", website=self.id)
        snippet_assets = (
            self.env["ir.asset"]
            .with_context(active_test=False)
            .search_fetch(
                [("path", "like", "/static%/snippets/")], ["active", "path"], order="id"
            )
        )
        snippet_re = re.compile(
            r"(\w*)\/.*\/snippets\/(\w*)\/(\d{3})(?:_\w*)?\.(js|scss)"
        )
        html_fields = self._get_fields_html()

        # One pass to learn which snippets exist, then ONE scan of the stored
        # html for all of them, then the per-(version, flavour) decision. The
        # scan used to run once per asset and depends only on the snippet id.
        parsed = []
        for snippet_asset in snippet_assets:
            match = snippet_re.match(snippet_asset.path)
            if not match:
                continue
            (snippet_module, snippet_id, asset_version, asset_type) = match.groups()
            if asset_type == "scss":
                asset_type = "css"
            parsed.append(
                (snippet_asset, snippet_module, snippet_id, asset_version, asset_type)
            )
        stored_occurrences = self._get_snippet_occurrences(
            {snippet_id for _a, _m, snippet_id, _v, _t in parsed}, html_fields
        )
        template_occurrences = {}
        snippet_used = {}
        for (
            snippet_asset,
            snippet_module,
            snippet_id,
            asset_version,
            asset_type,
        ) in parsed:
            key = (
                snippet_id,
                asset_version,
                asset_type,
            )
            if key not in snippet_used:
                if snippet_id not in template_occurrences:
                    template_occurrences[snippet_id] = (
                        self._get_snippet_template_occurrence(
                            snippet_module, snippet_id
                        )
                    )
                snippet_used[key] = self._is_snippet_used_in_occurrences(
                    template_occurrences[snippet_id], asset_type, asset_version
                ) or self._is_snippet_used_in_occurrences(
                    stored_occurrences.get(snippet_id, ()), asset_type, asset_version
                )
            is_snippet_used = snippet_used[key]
            if is_snippet_used != snippet_asset.active:
                _debug.lifecycle(
                    "snippet_asset_toggled",
                    path=snippet_asset.path,
                    active=is_snippet_used,
                )
                snippet_asset.active = is_snippet_used
                if (
                    snippet_id == "s_quotes_carousel"
                    and asset_type == "css"
                    and asset_version in ["000", "001"]
                ):
                    old_blockquote_key = ("s_blockquote", "000", "css")
                    if not snippet_used.get(old_blockquote_key):
                        snippet_used[old_blockquote_key] = True
                        old_blockquote_asset = snippet_assets.filtered(
                            lambda asset: (
                                asset.path
                                == "website/static/src/snippets/s_blockquote/000.scss"
                            )
                        )
                        if old_blockquote_asset and not old_blockquote_asset.active:
                            old_blockquote_asset.active = True
        self.env["ir.asset"].flush_model()

    def _is_every_consent_granted(self):
        self.check_singleton()
        return not self.cookies_bar or self.env["ir.http"]._is_allowed_cookie(
            "optional"
        )
