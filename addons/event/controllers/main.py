# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from werkzeug.exceptions import NotFound

from odoo.http import Controller, request, route, content_disposition


class EventController(Controller):

    @route(['''/event/<model("event.event", "[('state', 'in', ('confirm', 'done'))]"):event>/ics'''], type='http', auth="public")
    def event_ics_file(self, event, **kwargs):
        files = event._get_ics_file()
        if not event.id in files:
            return NotFound()
        content = files[event.id]
        return request.make_response(content, [
            ('Content-Type', 'application/octet-stream'),
            ('Content-Length', len(content)),
            ('Content-Disposition', content_disposition('%s.ics' % event.name))
        ])
