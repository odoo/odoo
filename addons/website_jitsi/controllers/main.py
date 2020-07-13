# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
from werkzeug.exceptions import Forbidden, NotFound

from odoo import http
from odoo.http import request


_logger = logging.getLogger(__name__)


class WebsiteJitsiController(http.Controller):
    @http.route(["/website_jitsi/update_participant_count"], type="json", auth="public")
    def update_participant_count(self, joined, participant_count, room_name):
        """Update the number of participant in the room.

        Use the SQL keywords "FOR UPDATE SKIP LOCKED" in order to do anything if the SQL
        row is locked (instead of raising an exception, wait for a moment and retry).
        As this endpoint can be called multiple times, and we do not care to have a small
        error in the participant count (but we care about performance).

        We need to provide the room name so it limit the rooms for which we can update
        the participant count (visitors can not update the participant count for
        unpublished rooms).
        """
        if participant_count < 0:
            raise Forbidden()

        self._chat_room_exists(room_name)

        request.env.cr.execute(
            """
            WITH req AS (
                SELECT id
                  FROM chat_room
                  -- Can not update the chat room if we do not have its name
                 WHERE name = %s
                   FOR UPDATE SKIP LOCKED
            )
            UPDATE chat_room AS wcr
               SET participant_count = %s,
                   last_joined = CASE WHEN %s THEN NOW() ELSE last_joined END,
                   last_activity = NOW(),
                   max_participant_reached = GREATEST(max_participant_reached, %s)
              FROM req
             WHERE wcr.id = req.id;
            """,
            [room_name, participant_count, joined, participant_count]
        )

    @http.route(["/website_jitsi/<string:room_name>/is_chat_room_full"], type="json", auth="public")
    def is_chat_room_full(self, room_name):
        """Return True is the given chat room is full."""
        chat_room = self._chat_room_exists(room_name)
        return chat_room.sudo().is_full

    def _chat_room_exists(self, room_name):
        """Return the Chat Room record or raise an exception if not found."""
        chat_room = request.env["chat.room"].sudo().search([("name", "=", room_name)], limit=1)

        if not chat_room:
            raise NotFound()

        return chat_room
