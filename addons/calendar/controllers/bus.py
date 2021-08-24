# -*- coding: utf-8 -*

from odoo.addons.bus.controllers.main import BusController
from odoo.http import request, route


class CalendarBusController(BusController):
    # --------------------------
    # Extends BUS Controller Poll/Subscribe
    # --------------------------
    def _poll(self, dbname, channels, last, options):
        if request.session.uid:
            channels = list(channels)
            channels.append((request.db, 'calendar.alarm', request.env.user.partner_id.id))
        return super(CalendarBusController, self)._poll(dbname, channels, last, options)

    @route('/subscribe', type="websocket")
    def subscribe(self, channels):
        if request.session.uid:
            channels.append((request.db, 'calendar.alarm', request.env.user.partner_id.id))
        return super().subscribe(channels)
