# -*- coding: utf-8 -*-

import base64

from odoo import exceptions, _
from odoo.http import Controller, request, route
from odoo.addons.base.models.assetsbundle import AssetsBundle
from odoo.addons.bus.models.bus import dispatch


class BusController(Controller):
    """ Examples:
    openerp.jsonRpc('/longpolling/poll','call',{"channels":["c1"],last:0}).then(function(r){console.log(r)});
    """

    # override to add channels
    def _poll(self, dbname, channels, last_bus_message_id, options):
        # update the user presence
        if request.session.uid and 'bus_inactivity' in options:
            request.env['bus.presence'].update(options.get('bus_inactivity'))
        request.cr.close()
        request._cr = None
        return dispatch.poll(dbname=dbname, channels=channels, last_bus_message_id=last_bus_message_id, options=options)

    @route('/longpolling/poll', type="json", auth="public", cors="*")
    def poll(self, channels, last_bus_message_id, options=None):
        # TODO SEB clean up those params and options, rename last to be more explicit
        # have channel as kwargs handle by other modules (mail_channel specifically)
        # get rid of options probably
        if options is None:
            options = {}
        if not dispatch:
            raise Exception("bus.Bus unavailable")
        if [c for c in channels if not isinstance(c, str)]:
            raise Exception("bus.Bus only string channels are allowed.")
        if request.registry.in_test_mode():
            raise exceptions.UserError(_("bus.Bus not available in test mode"))
        return self._poll(dbname=request.db, channels=channels, last_bus_message_id=last_bus_message_id, options=options)

    @route('/longpolling/im_status', type="json", auth="user")
    def im_status(self, partner_ids):
        return request.env['res.partner'].with_context(active_test=False).search([('id', 'in', partner_ids)]).read(['im_status'])

    @route('/bus/server_communication_shared_worker.js', type='http', auth='public')
    def server_communication_shared_worker(self, **kwargs):
        # _get_asset return the bundle html code (script and link list) but we want to use the attachment content
        bundle = 'bus.server_communication_shared_worker'
        files, remains = request.env["ir.qweb"]._get_asset_content(bundle, options=request.context)
        asset = AssetsBundle(bundle, files)

        mock_attachment = getattr(asset, 'js')()
        if isinstance(mock_attachment, list):  # suppose that CSS asset will not required to be split in pages
            mock_attachment = mock_attachment[0]
        # can't use /web/content directly because we don't have attachment ids (attachments must be created)
        status, headers, content = request.env['ir.http'].binary_content(id=mock_attachment.id, unique=asset.checksum)
        content_base64 = base64.b64decode(content) if content else ''
        headers.append(('Content-Length', len(content_base64)))
        return request.make_response(content_base64, headers)
