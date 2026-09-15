import base64
import operator
from ast import literal_eval
from collections import defaultdict
from datetime import UTC, timedelta

import babel.dates
from werkzeug.exceptions import Forbidden, NotFound

from odoo import Command, _, fields, http, tools
from odoo.fields import Domain
from odoo.http import prepare_content_disposition_header, request
from odoo.libs.datetime import timezone
from odoo.libs.debug_log import DebugLog
from odoo.tools import is_html_empty, plaintext2html
from odoo.tools.misc import babel_locale_parse

_debug = DebugLog(__name__)


class EventTrackController(http.Controller):
    def _get_domain_event_tracks_agenda(self, event):
        return [
            "&",
            ("event_id", "=", event.id),
            "|",
            ("is_published", "=", True),
            ("stage_id.is_visible_in_agenda", "=", True),
        ]

    def _get_domain_event_tracks(self, event):
        search_domain_base = self._get_domain_event_tracks_agenda(event)
        if not request.env.user.has_group("event.group_event_registration_desk"):
            search_domain_base = Domain.AND(
                [search_domain_base, [("is_published", "=", True)]]
            )
        return search_domain_base

    @http.route(
        [
            """/event/<model("event.event"):event>/track""",
            """/event/<model("event.event"):event>/track/tag/<model("event.track.tag"):tag>""",
        ],
        type="http",
        auth="public",
        website=True,
        sitemap=False,
        readonly=True,
    )
    def event_tracks(self, event, tag=None, **searches):

        if (
            searches.get("tags", "[]").count(",") > 0
            and request.httprequest.method == "GET"
            and not searches.get("prevent_redirect")
        ):
            slug = request.env["ir.http"]._slug
            return request.redirect(f"/event/{slug(event)}/track", code=301)
        seo_object = event.track_menu_ids.filtered(
            lambda menu: menu.menu_id.url.endswith("/track")
        )

        return request.render(
            "website_event_track.tracks_session",
            self._event_tracks_get_values(event, tag=tag, **searches)
            | {"seo_object": seo_object},
        )

    def _event_tracks_get_values(self, event, tag=None, **searches):
        searches.setdefault("search", "")
        searches.setdefault("search_wishlist", "")
        searches.setdefault("tags", "")
        search_domain = self._get_domain_event_tracks_agenda(event)

        if searches.get("search"):
            search_domain = Domain.AND(
                [
                    search_domain,
                    [
                        "|",
                        ("name", "ilike", searches["search"]),
                        ("partner_name", "ilike", searches["search"]),
                    ],
                ]
            )

        search_tags = self._get_search_tags(searches["tags"])
        if not search_tags and tag:
            search_tags = tag
        if search_tags:
            grouped_tags = {}
            for search_tag in search_tags:
                grouped_tags.setdefault(search_tag.category_id, []).append(search_tag)
            search_domain_items = [
                [("tag_ids", "in", [tag.id for tag in grouped_tags[group]])]
                for group in grouped_tags
            ]
            search_domain = Domain.AND([search_domain, *search_domain_items])

        now_tz = (
            fields.Datetime.now()
            .replace(microsecond=0)
            .replace(tzinfo=UTC)
            .astimezone(timezone(event.date_tz))
        )
        today_tz = now_tz.date()
        event = event.with_context(tz=event.date_tz or "UTC")
        tracks_sudo = (
            event.env["event.track"]
            .sudo()
            .search(search_domain, order="is_published desc, date asc")
        )
        tag_categories = request.env["event.track.tag.category"].sudo().search([])

        if searches.get("search_wishlist"):
            tracks_sudo = tracks_sudo.filtered(lambda track: track.is_reminder_on)

        tracks_announced = tracks_sudo.filtered(lambda track: not track.date)
        tracks_wdate = tracks_sudo - tracks_announced
        date_begin_tz_all = list(
            {
                dt.date()
                for dt in self._get_dt_in_event_tz(tracks_wdate.mapped("date"), event)
            }
        )
        date_begin_tz_all.sort()
        tracks_sudo_live = tracks_wdate.filtered(lambda track: track.is_track_live)
        tracks_sudo_soon = tracks_wdate.filtered(
            lambda track: not track.is_track_live and track.is_track_soon
        )
        tracks_by_day = []
        for display_date in date_begin_tz_all:
            matching_tracks = tracks_wdate.filtered(
                lambda track, display_date=display_date: (
                    self._get_dt_in_event_tz([track.date], event)[0].date()
                    == display_date
                )
            )
            tracks_by_day.append(
                {"date": display_date, "name": display_date, "tracks": matching_tracks}
            )
        if tracks_announced:
            tracks_announced = tracks_announced.sorted(
                "wishlisted_by_default", reverse=True
            )
            tracks_by_day.append(
                {"date": False, "name": _("Coming soon"), "tracks": tracks_announced}
            )
        has_upcoming_or_ongoing = any(
            track for track in tracks_sudo if not track.is_track_done
        )

        for tracks_group in tracks_by_day:
            tracks_group["default_collapsed"] = (
                has_upcoming_or_ongoing
                and tracks_group["date"]
                and all(track.is_track_done for track in tracks_group["tracks"])
            )

        return {
            "event": event,
            "main_object": event,
            "slots": event.event_slot_ids._filter_open_slots().grouped("date"),
            "tracks": tracks_sudo,
            "tracks_by_day": tracks_by_day,
            "tracks_live": tracks_sudo_live,
            "tracks_soon": tracks_sudo_soon,
            "today_tz": today_tz,
            "searches": searches,
            "search_count": len(tracks_sudo),
            "search_key": searches["search"],
            "search_wishlist": searches["search_wishlist"],
            "search_tags": search_tags,
            "tag_categories": tag_categories,
            "is_html_empty": is_html_empty,
            "hostname": request.httprequest.host.split(":")[0],
            "is_event_user": request.env.user.has_group("event.group_event_user"),
            "website_visitor_timezone": request.env[
                "website.visitor"
            ]._get_visitor_timezone(),
        }

    @http.route(
        ["""/event/<model("event.event"):event>/agenda"""],
        type="http",
        auth="public",
        website=True,
        sitemap=False,
    )
    def event_agenda(self, event, tag=None, **post):
        event = event.with_context(tz=event.date_tz or "UTC")
        seo_object = event.track_menu_ids.filtered(
            lambda menu: menu.menu_id.url.endswith("/agenda")
        )
        vals = {
            "event": event,
            "main_object": event,
            "seo_object": seo_object,
            "slots": event.event_slot_ids._filter_open_slots().grouped("date"),
            "tag": tag,
            "is_event_user": request.env.user.has_group("event.group_event_user"),
            "website_visitor_timezone": request.env[
                "website.visitor"
            ]._get_visitor_timezone(),
        }

        vals.update(self._prepare_calendar_values(event))

        return request.render("website_event_track.agenda_online", vals)

    def _prepare_calendar_values(self, event):
        event = event.with_context(tz=event.date_tz or "UTC")
        local_tz = timezone(event.date_tz or "UTC")
        lang_code = request.env.context.get("lang")

        base_track_domain = Domain.AND(
            [self._get_domain_event_tracks_agenda(event), [("date", "!=", False)]]
        )
        tracks_sudo = request.env["event.track"].sudo().search(base_track_domain)

        locations = list({track.location_id for track in tracks_sudo})
        locations.sort(key=operator.itemgetter("sequence", "id"))

        time_slots_by_tracks = {
            track: self._split_track_by_days(track, local_tz) for track in tracks_sudo
        }

        track_time_slots = set().union(
            *(time_slot.keys() for time_slot in list(time_slots_by_tracks.values()))
        )

        days = list({time_slot.date() for time_slot in track_time_slots})
        days.sort()

        tracks_by_days = dict.fromkeys(days, 0)
        time_slots_by_day = {day: {"start": set(), "end": set()} for day in days}
        tracks_by_rounded_times = {
            time_slot: {location: {} for location in locations}
            for time_slot in track_time_slots
        }
        for track, time_slots in time_slots_by_tracks.items():
            start_date = (
                fields.Datetime.from_string(track.date)
                .replace(tzinfo=UTC)
                .astimezone(local_tz)
            )
            end_date = start_date + timedelta(hours=(track.duration or 0.25))

            for time_slot, duration in time_slots.items():
                tracks_by_rounded_times[time_slot][track.location_id][track] = {
                    "rowspan": duration,
                    "start_date": self._get_locale_time(start_date, lang_code),
                    "end_date": self._get_locale_time(end_date, lang_code),
                    "occupied_cells": self._get_occupied_cells(
                        track, duration, locations, local_tz
                    ),
                }

                day = time_slot.date()
                time_slots_by_day[day]["start"].add(time_slot)
                time_slots_by_day[day]["end"].add(
                    time_slot + timedelta(minutes=15 * duration)
                )
                tracks_by_days[day] += 1

        global_time_slots_by_day = {day: {} for day in days}
        for day, time_slots in time_slots_by_day.items():
            start_time_slot = min(time_slots["start"])
            end_time_slot = max(time_slots["end"])

            time_slots_count = int(
                ((end_time_slot - start_time_slot).total_seconds() / 3600) * 4
            )
            current_time_slot = start_time_slot
            for _i in range(time_slots_count + 1):
                global_time_slots_by_day[day][current_time_slot] = (
                    tracks_by_rounded_times.get(current_time_slot, {})
                )
                global_time_slots_by_day[day][current_time_slot]["formatted_time"] = (
                    self._get_locale_time(current_time_slot, lang_code)
                )
                current_time_slot += timedelta(minutes=15)

        tracks_by_days = dict.fromkeys(days, 0)
        locations_by_days = defaultdict(list)
        for track in tracks_sudo:
            track_day = (
                fields.Datetime.from_string(track.date)
                .replace(tzinfo=UTC)
                .astimezone(local_tz)
                .date()
            )
            tracks_by_days[track_day] += 1
            if track.location_id not in locations_by_days[track_day]:
                locations_by_days[track_day].append(track.location_id)

        for used_locations in locations_by_days.values():
            used_locations.sort(key=operator.itemgetter("sequence", "id"))

        return {
            "days": days,
            "tracks_by_days": tracks_by_days,
            "locations_by_days": locations_by_days,
            "time_slots": global_time_slots_by_day,
            "locations": locations,
        }

    def _get_locale_time(self, dt_time, lang_code):
        locale = babel_locale_parse(lang_code)
        return babel.dates.format_time(dt_time, format="short", locale=locale)

    def time_slot_rounder(self, time, rounded_minutes):
        return time.replace(
            second=0, microsecond=0, minute=0, hour=time.hour
        ) + timedelta(minutes=rounded_minutes * (time.minute // rounded_minutes))

    def _split_track_by_days(self, track, local_tz):
        start_date = (
            fields.Datetime.from_string(track.date)
            .replace(tzinfo=UTC)
            .astimezone(local_tz)
        )
        start_datetime = self.time_slot_rounder(start_date, 15)
        end_datetime = self.time_slot_rounder(
            start_datetime + timedelta(hours=(track.duration or 0.25)), 15
        )
        time_slots_count = int(
            ((end_datetime - start_datetime).total_seconds() / 3600) * 4
        )

        time_slots_by_day_start_time = {start_datetime: 0}
        for i in range(time_slots_count):
            next_day = (start_datetime + timedelta(days=1)).date()
            if (start_datetime + timedelta(minutes=15 * i)).date() <= next_day:
                time_slots_by_day_start_time[start_datetime] += 1
            else:
                start_datetime = next_day.datetime()
                time_slots_by_day_start_time[start_datetime] = 0

        return time_slots_by_day_start_time

    def _get_occupied_cells(self, track, rowspan, locations, local_tz):
        occupied_cells = []

        start_date = (
            fields.Datetime.from_string(track.date)
            .replace(tzinfo=UTC)
            .astimezone(local_tz)
        )
        start_date = self.time_slot_rounder(start_date, 15)
        for i in range(rowspan):
            time_slot = start_date + timedelta(minutes=15 * i)
            if track.location_id:
                occupied_cells.append((time_slot, track.location_id))
            else:
                occupied_cells += [
                    (time_slot, location) for location in locations if location
                ]

        return occupied_cells

    @http.route(
        """/event/<model("event.event", "[('website_track', '=', True)]"):event>/track/<model("event.track", "[('event_id', '=', event.id)]"):track>""",
        type="http",
        auth="public",
        website=True,
        sitemap=True,
        readonly=True,
    )
    def event_track_page(self, event, track, **options):
        track = self._get_track(track.id, allow_sudo=False)

        return request.render(
            "website_event_track.event_track_main",
            self._event_track_page_get_values(event, track.sudo(), **options),
        )

    def _event_track_page_get_values(self, event, track, **options):
        track = track.sudo()

        option_widescreen = options.get("widescreen", False)
        option_widescreen = (
            bool(option_widescreen) if option_widescreen != "0" else False
        )
        tracks_other = track._get_track_suggestions(
            restrict_domain=self._get_domain_event_tracks(track.event_id), limit=10
        )

        return {
            "event": event,
            "main_object": track,
            "slots": event.event_slot_ids._filter_open_slots().grouped("date"),
            "track": track,
            "tracks_other": tracks_other,
            "option_widescreen": option_widescreen,
            "is_html_empty": is_html_empty,
            "hostname": request.httprequest.host.split(":")[0],
            "is_event_user": request.env.user.has_group("event.group_event_user"),
            "user_event_manager": request.env.user.has_group(
                "event.group_event_manager"
            ),
            "website_visitor_timezone": request.env[
                "website.visitor"
            ]._get_visitor_timezone(),
        }

    @http.route(
        "/event/track/toggle_reminder", type="jsonrpc", auth="public", website=True
    )
    def track_reminder_toggle(self, track_id, set_reminder_on):
        track = self._get_track(track_id, allow_sudo=True)
        force_create = set_reminder_on or track.wishlisted_by_default
        event_track_partner = track._get_event_track_visitors(force_create=force_create)

        if not track.wishlisted_by_default:
            if (
                not event_track_partner
                or event_track_partner.is_wishlisted == set_reminder_on
            ):
                return {"error": "ignored"}
            event_track_partner.is_wishlisted = set_reminder_on
        else:
            if (
                not event_track_partner
                or event_track_partner.is_blacklisted != set_reminder_on
            ):
                return {"error": "ignored"}
            event_track_partner.is_blacklisted = not set_reminder_on

        return {"reminderOn": set_reminder_on}

    @http.route(
        "/event/track/send_email_reminder", type="jsonrpc", auth="public", website=True
    )
    def send_email_reminder(self, track_id, email_to):
        template = self.env.ref(
            "website_event_track.mail_template_data_track_reminder",
            raise_if_not_found=False,
        )
        if not template:
            return {"success": False, "error": "missing_template"}

        track_su = self.env["event.track"].sudo().browse(track_id)
        track = track_su.filtered_domain(
            self._get_domain_event_tracks(track_su.event_id)
        )
        valid_email_to = tools.email_normalize(
            email_to if request.env.user._is_public() else request.env.user.email
        )
        error_message = ""
        if not track:
            error_message = _("Invalid data.")
        elif not valid_email_to:
            error_message = _("Invalid email.")
        elif track.is_track_done or track.event_id.is_finished:
            error_message = _("The talk is already finished.")
        elif not track.is_track_upcoming:
            error_message = _("The talk has already begun.")
        if error_message:
            return {"success": False, "message": error_message}

        template.sudo().with_context(
            lang=request.cookies.get("frontend_lang")
            if request.env.user._is_public()
            else request.env.context.get("lang", request.env.user.lang)
        ).send_mail(track.id, email_values={"email_to": valid_email_to})
        return {"success": True}

    @http.route(
        ["""/event/<model("event.event"):event>/track_proposal"""],
        type="http",
        auth="public",
        website=True,
        sitemap=False,
    )
    def event_track_proposal(self, event, **post):
        return request.render(
            "website_event_track.event_track_proposal",
            {
                "event": event,
                "main_object": event,
                "seo_object": event.track_proposal_menu_ids,
                "slots": event.event_slot_ids._filter_open_slots().grouped("date"),
            },
        )

    @http.route(
        ["""/event/<model("event.event"):event>/track_proposal/post"""],
        type="http",
        auth="public",
        methods=["POST"],
        website=True,
    )
    def event_track_proposal_post(self, event, **post):
        if not event.can_access_from_current_website():
            return request.prepare_json_response({"error": "forbidden"})

        input_tag_indices = [
            int(tag_id) for tag_id in post["tags"].split(",") if tag_id
        ]
        valid_tag_indices = (
            request.env["event.track.tag"].search([("id", "in", input_tag_indices)]).ids
        )

        contact = request.env["res.partner"]
        visitor_partner = (
            request.env["website.visitor"]._get_visitor_from_request().partner_id
        )
        if post.get("add_contact_information"):
            valid_contact_email = tools.email_normalize(post.get("contact_email"))
            if valid_contact_email or post.get("contact_phone"):
                if (
                    visitor_partner
                    and valid_contact_email == visitor_partner.email_normalized
                ):
                    contact = visitor_partner
                else:
                    contact = (
                        request.env["res.partner"]
                        .sudo()
                        .create(
                            {
                                "email": valid_contact_email,
                                "name": post.get("contact_name"),
                                "phone_ids": [
                                    Command.create(
                                        {
                                            "number": post["contact_phone"],
                                            "type": "landline",
                                        }
                                    )
                                ]
                                if post.get("contact_phone")
                                else [],
                            }
                        )
                    )
            else:
                return request.prepare_json_response({"error": "invalidFormInputs"})
        else:
            valid_speaker_email = tools.email_normalize(post["partner_email"])
            if (
                visitor_partner
                and valid_speaker_email == visitor_partner.email_normalized
            ):
                contact = visitor_partner

        track = (
            request.env["event.track"]
            .with_context({"mail_create_nosubscribe": True})
            .sudo()
            .create(
                {
                    "name": post["track_name"],
                    "partner_id": contact.id,
                    "partner_name": post["partner_name"],
                    "partner_email": post["partner_email"],
                    "phone_ids": [
                        Command.create(
                            {"number": post["partner_phone"], "type": "landline"}
                        )
                    ]
                    if post.get("partner_phone")
                    else [],
                    "partner_function": post["partner_function"],
                    "contact_phone_ids": [
                        Command.set(contact.phone_ids._primary().ids)
                    ],
                    "contact_email": contact.email,
                    "event_id": event.id,
                    "tag_ids": [(6, 0, valid_tag_indices)],
                    "description": plaintext2html(post["description"]),
                    "partner_biography": plaintext2html(post["partner_biography"]),
                    "user_id": False,
                    "image": base64.b64encode(post["image"].read())
                    if post.get("image")
                    else False,
                }
            )
        )

        if request.env.user != request.website.user_id:
            track.sudo().message_subscribe(partner_ids=request.env.user.partner_id.ids)

        return request.prepare_json_response({"success": True})

    @http.route(
        ["""/event/track_tag/search_read"""],
        type="jsonrpc",
        auth="public",
        website=True,
    )
    def website_event_track_fetch_tags(self, domain, fields):
        return request.env["event.track.tag"].search_read(domain, fields)

    @http.route(
        [
            """/event/<model("event.event"):event>/track/<model("event.track"):track>/ics"""
        ],
        type="http",
        auth="public",
    )
    def event_track_ics_file(self, event, track):
        lang = request.env.context.get("lang", request.env.user.lang)
        if request.env.user._is_public():
            lang = request.cookies.get("frontend_lang")
        track = track.with_context(lang=lang)
        files = track._get_ics_file()
        content = files.get(track.id)
        if not content:
            return NotFound()
        return request.prepare_response(
            content,
            [
                ("Content-Type", "application/octet-stream"),
                ("Content-Length", len(content)),
                (
                    "Content-Disposition",
                    prepare_content_disposition_header(
                        f"{event.name}-{track.name}.ics"
                    ),
                ),
            ],
        )

    def _get_track(self, track_id, allow_sudo=False):
        track = request.env["event.track"].browse(track_id).exists()
        if not track:
            _debug.logic("track_refused", reason="missing", track=track_id)
            raise NotFound
        if not track.has_access("read"):
            if not allow_sudo:
                _debug.logic("track_refused", reason="no_read", track=track_id)
                raise Forbidden
            _debug.logic("track_access", by="sudo", track=track_id)
            track = track.sudo()

        event = track.event_id
        if (
            hasattr(request, "website_id")
            and not event.can_access_from_current_website()
        ):
            _debug.logic("track_refused", reason="other_website", track=track_id)
            raise NotFound
        if not event.has_access("read"):
            _debug.logic("track_refused", reason="event_no_read", event=event.id)
            raise Forbidden

        return track

    def _get_search_tags(self, tag_search):
        try:
            tag_ids = literal_eval(tag_search)
        except Exception:
            tags = request.env["event.track.tag"].sudo()
        else:
            tags = request.env["event.track.tag"].sudo().search([("id", "in", tag_ids)])
        return tags

    def _get_dt_in_event_tz(self, datetimes, event):
        tz_name = event.date_tz
        return [
            dt.replace(tzinfo=UTC).astimezone(timezone(tz_name)) for dt in datetimes
        ]
