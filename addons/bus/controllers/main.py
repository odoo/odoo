# -*- coding: utf-8 -*-
import json
import random

from openerp import api, http, exceptions
from openerp.addons.bus.models.bus import dispatch

KEEPALIVES = [
    "Hellooo.",
    "Searching.",
    "Canvassing.",
    "Sentry mode activated.",
    "Is anyone there?",
    "Could you come over here?",
]

class BusController(http.Controller):
    # EventSource implementation
    @http.route('/longpolling/stream', type='http', auth='public')
    def stream(self, channels):
        if http.request.registry.in_test_mode():
            raise exceptions.UserError("bus.Bus not available in test mode")

        channels = self._get_channels(channels.split(','))

        db = http.request.db
        last = int(http.request.httprequest.headers.get('Last-Event-Id') or 0)

        http.request.cr.close()
        http.request._cr = None
        return http.Response(
            self._get_events_stream(db, channels, last),
            mimetype='text/event-stream'
        )

    def _get_channels(self, cs):
        return cs

    def _get_events_stream(self, db, channels, last):
        # first set random retry delay (between 0.1s and 10s) to mitigate stampedes
        yield 'retry: {}\n\n'.format(random.randint(100, 10000))

        while True:
            with api.Environment.manage():
                notifications = dispatch.poll(
                    dbname=db,
                    channels=channels,
                    last=last,
                    timeout=15,
                )

            if notifications:
                for n in notifications:
                    # update last event seen so next round doesn't try to
                    # re-fetch messages we've already seen
                    last = max(last, n['id'])
                    if n['id'] != -1:  # ignore id for presence messages
                        yield 'id: {}\n'.format(n['id'])
                    yield 'data: {}\n\n'.format(json.dumps(n))
            else:
                # timeout, just send a keepalive comment to the client so they
                # don't close the connection
                yield ': {}\n\n'.format(random.choice(KEEPALIVES))

