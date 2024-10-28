# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json
from threading import Event
import time

from odoo.addons.hw_drivers.tools import helpers
from odoo.addons.hw_drivers.websocket_client import WebsocketClient
from odoo.http import request


class EventManager(object):
    def __init__(self):
        self.events = []
        self.sessions = {}

    def _delete_expired_sessions(self, ttl=70):
        """Clear sessions that are no longer called.

        :param int ttl: time a session can stay unused before being deleted
        """
        self.sessions = {
            session: self.sessions[session]
            for session in self.sessions
            if self.sessions[session]['time_request'] + ttl < time.time()
        }

    def add_request(self, listener):
        """Create a new session for the listener.

        :param dict listener: listener id and devices
        :return: the session created
        """
        session_id = listener['session_id']
        session = {
            'session_id': session_id,
            'devices': listener['devices'],
            'event': Event(),
            'result': {},
            'time_request': time.time(),
        }
        self._delete_expired_sessions()
        self.sessions[session_id] = session
        return session

    def device_changed(self, device, data=None):
        """Register a new event.
        If ``data`` is provided, it will be used as the event data (instead
        of the one provided by the request).

        :param Driver device: actual device class
        :param dict data: data returned by the device (optional)
        """
        if data:
            # Notify via websocket
            WebsocketClient.send_to_controller({
                'session_id': data.get('action_args', {}).get('session_id', ''),
                'iot_box_identifier': helpers.get_mac_address(),
                'device_identifier': device.device_identifier,
                **data
            })
        else:
            data = json.loads(request.params['data']) if request and 'data' in request.params else {}

        # Make notification available to longpolling event route
        event = {
            **device.data,
            'device_identifier': device.device_identifier,
            'time': time.time(),
            **data,
        }
        self.events.append(event)
        for session in self.sessions:
            if (
                device.device_identifier in self.sessions[session]['devices']
                and not self.sessions[session]['event'].is_set()
            ):
                self.sessions[session]['result'] = event
                self.sessions[session]['event'].set()


event_manager = EventManager()
