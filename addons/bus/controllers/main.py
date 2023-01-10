# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json

from odoo import exceptions, _
from odoo.http import Controller, request, route
from odoo.addons.bus.models.bus import dispatch


class BusController(Controller):

    # override to add channels
    def _poll(self, dbname, channels, last, options):
        channels = list(channels)  # do not alter original list
        channels.append('broadcast')
        # update the user presence
        if request.session.uid and 'bus_inactivity' in options:
            request.env['bus.presence'].update(inactivity_period=options.get('bus_inactivity'), identity_field='user_id', identity_value=request.session.uid)
        request.cr.close()
        request._cr = None
        return dispatch.poll(dbname, channels, last, options)

    @route('/longpolling/poll', type="json", auth="public", cors="*")
    def poll(self, channels, last, options=None):
        if options is None:
            options = {}
        if not dispatch:
            raise Exception("bus.Bus unavailable")
        if [c for c in channels if not isinstance(c, str)]:
            raise Exception("bus.Bus only string channels are allowed.")
        if request.registry.in_test_mode():
            raise exceptions.UserError(_("bus.Bus not available in test mode"))
        return self._poll(request.db, channels, last, options)

    @route('/longpolling/im_status', type="json", auth="user")
    def im_status(self, partner_ids):
        return request.env['res.partner'].with_context(active_test=False).search([('id', 'in', partner_ids)]).read(['im_status'])

    @route('/longpolling/health', type='http', auth='none', save_session=False)
    def health(self):
        data = json.dumps({
            'status': 'pass',
        })
        headers = [('Content-Type', 'application/json'),
                   ('Cache-Control', 'no-store')]
        return request.make_response(data, headers)
