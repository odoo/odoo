# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from werkzeug.exceptions import NotFound

from odoo import http
from odoo.http import request


class WebsiteJitsiController(http.Controller):

    @http.route(["/jitsi/update_status"], type="json", auth="public")
    def jitsi_update_status(self, room_name, participant_count, joined):
        """ Update room status: participant count, max reached

        Use the SQL keywords "FOR UPDATE SKIP LOCKED" in order to skip if the row
        is locked (instead of raising an exception, wait for a moment and retry).
        This endpoint may be called multiple times and we don't care having small
        errors in participant count compared to performance issues.

        :raise ValueError: wrong participant count
        :raise NotFound: wrong room name
        """
        if participant_count < 0:
            raise ValueError()

        chat_room = self._chat_room_exists(room_name)
        if not chat_room:
            raise NotFound()

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
                   last_activity = NOW(),
                   max_participant_reached = GREATEST(max_participant_reached, %s)
              FROM req
             WHERE wcr.id = req.id;
            """,
            [room_name, participant_count, participant_count]
        )

    @http.route(["/jitsi/is_full"], type="json", auth="public")
    def jitsi_is_full(self, room_name):
        return self._chat_room_exists(room_name).is_full

    # ------------------------------------------------------------
    # TOOLS
    # ------------------------------------------------------------

    def _chat_room_exists(self, room_name):
        return request.env["chat.room"].sudo().search([("name", "=", room_name)], limit=1)
