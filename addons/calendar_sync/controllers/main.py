# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import http
from odoo.http import request


class CalendarSyncController(http.Controller):

    @http.route('/calendar_sync/sync_calendars', type='json', auth='user')
    def sync_calendars(self, model, **kw):
        """
        This route is called to sync Odoo user's calendar with the external calendar service
        which has been configured and enabled in this Odoo instance for the current user.
        """
        syncer = request.env['calendar.syncer'].get_syncer()
        syncer.sudo().sync()
        return {}
