# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.http import request
from odoo.addons.bus.controllers.main import BusController

class LiveChatController(BusController):
    def _poll(self, dbname, channels, last, options):
        visitor_channels = []
        for channel in channels:
            visitor = '-'.join([channel, str(request.env.user.partner_id.id)])
            visitor_channels.append((request.db, 'typing.notification', visitor))
        channels += visitor_channels
        return super(LiveChatController, self)._poll(dbname, channels, last, options)
