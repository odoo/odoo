# -*- coding: utf-8 -*-
from urllib import urlencode

from odoo import exceptions
from odoo.tools import config
from odoo.http import Controller, request, route
from odoo.addons.bus.models.bus import dispatch


class BusController(Controller):
    """ Examples:
    openerp.jsonRpc('/longpolling/poll','call',{"channels":["c1"],last:0}).then(function(r){console.log(r)});
    openerp.jsonRpc('/longpolling/send','call',{"channel":"c1","message":"m1"});
    openerp.jsonRpc('/longpolling/send','call',{"channel":"c2","message":"m2"});
    """

    _redirect_dispatch_url = (
        "http://localhost:{port}/longpolling/{verb}?{query_string}"
    )

    def _redirect_dispatch(self, verb, **kw):
        """Call this method to redirect calls to the longpolling port
        from the workers port"""
        # TODO: Allow the configuration file to specify alternate url for the
        # longpolling_port. I.e. in a cluster there might be a single instance
        # dedicated to longpolling and all other instances send requests to it.
        #
        # On the other hand, if there is a cluster, the load balancer might as
        # well do the /longpolling url redirection. This is just a convenience
        # for local development.
        port = config['longpolling_port']
        if port:

            query_string = urlencode(dict(
                # Create a new token since we don't have access to the original
                csrf_token=request.csrf_token(),
                # The session cookie won't be forwared to the longpolling_port
                session_id=request.httprequest.cookies.get('session_id'),
                # For some reason, chrome loses the Content-Type header so we
                # force it or the request won't be handled as JsonRequest
                force_content_type=request.httprequest.environ['CONTENT_TYPE'],
            ))
            url = self._redirect_dispatch_url.format(
                port=port, verb=verb, query_string=query_string,
            )
            # code 307 is necessary for keeping the POST verb and payload.
            # Otherwise browsers turn POSTs into GETs.
            result = request._json_response(url)
            result.status_code = 307
            result.headers['Location'] = url
            # the three lines above should be wrapped in a function called:
            # json_redirect() to parallel werkzeug.utils.redirect
            return result
        else:
            msg = "bus.Bus unavailable and longpolling_port undefined"
            raise Exception(msg)

    @route('/longpolling/send', type="json", auth="public")
    def send(self, channel, message):
        # NOTE: is this necessary? Or can we handle `send` in the workers?
        if not dispatch:
            return self._redirect_dispatch("send", channel=channel,
                                           message=message)
        if not isinstance(channel, basestring):
            raise Exception("bus.Bus only string channels are allowed.")
        return request.env['bus.bus'].sendone(channel, message)

    # override to add channels
    def _poll(self, dbname, channels, last, options):
        # update the user presence
        if request.session.uid and 'bus_inactivity' in options:
            request.env['bus.presence'].update(options.get('bus_inactivity'))
        request.cr.close()
        request._cr = None
        return dispatch.poll(dbname, channels, last, options)

    @route('/longpolling/poll', type="json", auth="public")
    def poll(self, channels, last, options=None):
        if options is None:
            options = {}
        if not dispatch:
            return self._redirect_dispatch("poll", channels=channels,
                                           last=last, options=options)
        if [c for c in channels if not isinstance(c, basestring)]:
            raise Exception("bus.Bus only string channels are allowed.")
        if request.registry.in_test_mode():
            raise exceptions.UserError("bus.Bus not available in test mode")
        return self._poll(request.db, channels, last, options)
