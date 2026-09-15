import logging
from datetime import UTC, timedelta
from random import randint
from textwrap import shorten
from urllib.parse import urlencode

from markupsafe import Markup

from odoo import api, fields, models, tools
from odoo.exceptions import UserError
from odoo.fields import Domain
from odoo.libs.datetime import timezone
from odoo.libs.debug_log import DebugLog
from odoo.tools.mail import email_normalize, html_to_inner_content, is_html_empty
from odoo.tools.translate import _, html_translate

_logger = logging.getLogger(__name__)
_debug = DebugLog(__name__)

try:
    import vobject
except ImportError:
    _logger.warning(
        "`vobject` Python module not found, iCal file generation disabled. Consider installing this module if you want to generate iCal files"
    )
    vobject = None

GOOGLE_CALENDAR_URL = "https://www.google.com/calendar/render?"


class EventTrack(models.Model):
    _name = "event.track"
    _description = "Event Track"
    _order = "priority desc, date"
    _inherit = [
        "mixin.mail.thread",
        "mixin.mail.activity",
        "mixin.website.seo.metadata",
        "mixin.website.published",
        "mixin.website.searchable",
    ]
    _primary_email = "contact_email"

    @api.model
    def _default_stage_id(self):
        return self.env["event.track.stage"].search([], limit=1).id

    name = fields.Char(
        string="Title",
        translate=True,
        required=True,
    )
    event_id = fields.Many2one(
        comodel_name="event.event",
        index=True,
        required=True,
    )
    active = fields.Boolean(default=True)
    user_id = fields.Many2one(
        comodel_name="res.users",
        string="Responsible",
        default=lambda self: self.env.user,
        tracking=True,
    )
    company_id = fields.Many2one(
        comodel_name="res.company",
        related="event_id.company_id",
    )
    tag_ids = fields.Many2many(
        comodel_name="event.track.tag",
        string="Tags",
    )
    description = fields.Html(
        translate=html_translate,
        sanitize_attributes=False,
        sanitize_form=False,
    )
    color = fields.Integer(string="Agenda Color")
    priority = fields.Selection(
        selection=[("0", "Low"), ("1", "Medium"), ("2", "High"), ("3", "Highest")],
        default="1",
        required=True,
    )
    stage_id = fields.Many2one(
        comodel_name="event.track.stage",
        default=_default_stage_id,
        index=True,
        copy=False,
        required=True,
        group_expand="_read_group_expand_full",
        ondelete="restrict",
        tracking=True,
    )
    legend_blocked = fields.Char(
        related="stage_id.legend_blocked",
        string="Kanban Blocked Explanation",
        readonly=True,
    )
    legend_done = fields.Char(
        related="stage_id.legend_done",
        string="Kanban Valid Explanation",
        readonly=True,
    )
    legend_normal = fields.Char(
        related="stage_id.legend_normal",
        string="Kanban Ongoing Explanation",
        readonly=True,
    )
    kanban_state = fields.Selection(
        selection=[("normal", "Grey"), ("done", "Green"), ("blocked", "Red")],
        default="normal",
        copy=False,
        required=True,
        help="A track's kanban state indicates special situations affecting it:\n"
        " * Grey is the default situation\n"
        " * Red indicates something is preventing the progress of this track\n"
        " * Green indicates the track is ready to be pulled to the next stage",
    )
    kanban_state_label = fields.Char(
        compute="_compute_kanban_state_label",
        store=True,
        tracking=True,
    )
    partner_id = fields.Many2one(
        comodel_name="res.partner",
        string="Contact",
    )
    partner_name = fields.Char(
        string="Name",
        compute="_compute_partner_name",
        store=True,
        readonly=False,
        tracking=10,
    )
    partner_email = fields.Char(
        string="Email",
        compute="_compute_partner_email",
        store=True,
        readonly=False,
        tracking=20,
    )
    phone_ids = fields.Many2many(
        comodel_name="phone.number",
        relation="event_track_phone_number_rel",
        column1="track_id",
        column2="phone_number_id",
        compute="_compute_phone_ids",
        store=True,
        readonly=False,
    )
    partner_biography = fields.Html(
        string="Biography",
        sanitize_attributes=False,
        compute="_compute_partner_biography",
        store=True,
        readonly=False,
    )
    partner_function = fields.Char(
        string="Job Position",
        compute="_compute_partner_function",
        store=True,
        readonly=False,
    )
    partner_company_name = fields.Char(
        string="Company Name",
        compute="_compute_partner_company_name",
        store=True,
        readonly=False,
    )
    partner_tag_line = fields.Char(
        string="Tag Line",
        compute="_compute_partner_tag_line",
        help="Description of the partner (name, function and company name)",
    )
    image = fields.Image(
        string="Speaker Photo",
        max_width=256,
        max_height=256,
        compute="_compute_partner_image",
        store=True,
        readonly=False,
    )
    contact_email = fields.Char(
        compute="_compute_contact_email",
        store=True,
        readonly=False,
        tracking=20,
    )
    contact_phone_ids = fields.Many2many(
        comodel_name="phone.number",
        relation="event_track_contact_phone_number_rel",
        column1="track_id",
        column2="phone_number_id",
        compute="_compute_contact_phone_ids",
        store=True,
        readonly=False,
    )
    location_id = fields.Many2one(comodel_name="event.track.location")
    date = fields.Datetime(
        string="Track Date",
        compute="_compute_date",
        inverse="_inverse_date",
        store=True,
    )
    date_end = fields.Datetime(
        string="Track End Date",
        compute="_compute_end_date",
        inverse="_inverse_date_end",
        store=True,
    )
    duration = fields.Float(default=0.5)
    is_track_live = fields.Boolean(compute="_compute_track_time_data")
    is_track_soon = fields.Boolean(compute="_compute_track_time_data")
    is_track_today = fields.Boolean(compute="_compute_track_time_data")
    is_track_upcoming = fields.Boolean(compute="_compute_track_time_data")
    is_track_done = fields.Boolean(compute="_compute_track_time_data")
    is_one_day = fields.Boolean(compute="_compute_is_one_day")
    track_start_remaining = fields.Integer(
        string="Minutes before track starts",
        compute="_compute_track_time_data",
        help="Remaining time before track starts (seconds)",
    )
    track_start_relative = fields.Integer(
        string="Minutes compare to track start",
        compute="_compute_track_time_data",
        help="Relative time compared to track start (seconds)",
    )
    website_image = fields.Image(
        max_width=1024,
        max_height=1024,
    )
    website_image_url = fields.Char(
        string="Image URL",
        compute="_compute_website_image_url",
        compute_sudo=True,
        store=False,
    )
    header_visible = fields.Boolean(
        related="event_id.header_visible",
        readonly=False,
    )
    footer_visible = fields.Boolean(
        related="event_id.footer_visible",
        readonly=False,
    )
    event_track_visitor_ids = fields.One2many(
        comodel_name="event.track.visitor",
        inverse_name="track_id",
        string="Track Visitors",
        groups="event.group_event_user",
    )
    is_reminder_on = fields.Boolean(compute="_compute_is_reminder_on")
    wishlist_visitor_ids = fields.Many2many(
        comodel_name="website.visitor",
        string="Visitor Wishlist",
        compute="_compute_wishlist_visitor_ids",
        search="_search_wishlist_visitor_ids",
        compute_sudo=True,
        groups="event.group_event_user",
    )
    wishlist_visitor_count = fields.Integer(
        string="# Wishlisted",
        compute="_compute_wishlist_visitor_ids",
        compute_sudo=True,
        groups="event.group_event_user",
    )
    wishlisted_by_default = fields.Boolean(
        string="Always Wishlisted",
        help="""If set, the talk will be set as favorite for each attendee registered to the event.""",
    )
    website_cta = fields.Boolean(
        string="Magic Button",
        help="Display a Call to Action button to your Attendees while they watch your Track.",
    )
    website_cta_title = fields.Char(string="Button Title")
    website_cta_url = fields.Char(string="Button Target URL")
    website_cta_delay = fields.Integer(string="Show Button")
    is_website_cta_live = fields.Boolean(
        string="Is CTA Live",
        compute="_compute_cta_time_data",
        help="CTA button is available",
    )
    website_cta_start_remaining = fields.Integer(
        string="Minutes before CTA starts",
        compute="_compute_cta_time_data",
        help="Remaining time before CTA starts (seconds)",
    )

    @api.depends("name")
    def _compute_website_url(self):
        super()._compute_website_url()
        for track in self:
            if track.id:
                track.website_url = "/event/%s/track/%s" % (
                    self.env["ir.http"]._slug(track.event_id),
                    self.env["ir.http"]._slug(track),
                )

    @api.depends("stage_id", "kanban_state")
    def _compute_kanban_state_label(self):
        for track in self:
            if track.kanban_state == "normal":
                track.kanban_state_label = track.stage_id.legend_normal
            elif track.kanban_state == "blocked":
                track.kanban_state_label = track.stage_id.legend_blocked
            else:
                track.kanban_state_label = track.stage_id.legend_done

    @api.depends("partner_id")
    def _compute_partner_name(self):
        for track in self:
            if track.partner_id and not track.partner_name:
                track.partner_name = track.partner_id.name

    @api.depends("partner_id")
    def _compute_partner_email(self):
        for track in self:
            if track.partner_id and not track.partner_email:
                track.partner_email = track.partner_id.email

    @api.depends("partner_id")
    def _compute_phone_ids(self):
        for track in self:
            if track.partner_id and not track.phone_ids:
                track.phone_ids = track.partner_id.phone_ids._primary()

    @api.depends("partner_id")
    def _compute_partner_biography(self):
        for track in self:
            if not track.partner_biography or (
                track.partner_id
                and is_html_empty(track.partner_biography)
                and not is_html_empty(track.partner_id.website_description)
            ):
                track.partner_biography = track.partner_id.website_description

    @api.depends("partner_id")
    def _compute_partner_function(self):
        for track in self:
            if track.partner_id and not track.partner_function:
                track.partner_function = track.partner_id.function

    @api.depends("partner_id", "partner_id.is_company")
    def _compute_partner_company_name(self):
        for track in self:
            if track.partner_id.is_company:
                track.partner_company_name = track.partner_id.name
            elif not track.partner_company_name:
                track.partner_company_name = track.partner_id.parent_id.name

    @api.depends("partner_name", "partner_function", "partner_company_name")
    def _compute_partner_tag_line(self):
        for track in self:
            if not track.partner_name:
                track.partner_tag_line = False
                continue

            tag_line = track.partner_name
            if track.partner_function:
                if track.partner_company_name:
                    tag_line = _(
                        "%(name)s, %(function)s at %(company)s",
                        name=track.partner_name,
                        function=track.partner_function,
                        company=track.partner_company_name,
                    )
                else:
                    tag_line = "%s, %s" % (track.partner_name, track.partner_function)
            elif track.partner_company_name:
                tag_line = _(
                    "%(name)s from %(company)s",
                    name=tag_line,
                    company=track.partner_company_name,
                )
            track.partner_tag_line = tag_line

    @api.depends("partner_id")
    def _compute_partner_image(self):
        for track in self:
            if not track.image:
                track.image = track.partner_id.image_256

    @api.depends("partner_id", "partner_id.email")
    def _compute_contact_email(self):
        for track in self:
            if track.partner_id:
                track.contact_email = track.partner_id.email

    @api.depends("partner_id", "partner_id.phone_ids")
    def _compute_contact_phone_ids(self):
        for track in self:
            if track.partner_id:
                track.contact_phone_ids = track.partner_id.phone_ids._primary()

    @api.depends("date_end", "duration")
    def _compute_date(self):
        for track in self:
            if track.date_end:
                delta = timedelta(minutes=60 * track.duration)
                track.date = track.date_end - delta
            else:
                track.date = False

    def _inverse_date(self):
        for track in self:
            if track.date and track.date_end:
                track.duration = (track.date_end - track.date).total_seconds() / 3600

    @api.depends("date", "duration")
    def _compute_end_date(self):
        for track in self:
            if track.date:
                delta = timedelta(minutes=60 * track.duration)
                track.date_end = track.date + delta
            else:
                track.date_end = False

    def _inverse_date_end(self):
        for track in self:
            if track.date and track.date_end:
                track.duration = (track.date_end - track.date).total_seconds() / 3600

    @api.depends("image", "partner_id.image_256")
    def _compute_website_image_url(self):
        for track in self:
            if track.website_image:
                track.website_image_url = self.env["website"].image_url(
                    track, "website_image", size=1024
                )
            else:
                track.website_image_url = (
                    "/website_event_track/static/src/img/event_track_default_%d.jpeg"
                    % (track.id % 2)
                )

    @api.depends(
        "wishlisted_by_default",
        "event_track_visitor_ids.visitor_id",
        "event_track_visitor_ids.partner_id",
        "event_track_visitor_ids.is_wishlisted",
        "event_track_visitor_ids.is_blacklisted",
    )
    @api.depends_context("uid")
    def _compute_is_reminder_on(self):
        current_visitor = self.env["website.visitor"]._get_visitor_from_request()
        if self.env.user._is_public() and not current_visitor:
            for track in self:
                track.is_reminder_on = track.wishlisted_by_default
        else:
            if self.env.user._is_public():
                domain = [("visitor_id", "=", current_visitor.id)]
            elif current_visitor:
                domain = [
                    "|",
                    ("partner_id", "=", self.env.user.partner_id.id),
                    ("visitor_id", "=", current_visitor.id),
                ]
            else:
                domain = [("partner_id", "=", self.env.user.partner_id.id)]

            event_track_visitors = (
                self.env["event.track.visitor"]
                .sudo()
                .search_read(
                    Domain.AND([domain, [("track_id", "in", self.ids)]]),
                    fields=["track_id", "is_wishlisted", "is_blacklisted"],
                )
            )

            wishlist_map = {
                track_visitor["track_id"][0]: {
                    "is_wishlisted": track_visitor["is_wishlisted"],
                    "is_blacklisted": track_visitor["is_blacklisted"],
                }
                for track_visitor in event_track_visitors
            }
            for track in self:
                if wishlist_map.get(track.id):
                    track.is_reminder_on = wishlist_map.get(track.id)[
                        "is_wishlisted"
                    ] or (
                        track.wishlisted_by_default
                        and not wishlist_map[track.id]["is_blacklisted"]
                    )
                else:
                    track.is_reminder_on = track.wishlisted_by_default

    @api.depends(
        "event_track_visitor_ids.visitor_id", "event_track_visitor_ids.is_wishlisted"
    )
    def _compute_wishlist_visitor_ids(self):
        results = self.env["event.track.visitor"]._read_group(
            [("track_id", "in", self.ids), ("is_wishlisted", "=", True)],
            ["track_id"],
            ["visitor_id:array_agg"],
        )
        visitor_ids_map = {track.id: visitor_ids for track, visitor_ids in results}
        for track in self:
            track.wishlist_visitor_ids = visitor_ids_map.get(track.id, [])
            track.wishlist_visitor_count = len(visitor_ids_map.get(track.id, []))

    def _search_wishlist_visitor_ids(self, operator, operand):
        if operator in ("not in", "not any"):
            _debug.logic("wishlist_search_refused", operator=operator)
            raise UserError(
                self.env._("Unsupported 'Not In' operation on track wishlist visitors")
            )

        subquery = (
            self.env["event.track.visitor"]
            .sudo()
            ._search([("visitor_id", operator, operand), ("is_wishlisted", "=", True)])
        )
        return [("id", "in", subquery.subselect("track_id"))]

    @api.depends("date", "date_end")
    def _compute_track_time_data(self):
        now_utc = fields.Datetime.now().replace(microsecond=0).replace(tzinfo=UTC)
        for track in self:
            if not (track.date or track.date_end):
                track.is_track_live = track.is_track_soon = track.is_track_today = (
                    track.is_track_upcoming
                ) = track.is_track_done = False
                track.track_start_relative = track.track_start_remaining = 0
                continue
            date_begin_utc = track.date.replace(tzinfo=UTC)
            date_end_utc = track.date_end.replace(tzinfo=UTC)
            track.is_track_live = date_begin_utc <= now_utc < date_end_utc
            track.is_track_soon = (
                (date_begin_utc - now_utc).total_seconds() < 30 * 60
                if date_begin_utc > now_utc
                else False
            )
            track.is_track_today = date_begin_utc.date() == now_utc.date()
            track.is_track_upcoming = date_begin_utc > now_utc
            track.is_track_done = date_end_utc <= now_utc
            if date_begin_utc >= now_utc:
                track.track_start_relative = int(
                    (date_begin_utc - now_utc).total_seconds()
                )
                track.track_start_remaining = track.track_start_relative
            else:
                track.track_start_relative = int(
                    (now_utc - date_begin_utc).total_seconds()
                )
                track.track_start_remaining = 0

    @api.depends("date", "date_end", "website_cta", "website_cta_delay")
    def _compute_cta_time_data(self):
        now_utc = fields.Datetime.now().replace(microsecond=0).replace(tzinfo=UTC)
        for track in self:
            if not track.website_cta:
                track.is_website_cta_live = track.website_cta_start_remaining = False
                continue

            date_begin_utc = track.date.replace(tzinfo=UTC) + timedelta(
                minutes=track.website_cta_delay or 0
            )
            date_end_utc = track.date_end.replace(tzinfo=UTC)
            track.is_website_cta_live = date_begin_utc <= now_utc <= date_end_utc
            if date_begin_utc >= now_utc:
                td = date_begin_utc - now_utc
                track.website_cta_start_remaining = int(td.total_seconds())
            else:
                track.website_cta_start_remaining = 0

    @api.depends("date", "date_end", "event_id")
    def _compute_is_one_day(self):
        for track in self:
            if not (track.date or track.date_end):
                track.is_one_day = False
                continue
            track = track.with_context(tz=track.event_id.date_tz or "UTC")
            begin_tz = fields.Datetime.context_timestamp(track, track.date)
            end_tz = fields.Datetime.context_timestamp(track, track.date_end)
            track.is_one_day = begin_tz.date() == end_tz.date()

    @api.model_create_multi
    def create(self, vals_list):
        for values in vals_list:
            if values.get("website_cta_url"):
                values["website_cta_url"] = self.env["res.partner"]._clean_website(
                    values["website_cta_url"]
                )

        tracks = super().create(vals_list)
        _debug.lifecycle("create", tracks=tracks, count=len(tracks))

        post_values = (
            {}
            if self.env.user.email
            else {"email_from": self.env.company.catchall_formatted}
        )
        for track in tracks:
            track.event_id.message_post_with_source(
                "website_event_track.event_track_template_new",
                render_values={
                    "track": track,
                    "is_html_empty": is_html_empty,
                },
                subtype_xmlid="website_event_track.mt_event_track",
                **post_values,
            )
            track._sync_with_stage(track.stage_id)

        return tracks

    def write(self, vals):
        if vals.get("website_cta_url"):
            vals["website_cta_url"] = self.env["res.partner"]._clean_website(
                vals["website_cta_url"]
            )
        if "stage_id" in vals and "kanban_state" not in vals:
            vals["kanban_state"] = "normal"
        if vals.get("stage_id"):
            stage = self.env["event.track.stage"].browse(vals["stage_id"])
            _debug.lifecycle(
                "track_stage_changed", tracks=self, stage=stage.id, name=stage.name
            )
            self._sync_with_stage(stage)
        return super().write(vals)

    def _sync_with_stage(self, stage):
        if stage.is_fully_accessible:
            _debug.lifecycle("track_published", by="stage", tracks=self)
            self.is_published = True
        elif stage.is_cancel:
            _debug.lifecycle("track_unpublished", by="stage_cancel", tracks=self)
            self.is_published = False

    @api.model
    def _search_get_detail(self, website, order, options):
        event_id = self.env["ir.http"]._unslug(options["event"])[1]
        domain = [
            "&",
            ("event_id", "=", event_id),
            "|",
            ("is_published", "=", True),
            ("stage_id.is_visible_in_agenda", "=", True),
        ]
        mapping = {
            "description": {
                "name": "description",
                "type": "text",
                "truncate": True,
                "html": True,
            },
            "name": {"name": "name", "type": "text", "match": True},
            "partner_name": {
                "name": "partner_name",
                "type": "text",
                "match": True,
                "html": True,
            },
            "website_url": {"name": "website_url", "type": "text", "truncate": False},
        }
        return {
            "model": "event.track",
            "base_domain": [domain],
            "search_fields": ["name", "partner_name"],
            "fetch_fields": ["name", "website_url", "partner_name", "description"],
            "mapping": mapping,
            "icon": "fa-microphone",
            "order": order,
        }

    def _mail_get_timezone(self):
        return self.event_id._mail_get_timezone() or super()._mail_get_timezone()

    def _message_get_default_recipients_sources(self):
        recipients = super()._message_get_default_recipients_sources()
        for track in self.filtered(
            lambda t: (
                not t.partner_id.email_normalized
                and not email_normalize(t.contact_email)
                and t.partner_email
            )
        ):
            info = recipients[track.id]
            info["email_to_lst"] = tools.mail.email_split_and_format_normalize(
                track.partner_email
            ) or [track.partner_email]
        return recipients

    def _message_post_after_hook(self, message, msg_vals):
        if msg_vals.get("partner_ids") and not self.partner_id:
            main_email = self.contact_email or self.partner_email
            main_email_normalized = tools.email_normalize(main_email)
            new_partner = message.partner_ids.filtered(
                lambda partner: (
                    partner.email == main_email
                    or (
                        main_email_normalized
                        and partner.email_normalized == main_email_normalized
                    )
                )
            )
            if new_partner:
                mail_email_fname = (
                    "contact_email" if self.contact_email else "partner_email"
                )
                if new_partner[0].email_normalized:
                    email_domain = (
                        mail_email_fname,
                        "in",
                        [new_partner[0].email, new_partner[0].email_normalized],
                    )
                else:
                    email_domain = (mail_email_fname, "=", new_partner[0].email)
                self.search(
                    [
                        ("partner_id", "=", False),
                        email_domain,
                        ("stage_id.is_cancel", "=", False),
                    ]
                ).write({"partner_id": new_partner[0].id})
        return super()._message_post_after_hook(message, msg_vals)

    def _track_template(self, changes):
        res = super()._track_template(changes)
        track = self[0]
        if "stage_id" in changes and track.stage_id.mail_template_id:
            res["stage_id"] = (
                track.stage_id.mail_template_id,
                {
                    "auto_delete_keep_log": False,
                    "composition_mode": "comment",
                    "email_layout_xmlid": "mail.mail_notification_light",
                    "subtype_id": self.env["ir.model.data"]._xmlid_to_res_id(
                        "mail.mt_note"
                    ),
                },
            )
        return res

    def _track_subtype(self, init_values):
        self.check_singleton()
        if "kanban_state" in init_values and self.kanban_state == "blocked":
            return self.env.ref("website_event_track.mt_track_blocked")
        elif "kanban_state" in init_values and self.kanban_state == "done":
            return self.env.ref("website_event_track.mt_track_ready")
        return super()._track_subtype(init_values)

    def open_track_speakers_list(self):
        return {
            "name": _("Speakers"),
            "domain": [("id", "in", self.mapped("partner_id").ids)],
            "view_mode": "kanban,form",
            "res_model": "res.partner",
            "view_id": False,
            "type": "ir.actions.act_window",
        }

    def get_backend_menu_id(self):
        return self.env.ref("event.event_main_menu").id

    def _get_event_track_visitors(self, force_create=False):
        self.check_singleton()

        force_visitor_create = self.env.user._is_public()
        visitor_sudo = self.env["website.visitor"]._get_visitor_from_request(
            force_create=force_visitor_create
        )
        if visitor_sudo:
            visitor_sudo._update_visitor_last_visit()

        if self.env.user._is_public():
            domain = [("visitor_id", "=", visitor_sudo.id)]
        elif visitor_sudo:
            domain = [
                "|",
                ("partner_id", "=", self.env.user.partner_id.id),
                ("visitor_id", "=", visitor_sudo.id),
            ]
        else:
            domain = [("partner_id", "=", self.env.user.partner_id.id)]

        track_visitors = (
            self.env["event.track.visitor"]
            .sudo()
            .search(Domain.AND([domain, [("track_id", "in", self.ids)]]))
        )
        missing = self - track_visitors.track_id
        if missing and force_create:
            track_visitors += (
                self.env["event.track.visitor"]
                .sudo()
                .create(
                    [
                        {
                            "visitor_id": visitor_sudo.id,
                            "partner_id": self.env.user.partner_id.id
                            if not self.env.user._is_public()
                            else False,
                            "track_id": track.id,
                        }
                        for track in missing
                    ]
                )
            )

        return track_visitors

    def _get_ics_file(self):
        result = dict.fromkeys(self.ids, False)
        if not vobject:
            return result

        for track in self:
            cal = vobject.iCalendar()
            cal_track = cal.add("vevent")

            date_tz = track.event_id.date_tz
            reminder_dates = track._get_track_calendar_reminder_dates()
            cal_track.add("created").value = fields.Datetime.now().replace(
                tzinfo=timezone("UTC")
            )
            cal_track.add("dtstart").value = reminder_dates["date_begin"].astimezone(
                timezone(date_tz)
            )
            cal_track.add("dtend").value = reminder_dates["date_end"].astimezone(
                timezone(date_tz)
            )
            cal_track.add("summary").value = track.name
            cal_track.add("description").value = track._get_track_calendar_description()
            if track.event_id.address_inline or track.location_id:
                cal_track.add("location").value = ", ".join(
                    [track.event_id.address_inline, track.location_id.sudo().name or ""]
                )

            result[track.id] = cal.serialize().encode("utf-8")
        return result

    def _get_track_suggestions(self, restrict_domain=None, limit=None):
        self.check_singleton()

        base_domain = [
            "&",
            ("event_id", "=", self.event_id.id),
            ("id", "!=", self.id),
        ]
        if restrict_domain:
            base_domain = Domain.AND([base_domain, restrict_domain])

        track_candidates = self.search(base_domain, limit=None, order="date asc")
        if not track_candidates:
            return track_candidates

        track_candidates = track_candidates.sorted(
            lambda track: (
                track.is_published,
                track.track_start_remaining == 0
                and track.track_start_relative < (10 * 60)
                and not track.is_track_done,
                track.track_start_remaining > 0,
                -1 * track.track_start_remaining,
                track.is_reminder_on,
                not track.wishlisted_by_default,
                len(track.tag_ids & self.tag_ids),
                track.location_id == self.location_id,
                randint(0, 20),
            ),
            reverse=True,
        )

        return track_candidates[:limit]

    def _get_track_calendar_description(self):
        self.check_singleton()
        return Markup(
            "<a href='%(event_track_url)s'>%(name)s</a>\n%(short_description)s\n\n%(reminder_times_warning)s"
        ) % {
            "event_track_url": tools.urls.urljoin(
                self.get_base_url(), self.website_url
            ),
            "name": self.name,
            "short_description": shorten(html_to_inner_content(self.description), 1900),
            "reminder_times_warning": self._get_track_calendar_reminder_times_warning(),
        }

    def _get_track_calendar_reminder_dates(self):
        return {
            "date_begin": self.date or self.event_id.date_begin,
            "date_end": self.date_end or self.event_id.date_end,
        }

    def _get_track_calendar_reminder_times_warning(self):
        return (
            Markup("<strong><u>%(warning_title)s</u></strong>: %(warning_content)s")
            % {
                "warning_title": _("Note"),
                "warning_content": _(
                    "The start and end times of the talk were not specified when you asked to add them to your calendar, "
                    "therefore the times indicated in this reminder correspond to those of the event."
                ),
            }
            if not self.date
            else ""
        )

    def _get_track_calendar_urls(self):
        date_tz = self.event_id.date_tz
        reminder_dates = self._get_track_calendar_reminder_dates()
        url_date_begin = (
            reminder_dates["date_begin"]
            .astimezone(timezone(date_tz))
            .strftime("%Y%m%dT%H%M%S")
        )
        url_date_end = (
            reminder_dates["date_end"]
            .astimezone(timezone(date_tz))
            .strftime("%Y%m%dT%H%M%S")
        )

        if self.event_id.address_inline or self.location_id:
            location = ", ".join(
                [
                    self.event_id.sudo().address_inline,
                    self.location_id.sudo().name or "",
                ]
            )
        else:
            location = ""

        google_params = {
            "action": "TEMPLATE",
            "text": f"{self.event_id.name}: {self.name}",
            "dates": f"{url_date_begin}/{url_date_end}",
            "ctz": self.event_id.date_tz,
            "details": self._get_track_calendar_description(),
            "location": location,
        }

        return {
            "google_url": GOOGLE_CALENDAR_URL + urlencode(google_params),
            "iCal_url": f"{self.get_base_url()}/event/{self.event_id.id}/track/{self.id}/ics",
        }
