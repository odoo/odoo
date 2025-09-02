# Part of Odoo. See LICENSE file for full copyright and licensing details.

from threading import Event
import time

from odoo.http import request
from odoo.addons.iot_drivers.tools import helpers
from odoo.addons.iot_drivers.webrtc_client import webrtc_client
from odoo.addons.iot_drivers.websocket_client import send_to_controller


class EventManager:
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

        If ``data`` is provided, it means that the caller is the action method,
        it will be used as the event data (instead of the one provided by the request).

        :param Driver device: actual device class
        :param dict data: data returned by the device (optional)
        """
        data = data or (request.params.get('data', {}) if request else {})

        # Make notification available to longpolling event route
        event = {
            **device.data,
            'device_identifier': device.device_identifier,
            'time': time.time(),
            **data,
        }
        send_to_controller({
            **event,
            'session_id': data.get('action_args', {}).get('session_id', ''),
            'iot_box_identifier': helpers.get_identifier(),
            **data,
        })
        webrtc_client.send(event)
        self.events.append(event)
        for session in self.sessions:
            session_devices = self.sessions[session]['devices']
            if (
                any(d in [device.device_identifier, device.device_type] for d in session_devices)
                and not self.sessions[session]['event'].is_set()
            ):
                if device.device_type in session_devices:
                    event['device_identifier'] = device.device_type  # allow device type as identifier (longpolling)
                self.sessions[session]['result'] = event
                self.sessions[session]['event'].set()


event_manager = EventManager()
