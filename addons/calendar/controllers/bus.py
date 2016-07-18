# -*- coding: utf-8 -*
import openerp
from openerp.http import request


class CalendarBusController(openerp.addons.bus.controllers.main.BusController):
    def _get_channels(self, channels):
        if request.session.uid:
            channels.append((request.db, 'calendar.alarm', request.env.user.partner_id.id))
        return super(CalendarBusController, self)._get_channels(channels)
