# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
from werkzeug.exceptions import Forbidden
from werkzeug.utils import redirect

from odoo import http
from odoo.http import request
from odoo.addons.http_routing.models.ir_http import slug


_logger = logging.getLogger(__name__)


class WebsiteEventMeetController(http.Controller):
    @http.route(["/event/<model('event.event'):event>/meeting_rooms"], type="http",
                auth="public", website=True, sitemap=True)
    def event_meeting_rooms(self, event, lang=None, open_room_id=None):
        """Display the meeting rooms of the event on the frontend side.

        :param event: Event for which we display the meeting rooms
        :param lang: lang id used to perform a search
        :param open_room_id: automatically open the meeting room given
        """
        if not event.can_access_from_current_website():
            raise Forbidden()

        meeting_rooms = event.sudo().meeting_room_ids.filtered(lambda m: m.room_active)
        meeting_rooms = meeting_rooms.sorted(lambda m: (m.is_pinned, m.room_last_joined, m.id), reverse=True)

        if lang is not None:
            lang = request.env["res.lang"].browse(int(lang))
            meeting_rooms = meeting_rooms.filtered(lambda m: m.room_lang_id == lang)

        values = {
            "event": event.sudo(),
            "meeting_rooms": meeting_rooms,
            "current_lang": lang,
            "available_languages": event.sudo().meeting_room_ids.mapped("room_lang_id"),
            "open_room_id": int(open_room_id) if open_room_id else None,
            "is_event_manager": request.env.user.has_group("event.group_event_manager"),
            "default_lang_code": request.env.user.lang,
        }

        return request.render("website_event_meet.template_meeting_rooms", values)

    @http.route(["/event/create_meeting_room"], type="http", auth="public", methods=["POST"], website=True)
    def create_meeting_room(self, **post):
        name = post.get("name")
        summary = post.get("summary")
        target_audience = post.get("audience")
        lang_code = post.get("lang_code")
        max_capacity = post.get("capacity")
        event_id = int(post.get("event"))

        # get the record to be sure they really exist
        event = request.env["event.event"].browse(event_id).exists()
        lang = request.env["res.lang"].search([("code", "=", lang_code)], limit=1)

        if not event or not event.can_access_from_current_website():
            raise Forbidden()

        if not event.website_published or not lang or max_capacity == "no_limit":
            raise Forbidden()

        _logger.info("New meeting room (%s) create by %s" % (name, request.httprequest.remote_addr))

        meeting_room = request.env["event.meeting.room"].sudo().create(
            {
                "name": name,
                "summary": summary,
                "target_audience": target_audience,
                "is_pinned": False,
                "event_id": event.id,
                "room_lang_id": lang.id,
                "room_max_capacity": max_capacity,
            },
        )

        return redirect("/event/%s/meeting_rooms?open_room_id=%i" % (slug(event), meeting_room.id))

    @http.route(["/event/active_langs"], type="json", auth="public")
    def active_langs(self):
        return request.env["res.lang"].sudo().get_installed()
