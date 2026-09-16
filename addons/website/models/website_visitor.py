import hashlib
import logging
from collections.abc import Collection
from datetime import datetime, timedelta

from odoo import api, fields, models
from odoo.exceptions import UserError
from odoo.fields import Domain
from odoo.http import request
from odoo.libs.datetime import all_timezones
from odoo.libs.debug_log import DebugLog
from odoo.tools import SQL, _
from odoo.tools.misc import _format_time_ago

from odoo.addons.base.models.res_partner import _selection_timezones

_logger = logging.getLogger(__name__)
_debug = DebugLog(__name__)


class WebsiteTrack(models.Model):
    _name = "website.track"
    _description = "Visited Pages"
    _order = "visit_datetime DESC, id DESC"
    _log_access = False

    visitor_id = fields.Many2one(
        comodel_name="website.visitor",
        index=True,
        readonly=True,
        required=True,
        ondelete="cascade",
    )
    page_id = fields.Many2one(
        comodel_name="website.page",
        index=True,
        readonly=True,
        ondelete="cascade",
    )
    url = fields.Text(index=True)
    visit_datetime = fields.Datetime(
        string="Visit Date",
        default=fields.Datetime.now,
        readonly=True,
        required=True,
    )

    _visitor_id_visit_datetime_idx = models.Index("(visitor_id, visit_datetime)")


