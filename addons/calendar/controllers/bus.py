# -*- coding: utf-8 -*
import openerp
from openerp.http import request


class CalendarBusController(openerp.addons.bus.controllers.main.BusController):
    # --------------------------
    # Extends BUS Controller Poll
    # --------------------------
    def _poll(self, dbname, channels, last, options):
        if request.session.uid:
            channels.append((request.db, 'calendar.alarm', request.env.user.partner_id.id))
        return super(CalendarBusController, self)._poll(dbname, channels, last, options)
