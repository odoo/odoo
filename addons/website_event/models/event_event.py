import json
from ast import literal_eval
from datetime import UTC
from urllib.parse import urlencode

from dateutil.relativedelta import relativedelta
from markupsafe import Markup

from odoo import _, api, fields, models, tools
from odoo.exceptions import ValidationError
from odoo.fields import Domain
from odoo.libs.datetime import timezone
from odoo.libs.debug_log import DebugLog
from odoo.tools.misc import format_date, get_lang

_debug = DebugLog(__name__)

GOOGLE_CALENDAR_URL = "https://www.google.com/calendar/render?"


class EventEvent(models.Model):
    _name = "event.event"
    _inherit = [
        "event.event",
        "mixin.website.seo.metadata",
        "mixin.website.published.multi",
        "mixin.website.cover_properties",
        "mixin.website.searchable",
        "mixin.website.page_visibility_options",
    ]

    def _default_cover_properties(self):
        res = super()._default_cover_properties()
        res.update(
            {
                "background-image": "url('/website_event/static/src/img/event_cover_4.jpg')",
                "opacity": "0.4",
                "resize_class": "cover_auto",
            }
        )
        return res

    subtitle = fields.Char(
        string="Event Subtitle",
        translate=True,
    )
    is_participating = fields.Boolean(
        compute="_compute_is_participating",
        search="_search_is_participating",
    )
    is_visible_on_website = fields.Boolean(
        string="Visible On Website",
        compute="_compute_is_visible_on_website",
        search="_search_is_visible_on_website",
    )
    event_register_url = fields.Char(
        string="Event Registration Link",
        compute="_compute_event_register_url",
    )
    website_visibility = fields.Selection(
        selection=[
            ("public", "Public"),
            ("link", "Via a Link"),
            ("logged_users", "Logged Users"),
        ],
        default="public",
        required=True,
        tracking=True,
        help="""Defines the Visibility of the Event on the Website and searches.\n
            Note that the EventEvent is however always available via its link.""",
    )
    website_published = fields.Boolean(tracking=True)
    website_menu = fields.Boolean(
        compute="_compute_website_menu",
        precompute=True,
        store=True,
        readonly=False,
        help="Allows to display and manage event-specific menus on website.",
    )
    menu_id = fields.Many2one(
        comodel_name="website.menu",
        string="Event Menu",
        copy=False,
    )
    introduction_menu = fields.Boolean(
        compute="_compute_website_menu_data",
        store=True,
        readonly=False,
    )
    introduction_menu_ids = fields.One2many(
        comodel_name="website.event.menu",
        inverse_name="event_id",
        string="Introduction Menus",
        domain=[("menu_type", "=", "introduction")],
    )
    address_name = fields.Char(related="address_id.name")
    register_menu = fields.Boolean(
        compute="_compute_website_menu_data",
        store=True,
        readonly=False,
    )
    register_menu_ids = fields.One2many(
        comodel_name="website.event.menu",
        inverse_name="event_id",
        string="Register Menus",
        domain=[("menu_type", "=", "register")],
    )
    community_menu = fields.Boolean(
        compute="_compute_community_menu",
        store=True,
        readonly=False,
        help="Display community tab on website",
    )
    community_menu_ids = fields.One2many(
        comodel_name="website.event.menu",
        inverse_name="event_id",
        string="Event Community Menus",
        domain=[("menu_type", "=", "community")],
    )
    other_menu_ids = fields.One2many(
        comodel_name="website.event.menu",
        inverse_name="event_id",
        string="Other Menus",
        domain=[("menu_type", "=", "other")],
    )
    is_ongoing = fields.Boolean(
        compute="_compute_time_data",
        search="_search_is_ongoing",
        help="Whether event has begun",
    )
    is_done = fields.Boolean(compute="_compute_time_data")
    start_today = fields.Boolean(
        compute="_compute_time_data",
        help="Whether event is going to start today if still not ongoing",
    )
    start_remaining = fields.Integer(
        string="Remaining before start",
        compute="_compute_time_data",
        help="Remaining time before event starts (minutes)",
    )

    @api.depends("website_url")
    def _compute_event_share_url(self):
        for event in self:
            event.event_share_url = event.event_url or tools.urls.urljoin(
                event.get_base_url(), event.website_url
            )

    @api.depends("registration_ids")
    @api.depends_context("uid")
    def _compute_is_participating(self):
        participating_events = self._get_participating_events()
        participating_events.is_participating = True
        (self - participating_events).is_participating = False

    @api.model
    def _search_is_participating(self, operator, value):
        if operator != "in":
            return NotImplemented
        return [("id", "in", self._get_participating_events().ids)]

    @api.model
    def _get_participating_events(self):
        current_visitor = self.env["website.visitor"]._get_visitor_from_request()
        if self.env.user._is_public() and not current_visitor:
            return self.env["event.event"]

        base_domain = Domain("state", "in", ["open", "done"])
        if self:
            base_domain = Domain("event_id", "in", self.ids) & base_domain

        visitor_domain = Domain.FALSE
        partner_id = self.env.user.partner_id
        if current_visitor:
            visitor_domain = Domain("visitor_id", "=", current_visitor.id)
            partner_id = current_visitor.partner_id
        if partner_id:
            visitor_domain |= Domain("partner_id", "=", partner_id.id)

        registrations_events = (
            self.env["event.registration"]
            .sudo()
            ._read_group(visitor_domain & base_domain, ["event_id"], ["__count"])
        )
        return self.env["event.event"].browse(
            [event.id for event, _reg_count in registrations_events]
        )

    @api.depends_context("uid")
    @api.depends("website_visibility", "is_participating")
    def _compute_is_visible_on_website(self):
        if all(event.website_visibility == "public" for event in self):
            self.is_visible_on_website = True
            return
        for event in self:
            if (
                event.website_visibility == "public"
                or event.is_participating
                or (
                    not self.env.user._is_public()
                    and event.website_visibility == "logged_users"
                )
            ):
                event.is_visible_on_website = True
            else:
                event.is_visible_on_website = False

    @api.model
    def _search_is_visible_on_website(self, operator, value):
        if operator != "in":
            return NotImplemented
        user = self.env.user
        visibility = ["public"]
        if not user._is_public():
            visibility.append("logged_users")
        return [
            "|",
            ("is_participating", "=", True),
            ("website_visibility", "in", visibility),
        ]

    @api.depends("website_url")
    def _compute_event_register_url(self):
        for event in self:
            event.event_register_url = tools.urls.urljoin(
                event.get_base_url(), f"{event.website_url}/register"
            )

    @api.depends("event_type_id")
    def _compute_website_menu(self):
        for event in self:
            if (
                event.event_type_id
                and event.event_type_id != event._origin.event_type_id
            ):
                event.website_menu = event.event_type_id.website_menu
            elif not event.website_menu:
                event.website_menu = False

    @api.depends("event_type_id", "website_menu", "community_menu")
    def _compute_community_menu(self):
        for event in self:
            event.community_menu = False

    @api.depends("website_menu")
    def _compute_website_menu_data(self):
        for event in self:
            event.introduction_menu = event.website_menu
            event.register_menu = event.website_menu

    @api.depends("date_begin", "date_end")
    def _compute_time_data(self):
        now_utc = fields.Datetime.now().replace(microsecond=0).replace(tzinfo=UTC)
        for event in self:
            date_begin_utc = event.date_begin.replace(tzinfo=UTC)
            date_end_utc = event.date_end.replace(tzinfo=UTC)
            event.is_ongoing = date_begin_utc <= now_utc <= date_end_utc
            event.is_done = now_utc > date_end_utc
            event.start_today = date_begin_utc.date() == now_utc.date()
            if date_begin_utc >= now_utc:
                td = date_begin_utc - now_utc
                event.start_remaining = int(td.total_seconds() / 60)
            else:
                event.start_remaining = 0

    @api.depends("name")
    def _compute_website_url(self):
        super()._compute_website_url()
        for event in self:
            if event.id:
                event.website_url = "/event/%s" % self.env["ir.http"]._slug(event)

    @api.constrains("website_id")
    def _check_website_id(self):
        for event in self:
            if event.website_id and event.website_id.company_id != event.company_id:
                _debug.logic(
                    "event_website_refused",
                    reason="company_mismatch",
                    event=event.id,
                    website=event.website_id.id,
                )
                raise ValidationError(
                    _("The website must be from the same company as the event.")
                )

    def copy(self, default=None):
        res = super().copy(default=default)
        res.copy_event_menus(self)
        return res

    def copy_event_menus(self, old_events):
        for new_event, old_event in zip(self, old_events, strict=True):
            default_menu_values = {"event_id": new_event.id}
            new_event.menu_id = old_event.menu_id.copy(
                {"name": new_event.name, "website_id": new_event.website_id.id}
            )
            new_event.introduction_menu_ids = old_event.introduction_menu_ids.copy(
                default_menu_values
            )
            new_event.other_menu_ids = old_event.other_menu_ids.copy(
                default_menu_values
            )
            (
                new_event.introduction_menu_ids
                + new_event.other_menu_ids
                + new_event.community_menu_ids
                + new_event.register_menu_ids
            ).menu_id.parent_id = new_event.menu_id

    @api.model_create_multi
    def create(self, vals_list):
        events = super().create(vals_list)
        events._update_website_menus()
        return events

    def write(self, vals):
        menus_state_by_field = self._split_menus_state_by_field()
        res = super().write(vals)
        menus_update_by_field = self._get_menus_update_by_field(
            menus_state_by_field, force_update=vals.keys()
        )
        self._update_website_menus(menus_update_by_field=menus_update_by_field)
        return res

    def toggle_website_menu(self, val):
        self.website_menu = val

    def _get_fields_menu_update(self):
        return ["community_menu", "introduction_menu", "register_menu"]

    def _get_menu_type_field_matching(self):
        return {
            "community": "community_menu",
            "introduction": "introduction_menu",
            "register": "register_menu",
        }

    def _split_menus_state_by_field(self):
        menus_state_by_field = {}
        for fname in self._get_fields_menu_update():
            activated = self.filtered(lambda event, fname=fname: event[fname])
            menus_state_by_field[fname] = {
                "activated": activated,
                "deactivated": self - activated,
            }
        return menus_state_by_field

    def _get_menus_update_by_field(self, menus_state_by_field, force_update=None):
        menus_update_by_field = {}
        for fname in self._get_fields_menu_update():
            if fname in force_update:
                menus_update_by_field[fname] = self
            else:
                menus_update_by_field[fname] = self.env["event.event"]
                menus_update_by_field[fname] |= menus_state_by_field[fname][
                    "activated"
                ].filtered(lambda event, fname=fname: not event[fname])
                menus_update_by_field[fname] |= menus_state_by_field[fname][
                    "deactivated"
                ].filtered(lambda event, fname=fname: event[fname])
        return menus_update_by_field

    def _get_website_menu_entries(self):
        self.check_singleton()
        return [
            (
                _("Home"),
                False,
                "website_event.template_intro",
                1,
                "introduction",
                False,
            ),
            (
                _("Practical"),
                "/event/%s/register" % self.env["ir.http"]._slug(self),
                False,
                100,
                "register",
                False,
            ),
            (
                _("Rooms"),
                "/event/%s/community" % self.env["ir.http"]._slug(self),
                False,
                80,
                "community",
                False,
            ),
        ]

    def _update_website_menus(self, menus_update_by_field=None):
        for event in self:
            if event.menu_id and not event.website_menu:
                (event.menu_id + event.menu_id.child_id).sudo().unlink()
            elif event.website_menu and not event.menu_id:
                root_menu = (
                    self.env["website.menu"]
                    .sudo()
                    .create({"name": event.name, "website_id": event.website_id.id})
                )
                event.menu_id = root_menu
            if event.menu_id and (
                not menus_update_by_field
                or event in menus_update_by_field.get("community_menu")
            ):
                event._update_website_menu_entry(
                    "community_menu", "community_menu_ids", "community"
                )
            if event.menu_id and (
                not menus_update_by_field
                or event in menus_update_by_field.get("introduction_menu")
            ):
                event._update_website_menu_entry(
                    "introduction_menu", "introduction_menu_ids", "introduction"
                )
            if event.menu_id and (
                not menus_update_by_field
                or event in menus_update_by_field.get("register_menu")
            ):
                event._update_website_menu_entry(
                    "register_menu", "register_menu_ids", "register"
                )

    def _update_website_menu_entry(self, fname_bool, fname_o2m, fmenu_type):
        self.check_singleton()
        new_menu = None

        menu_data = [
            menu_info
            for menu_info in self._get_website_menu_entries()
            if menu_info[4] == fmenu_type
        ]
        if self[fname_bool] and not self[fname_o2m]:
            for (
                name,
                url,
                xml_id,
                menu_sequence,
                menu_type,
                parent_menu_type,
            ) in menu_data:
                new_menu = self._create_menu(
                    menu_sequence, name, url, xml_id, menu_type, parent_menu_type
                )
        elif not self[fname_bool]:
            self[fname_o2m].mapped("menu_id").sudo().unlink()

        return new_menu

    def _create_menu(
        self, sequence, name, url, xml_id, menu_type, parent_menu_type=False
    ):
        self.browse().check_access("write")
        view_id = False
        if not url:
            page_result = (
                self.env["website"]
                .sudo()
                .new_page(
                    name=f"{name} {self.name}",
                    template=xml_id,
                    add_menu=False,
                    ispage=False,
                )
            )
            view_id = page_result["view_id"]
            view = self.env["ir.ui.view"].browse(view_id)
            url = f"/event/{self.env['ir.http']._slug(self)}/page/{view.key.split('.')[-1]}"

        parent_id = self.menu_id.id
        if parent_menu_type:
            parent_menu = self.env["website.event.menu"].search(
                [("event_id", "=", self.id), ("menu_type", "=", parent_menu_type)],
                limit=1,
            )
            if parent_menu:
                parent_id = parent_menu.menu_id.id
        website_menu = (
            self.env["website.menu"]
            .sudo()
            .create(
                {
                    "name": name,
                    "url": url,
                    "parent_id": parent_id,
                    "sequence": sequence,
                    "website_id": self.website_id.id,
                }
            )
        )
        self.env["website.event.menu"].create(
            {
                "menu_id": website_menu.id,
                "event_id": self.id,
                "menu_type": menu_type,
                "view_id": view_id,
            }
        )
        return website_menu

    def google_map_link(self, zoom=8):
        return self._google_map_link(zoom=zoom)

    def _google_map_link(self, zoom=8):
        self.check_singleton()
        if self.address_id:
            return self.sudo().address_id.google_map_link(zoom=zoom)
        return None

    def _track_subtype(self, init_values):
        self.check_singleton()
        if init_values.keys() & {"is_published", "website_published"}:
            if self.is_published:
                return self.env.ref(
                    "website_event.mt_event_published", raise_if_not_found=False
                )
            return self.env.ref(
                "website_event.mt_event_unpublished", raise_if_not_found=False
            )
        return super()._track_subtype(init_values)

    def _get_event_resource_urls(self, slot=False):
        start = slot.start_datetime if slot else self.date_begin
        end = slot.end_datetime if slot else self.date_end
        url_date_start = start.astimezone(timezone(self.date_tz)).strftime(
            "%Y%m%dT%H%M%S"
        )
        url_date_stop = end.astimezone(timezone(self.date_tz)).strftime("%Y%m%dT%H%M%S")
        params = {
            "action": "TEMPLATE",
            "text": self.name,
            "dates": f"{url_date_start}/{url_date_stop}",
            "ctz": self.date_tz,
            "details": self._get_external_description(),
        }
        if self.address_id:
            params.update(location=self.address_inline)
        encoded_params = urlencode(params)
        google_url = GOOGLE_CALENDAR_URL + encoded_params
        iCal_url = f"/event/{self.id:d}/ics"
        if slot:
            iCal_url += "?" + urlencode({"slot_id": slot.id})
        return {"google_url": google_url, "iCal_url": iCal_url}

    def _get_default_website_meta(self):
        res = super()._get_default_website_meta()
        event_cover_properties = json.loads(self.cover_properties)
        res["default_opengraph"]["og:image"] = res["default_twitter"][
            "twitter:image"
        ] = event_cover_properties.get("background-image", "none")[4:-1].strip("'")
        res["default_opengraph"]["og:title"] = res["default_twitter"][
            "twitter:title"
        ] = self.name
        res["default_opengraph"]["og:description"] = res["default_twitter"][
            "twitter:description"
        ] = self.subtitle
        res["default_twitter"]["twitter:card"] = "summary"
        res["default_meta_description"] = self.subtitle
        return res

    def get_backend_menu_id(self):
        return self.env.ref("event.event_main_menu").id

    @api.model
    def _search_build_dates(self):
        now = fields.Datetime.now()
        tz = timezone(self.env.user.tz or self.env.context.get("tz") or "UTC")
        localized_today_begin = fields.Datetime.today().replace(tzinfo=tz)
        utc_today_end = localized_today_begin.replace(
            hour=23, minute=59, second=59
        ).astimezone(UTC)

        def sd(date):
            return fields.Datetime.to_string(date)

        def get_domain_month_filter(filter_name, months_delta):
            localized_month_begin = localized_today_begin.replace(day=1)
            utc_months_delta_end = (
                localized_month_begin + relativedelta(months=months_delta + 1)
            ).astimezone(UTC)
            filter_string = (
                _("This month")
                if months_delta == 0
                else format_date(
                    self.env,
                    value=localized_today_begin + relativedelta(months=months_delta),
                    date_format="LLLL",
                    lang_code=get_lang(self.env).code,
                ).capitalize()
            )
            return [
                filter_name,
                filter_string,
                [
                    ("date_end", ">=", sd(now)),
                    ("date_begin", "<", sd(utc_months_delta_end)),
                ],
                0,
            ]

        return [
            ["scheduled", _("Scheduled Events"), [("date_end", ">=", sd(now))], 0],
            [
                "today",
                _("Today"),
                [("date_end", ">", sd(now)), ("date_begin", "<", sd(utc_today_end))],
                0,
            ],
            get_domain_month_filter("month", 0),
            ["old", _("Past Events"), [("date_end", "<", sd(now))], 0],
            ["all", _("All Events"), [], 0],
        ]

    @api.model
    def _search_get_detail(self, website, order, options):
        with_description = options["displayDescription"]
        with_date = options["displayDetail"]
        date = options.get("date", "all")
        country = options.get("country")
        tags = options.get("tags")
        event_type = options.get("type", "all")

        domain = [website.website_domain()]
        domain.append([("is_visible_on_website", "=", True)])

        if event_type != "all" and str(event_type).isdigit():
            domain.append([("event_type_id", "=", int(event_type))])
        search_tags = self.env["event.tag"]
        if tags:
            try:
                tag_ids = list(
                    filter(
                        None,
                        [
                            self.env["ir.http"]._unslug(tag)[1]
                            for tag in tags.split(",")
                        ],
                    )
                ) or literal_eval(tags)
            except SyntaxError:
                pass
            except ValueError:
                pass
            else:
                search_tags = self.env["event.tag"].search([("id", "in", tag_ids)])

            domain.extend(
                [("tag_ids", "in", tags.ids)]
                for tags in search_tags.grouped("category_id").values()
            )

        no_country_domain = domain.copy()
        if country:
            if country == "online":
                domain.append([("country_id", "=", False)])
            elif country != "all" and str(country).isdigit():
                domain.append([("country_id", "=", int(country))])

        no_date_domain = domain.copy()
        dates = self._search_build_dates()
        current_date = None
        for date_details in dates:
            if date == date_details[0]:
                domain.append(date_details[2])
                no_country_domain.append(date_details[2])
                if date_details[0] != "scheduled":
                    current_date = date_details[1]

        search_fields = ["name"]
        fetch_fields = ["name", "website_url", "address_name"]
        mapping = {
            "name": {"name": "name", "type": "text", "match": True},
            "website_url": {"name": "website_url", "type": "text", "truncate": False},
            "address_name": {"name": "address_name", "type": "text", "match": True},
        }
        if with_description:
            search_fields.append("subtitle")
            fetch_fields.append("subtitle")
            mapping["description"] = {"name": "subtitle", "type": "text", "match": True}
        if with_date:
            mapping["detail"] = {"name": "range", "type": "html"}

        def search_in_address(env, search_term):
            ret = (
                env["event.event"]
                .sudo()
                ._search(
                    [
                        ("address_search", "ilike", search_term),
                    ]
                )
            )
            return [("id", "in", ret)]

        return {
            "model": "event.event",
            "base_domain": domain,
            "search_fields": search_fields,
            "search_extra": search_in_address,
            "fetch_fields": fetch_fields,
            "mapping": mapping,
            "icon": "fa-ticket",
            "dates": dates,
            "current_date": current_date,
            "search_tags": search_tags,
            "no_date_domain": no_date_domain,
            "no_country_domain": no_country_domain,
        }

    def _search_render_results(self, fetch_fields, mapping, icon, limit):
        with_date = "detail" in mapping
        results_data = super()._search_render_results(
            fetch_fields, mapping, icon, limit
        )
        if with_date:
            for event, data in zip(self, results_data, strict=True):
                begin = self.env["ir.qweb.field.date"].record_to_html(
                    event, "date_begin", {}
                )
                end = self.env["ir.qweb.field.date"].record_to_html(
                    event, "date_end", {}
                )
                data["range"] = (
                    Markup('{} <i class="fa-solid fa-right-long"></i> {}').format(
                        begin, end
                    )
                    if begin != end
                    else begin
                )
        return results_data
