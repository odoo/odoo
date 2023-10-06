# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json
from threading import Event
import time

from odoo.http import request

class EventManager(object):
    def __init__(self):
        self.events = []
        self.sessions = {}

    def _delete_expired_sessions(self, max_time=70):
        '''
        Clears sessions that are no longer called.

        :param max_time: time a session can stay unused before being deleted
        '''
        now = time.time()
        expired_sessions = [
            session
            for session in self.sessions
            if now - self.sessions[session]['time_request'] > max_time
        ]
        for session in expired_sessions:
            del self.sessions[session]

    def add_request(self, listener):
        self.session = {
            'session_id': listener['session_id'],
            'devices': listener['devices'],
            'event': Event(),
            'result': {},
            'time_request': time.time(),
        }
        self._delete_expired_sessions()
        self.sessions[listener['session_id']] = self.session
        return self.sessions[listener['session_id']]

    def device_changed(self, device):
        event = {
            **device.data,
            'device_identifier': device.device_identifier,
            'time': time.time(),
            'request_data': json.loads(request.params['data']) if request and 'data' in request.params else None,
        }
        self.events.append(event)
        for session in self.sessions:
            if device.device_identifier in self.sessions[session]['devices'] and not self.sessions[session]['event'].is_set():
                self.sessions[session]['result'] = event
                self.sessions[session]['event'].set()


event_manager = EventManager()