class WebsiteVisitor(models.Model):
    _name = "website.visitor"
    _description = "Website Visitor"
    _order = "id DESC"

    def _default_access_token(self):
        return self._get_access_token()

    def _get_access_token(self):
        if not request:
            _debug.logic("visitor_token_refused", reason="no_request")
            raise ValueError("Visitors can only be created through the frontend.")

        if not request.env.user._is_public():
            return request.env.user.partner_id.id

        msg = repr(
            (
                request.httprequest.remote_addr,
                request.httprequest.environ.get("HTTP_USER_AGENT"),
                request.session.sid,
            )
        ).encode("utf-8")
        return hashlib.sha1(msg).hexdigest()[:32]

    name = fields.Char(
        related="partner_id.name",
        string="Name",
    )
    access_token = fields.Char(
        default=_default_access_token,
        copy=False,
        required=True,
    )
    website_id = fields.Many2one(
        comodel_name="website",
        readonly=True,
    )
    partner_id = fields.Many2one(
        comodel_name="res.partner",
        string="Contact",
        compute="_compute_partner_id",
        store=True,
        index="btree_not_null",
        help="Partner of the last logged in user.",
    )
    partner_image = fields.Binary(related="partner_id.image_1920")

    country_id = fields.Many2one(
        comodel_name="res.country",
        readonly=True,
    )
    country_flag = fields.Char(
        related="country_id.image_url",
        string="Country Flag",
    )
    lang_id = fields.Many2one(
        comodel_name="res.lang",
        string="Language",
        help="Language from the website when visitor has been created",
    )
    timezone = fields.Selection(selection=_selection_timezones)
    email = fields.Char(
        compute="_compute_email_phone",
        compute_sudo=True,
    )
    mobile = fields.Char(
        compute="_compute_email_phone",
        compute_sudo=True,
    )

    visit_count = fields.Integer(
        string="# Visits",
        default=1,
        readonly=True,
        help="A new visit is considered if last connection was more than 8 hours ago.",
    )
    website_track_ids = fields.One2many(
        comodel_name="website.track",
        inverse_name="visitor_id",
        string="Visited Pages History",
        readonly=True,
    )
    visitor_page_count = fields.Integer(
        string="Page Views",
        compute="_compute_page_statistics",
        help="Total number of visits on tracked pages",
    )
    page_ids = fields.Many2many(
        comodel_name="website.page",
        string="Visited Pages",
        compute="_compute_page_statistics",
        search="_search_page_ids",
        groups="website.group_website_designer",
    )
    page_count = fields.Integer(
        string="# Visited Pages",
        compute="_compute_page_statistics",
        help="Total number of tracked page visited",
    )
    last_visited_page_id = fields.Many2one(
        comodel_name="website.page",
        compute="_compute_last_visited_page_id",
    )

    create_date = fields.Datetime(
        string="First Connection",
        readonly=True,
    )
    last_connection_datetime = fields.Datetime(
        string="Last Connection",
        default=fields.Datetime.now,
        readonly=True,
        help="Last page view date",
    )
    time_since_last_action = fields.Char(
        string="Last action",
        compute="_compute_time_statistics",
        help="Time since last page view. E.g.: 2 minutes ago",
    )
    is_connected = fields.Boolean(
        string="Is connected?",
        compute="_compute_time_statistics",
        help="A visitor is considered as connected if his last page view was within the last 5 minutes.",
    )

    _access_token_unique = models.Constraint(
        "unique(access_token)",
        "Access token should be unique.",
    )

    @api.depends("partner_id")
    def _compute_display_name(self):
        for record in self:
            record.display_name = record.partner_id.sudo().name or _(
                "Website Visitor #%s", record.id
            )

    @api.depends("access_token")
    def _compute_partner_id(self):
        for visitor in self:
            if not visitor.id:
                visitor.partner_id = visitor._origin.partner_id
                continue
            token = visitor.access_token or ""
            partner_id = int(token) if len(token) != 32 and token.isdigit() else False
            visitor.partner_id = self.env["res.partner"].browse(partner_id)

    @api.depends("partner_id.email_normalized", "partner_id.phone_ids")
    def _compute_email_phone(self):
        for visitor in self:
            partner = visitor.partner_id
            visitor.email = partner.email_normalized
            visitor.mobile = partner._phone_get_number().number if partner else False

    @api.depends("website_track_ids.page_id", "website_track_ids.url")
    def _compute_page_statistics(self):
        results = self.env["website.track"]._read_group(
            [("visitor_id", "in", self.ids), ("url", "!=", False)],
            ["visitor_id", "page_id"],
            ["__count"],
        )
        mapped_data = {}
        for visitor, page, count in results:
            visitor_info = mapped_data.get(
                visitor.id,
                {"page_count": 0, "visitor_page_count": 0, "page_ids": set()},
            )
            visitor_info["visitor_page_count"] += count
            if page:
                visitor_info["page_count"] += 1
                visitor_info["page_ids"].add(page.id)
            mapped_data[visitor.id] = visitor_info

        for visitor in self:
            visitor_info = mapped_data.get(
                visitor.id,
                {"page_count": 0, "visitor_page_count": 0, "page_ids": set()},
            )
            visitor.sudo().page_ids = [(6, 0, visitor_info["page_ids"])]
            visitor.visitor_page_count = visitor_info["visitor_page_count"]
            visitor.page_count = visitor_info["page_count"]

    def _search_page_ids(self, operator, value):
        negative = operator in Domain.NEGATIVE_OPERATORS
        operator = Domain.NEGATIVE_OPERATORS.get(operator, operator)
        tracked_pages = Domain("url", "!=", False) & Domain("page_id", "!=", False)
        result = Domain(
            "website_track_ids",
            "any",
            tracked_pages & Domain("page_id", operator, value),
        )
        if (operator == "=" and value is False) or (
            operator == "in" and isinstance(value, Collection) and False in value
        ):
            result |= Domain("website_track_ids", "not any", tracked_pages)
        return ~result if negative else result

    @api.depends("website_track_ids.page_id", "website_track_ids.visit_datetime")
    def _compute_last_visited_page_id(self):
        tracks = self.env["website.track"]
        query = tracks._search(
            [("visitor_id", "in", self.ids), ("page_id", "!=", False)]
        )
        visitor_id, page_id, visited_at, track_id = (
            tracks._field_to_sql(tracks._table, name, query)
            for name in ("visitor_id", "page_id", "visit_datetime", "id")
        )
        query.order = SQL("%s, %s DESC, %s DESC", visitor_id, visited_at, track_id)
        mapped_data = dict(
            self.env.execute_query(
                query.select(
                    SQL("DISTINCT ON (%s) %s, %s", visitor_id, visitor_id, page_id)
                )
            )
        )
        for visitor in self:
            visitor.last_visited_page_id = mapped_data.get(visitor.id, False)

    @api.depends("last_connection_datetime")
    def _compute_time_statistics(self):
        now = datetime.now()
        for visitor in self:
            if not visitor.last_connection_datetime:
                visitor.time_since_last_action = False
                visitor.is_connected = False
                continue
            elapsed = now - visitor.last_connection_datetime
            visitor.time_since_last_action = _format_time_ago(self.env, elapsed)
            visitor.is_connected = elapsed < timedelta(minutes=5)

    def _check_for_message_composer(self):
        return bool(self.partner_id and self.partner_id.email)

    def _prepare_message_composer_context(self):
        return {
            "default_model": "res.partner",
            "default_res_ids": self.partner_id.ids,
            "default_partner_ids": [self.partner_id.id],
        }

    def action_send_mail(self):
        self.check_singleton()
        if not self._check_for_message_composer():
            raise UserError(
                _("There are no contact and/or no email linked to this visitor.")
            )
        visitor_composer_ctx = self._prepare_message_composer_context()
        compose_form = self.env.ref("mail.email_compose_message_wizard_form", False)
        compose_ctx = {
            "default_composition_mode": "comment",
        }
        compose_ctx.update(**visitor_composer_ctx)
        return {
            "name": _("Contact Visitor"),
            "type": "ir.actions.act_window",
            "view_mode": "form",
            "res_model": "mail.compose.message",
            "views": [(compose_form.id, "form")],
            "view_id": compose_form.id,
            "target": "new",
            "context": compose_ctx,
        }

    def _get_upsert_values(
        self, access_token, *, lang_id, country_code, website_id, timezone
    ):
        return {
            "access_token": str(access_token),
            "lang_id": (request.lang.id if lang_id is None else lang_id) or None,
            "country_code": (
                request.geoip.get("country_code")
                if country_code is None
                else country_code
            )
            or None,
            "website_id": (request.website.id if website_id is None else website_id)
            or None,
            "timezone": (self._get_visitor_timezone() if timezone is None else timezone)
            or None,
            "write_uid": self.env.uid,
            "create_uid": self.env.uid,
            "partner_id": None if len(str(access_token)) == 32 else access_token,
        }

    def _upsert_visitor(
        self,
        access_token,
        force_track_values=None,
        *,
        lang_id=None,
        country_code=None,
        website_id=None,
        timezone=None,
    ):
        updated_fields = ["last_connection_datetime", "visit_count", "timezone"]
        self.flush_model(["access_token", *updated_fields])
        create_values = self._get_upsert_values(
            access_token,
            lang_id=lang_id,
            country_code=country_code,
            website_id=website_id,
            timezone=timezone,
        )
        query = SQL(
            """
            INSERT INTO website_visitor (
                partner_id, access_token, last_connection_datetime, visit_count, lang_id,
                website_id, timezone, write_uid, create_uid, write_date, create_date, country_id)
            VALUES (
                %(partner_id)s::integer, %(access_token)s, now() at time zone 'UTC', 1, %(lang_id)s,
                %(website_id)s, %(timezone)s, %(write_uid)s, %(create_uid)s,
                now() at time zone 'UTC', now() at time zone 'UTC',
                (SELECT id FROM res_country WHERE code = %(country_code)s))
            ON CONFLICT (access_token) DO UPDATE SET
                last_connection_datetime = now() at time zone 'UTC',
                -- Back-fill the timezone once it becomes available: the tracked
                -- page path always force-creates and so never reaches the
                -- non-force back-fill branch, leaving a visitor first seen
                -- without a tz cookie stuck at NULL for life otherwise.
                timezone = COALESCE(website_visitor.timezone, EXCLUDED.timezone),
                visit_count = CASE WHEN website_visitor.last_connection_datetime < NOW() AT TIME ZONE 'UTC' - INTERVAL '8 hours'
                                    THEN website_visitor.visit_count + 1
                                    ELSE website_visitor.visit_count
                                END
            RETURNING id, (xmax = 0) AS upsert
        """,
            **create_values,
        )

        if force_track_values:
            query = SQL(
                """
                WITH visitor AS (
                    %(query)s, %(url)s AS url, %(page_id)s AS page_id
                ), track AS (
                    INSERT INTO website_track (visitor_id, url, page_id, visit_datetime)
                    SELECT id, url, page_id::integer, now() at time zone 'UTC' FROM visitor
                )
                SELECT id, upsert from visitor;
                """,
                query=query,
                url=force_track_values["url"],
                page_id=force_track_values.get("page_id"),
            )

        tracked = bool(force_track_values)
        with _debug.perf("visitor_upsert", cr=self.env.cr, tracked=tracked) as span:
            [result] = self.env.execute_query(query)
            span.set(visitor=result[0], created=result[1])
        visitor = self.browse(result[0])
        if force_track_values:
            updated_fields.append("website_track_ids")
        visitor.invalidate_recordset(updated_fields)
        visitor.modified(updated_fields)
        if result[1] and create_values["partner_id"]:
            partner = self.env["res.partner"].browse(int(create_values["partner_id"]))
            partner.invalidate_recordset(["visitor_ids"])
            partner.modified(["visitor_ids"])
        _logger.debug(
            "Visitor upsert id=%s created=%s tracked=%s", result[0], result[1], tracked
        )
        _debug.lifecycle(
            "visitor_upsert",
            visitor=result[0],
            created=result[1],
            tracked=tracked,
            partner=create_values["partner_id"],
        )
        return result

    def _get_visitor_from_request(self, force_create=False, force_track_values=None):
        if not (request and request.env and request.env.uid):
            _debug.logic("visitor_skipped", reason="no_request_env")
            return None

        access_token = self._get_access_token()

        if force_create:
            visitor_id, _created = self._upsert_visitor(
                access_token, force_track_values
            )
            return self.env["website.visitor"].sudo().browse(visitor_id)

        visitor = (
            self.env["website.visitor"]
            .sudo()
            .search_fetch([("access_token", "=", access_token)])
        )

        if not self.env.cr.readonly and visitor and not visitor.timezone:
            tz = self._get_visitor_timezone()
            if tz:
                _debug.lifecycle(
                    "visitor_timezone_backfilled", visitor=visitor.id, tz=tz
                )
                visitor._update_visitor_timezone(tz)

        _debug.logic(
            "visitor_from_request", by="lookup", visitor=visitor.id, found=bool(visitor)
        )
        return visitor

    def _handle_webpage_dispatch(self, website_page):
        url = request.httprequest.url
        website_track_values = {"url": url}
        if website_page:
            website_track_values["page_id"] = website_page.id
        _debug.pipeline("webpage_dispatch_tracked", page=website_page or None, url=url)

        self._get_visitor_from_request(
            force_create=True, force_track_values=website_track_values
        )

    def _add_tracking(self, domain, website_track_values):
        self.check_singleton()
        domain = Domain.AND([domain, Domain("visitor_id", "=", self.id)])
        last_view = self.env["website.track"].sudo().search(domain, limit=1)
        recorded = (
            not last_view
            or last_view.visit_datetime < datetime.now() - timedelta(minutes=30)
        )
        # Logged before the branch, with the inputs, so one site answers both
        # outcomes. Logging only the taken side made "this page view was not
        # counted" -- an ordinary complaint about visitor analytics --
        # indistinguishable from "_add_tracking was never called".
        _debug.lifecycle(
            "visitor_track",
            visitor=self.id,
            recorded=recorded,
            by="new" if not last_view else ("stale" if recorded else "within_window"),
            last_seen=last_view.visit_datetime or None,
        )
        if recorded:
            self.env["website.track"].create(
                {**website_track_values, "visitor_id": self.id}
            )
        self._update_visitor_last_visit()

    def _merge_visitor(self, target):
        if not target.partner_id:
            _debug.logic("visitor_merge_refused", reason="target_has_no_partner")
            raise ValueError("The `target` visitor should be linked to a partner.")
        _debug.lifecycle(
            "visitor_merged",
            visitor=self.id,
            target=target.id,
            tracks=len(self.website_track_ids),
        )
        self.website_track_ids.visitor_id = target.id
        self.unlink()

    def _cron_unlink_old_visitors(self, batch_size=1000):
        domain = self._get_domain_inactive_visitors()
        visitors = self.env["website.visitor"].sudo().search(domain, limit=batch_size)
        _debug.pipeline("gc_visitors", batch=batch_size, removed=len(visitors))
        visitors.unlink()
        self.env["ir.cron"]._commit_progress(
            processed=len(visitors),
            remaining=0
            if len(visitors) < batch_size
            else visitors.search_count(domain),
        )

    def _get_domain_inactive_visitors(self):
        delay_days = int(
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("website.visitor.live.days", 60)
        )
        deadline = datetime.now() - timedelta(days=delay_days)
        return Domain("last_connection_datetime", "<", deadline) & Domain(
            "partner_id", "=", False
        )

    def _update_visitor_timezone(self, timezone):
        self.check_singleton()
        self.flush_recordset(["timezone"])
        query = """
            UPDATE website_visitor
            SET timezone = %s
            WHERE id IN (
                SELECT id FROM website_visitor WHERE id = %s
                FOR NO KEY UPDATE SKIP LOCKED
            )
        """
        _debug.lifecycle("visitor_timezone_set", visitor=self.id, tz=timezone)
        self.env.cr.execute(query, (timezone, self.id))
        self.invalidate_recordset(["timezone"])
        self.modified(["timezone"])

    def _update_visitor_last_visit(self):
        self.check_singleton()
        updated_fields = ["visit_count", "last_connection_datetime"]
        self.flush_recordset(updated_fields)
        query = """
            UPDATE website_visitor
               SET visit_count = CASE
                       WHEN last_connection_datetime < (now() at time zone 'UTC') - INTERVAL '8 hours'
                       THEN visit_count + 1
                       ELSE visit_count
                   END,
                   last_connection_datetime = now() at time zone 'UTC'
             WHERE id IN (
                   SELECT id FROM website_visitor WHERE id = %s
                   FOR NO KEY UPDATE SKIP LOCKED
             )
        """
        self.env.cr.execute(query, (self.id,), log_exceptions=False)
        self.invalidate_recordset(updated_fields)
        self.modified(updated_fields)
        _logger.debug("Visitor last visit refreshed id=%s", self.id)

    def _get_visitor_timezone(self):
        tz = request.cookies.get("tz") if request else None
        if tz in all_timezones():
            _debug.logic("visitor_timezone", by="cookie", tz=tz)
            return tz
        elif not self.env.user._is_public():
            _debug.logic("visitor_timezone", by="user", tz=self.env.user.tz)
            return self.env.user.tz
        else:
            return None
