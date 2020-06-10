#!/usr/bin/python3
from base64 import b64decode
from dbus.mainloop.glib import DBusGMainLoop
from importlib import util
import json
import logging
import os
import socket
import subprocess
import sys
from threading import Thread, Event
import time
import urllib3

from odoo import http, tools
from odoo.http import send_file
from odoo.modules.module import get_resource_path
from odoo.addons.hw_drivers.tools import helpers

_logger = logging.getLogger(__name__)


#----------------------------------------------------------
# Controllers
#----------------------------------------------------------

class StatusController(http.Controller):
    @http.route('/hw_drivers/action', type='json', auth='none', cors='*', csrf=False, save_session=False)
    def action(self, session_id, device_id, data):
        """
        This route is called when we want to make a action with device (take picture, printing,...)
        We specify in data from which session_id that action is called
        And call the action of specific device
        """
        iot_device = iot_devices.get(device_id)
        if iot_device:
            iot_device.data['owner'] = session_id
            data = json.loads(data)
            iot_device.action(data)
            return True
        return False

    @http.route('/hw_drivers/check_certificate', type='http', auth='none', cors='*', csrf=False, save_session=False)
    def check_certificate(self):
        """
        This route is called when we want to check if certificate is up-to-date
        Used in cron.daily
        """
        helpers.check_certificate()

    @http.route('/hw_drivers/event', type='json', auth='none', cors='*', csrf=False, save_session=False)
    def event(self, listener):
        """
        listener is a dict in witch there are a sessions_id and a dict of device_id to listen
        """
        req = event_manager.add_request(listener)
        if req['event'].wait(50):
            req['event'].clear()
            req['result']['session_id'] = req['session_id']
            return req['result']

    @http.route('/hw_drivers/box/connect', type='http', auth='none', cors='*', csrf=False, save_session=False)
    def connect_box(self, token):
        """
        This route is called when we want that a IoT Box will be connected to a Odoo DB
        token is a base 64 encoded string and have 2 argument separate by |
        1 - url of odoo DB
        2 - token. This token will be compared to the token of Odoo. He have 1 hour lifetime
        """
        server = helpers.get_odoo_server_url()
        image = get_resource_path('hw_drivers', 'static/img', 'False.jpg')
        if not server:
            credential = b64decode(token).decode('utf-8').split('|')
            url = credential[0]
            token = credential[1]
            if len(credential) > 2:
                # IoT Box send token with db_uuid and enterprise_code only since V13
                db_uuid = credential[2]
                enterprise_code = credential[3]
                helpers.add_credential(db_uuid, enterprise_code)
            try:
                subprocess.check_call([get_resource_path('point_of_sale', 'tools/posbox/configuration/connect_to_server.sh'), url, '', token, 'noreboot'])
                m.send_alldevices()
                image = get_resource_path('hw_drivers', 'static/img', 'True.jpg')
                helpers.odoo_restart(3)
            except subprocess.CalledProcessError as e:
                _logger.error('A error encountered : %s ' % e.output)
        if os.path.isfile(image):
            with open(image, 'rb') as f:
                return f.read()

    @http.route('/hw_drivers/download_logs', type='http', auth='none', cors='*', csrf=False, save_session=False)
    def download_logs(self):
        """
        Downloads the log file
        """
        if tools.config['logfile']:
            res = send_file(tools.config['logfile'], mimetype="text/plain", as_attachment=True)
            res.headers['Cache-Control'] = 'no-cache'
            return res

#----------------------------------------------------------
# Log Exceptions
#----------------------------------------------------------

class ExceptionLogger:
    """
    Redirect Exceptions to the logger to keep track of them in the log file.
    """

    def __init__(self):
        self.logger = logging.getLogger()

    def write(self, message):
        if message != '\n':
            self.logger.error(message)

    def flush(self):
        pass

sys.stderr = ExceptionLogger()

#----------------------------------------------------------
# Drivers
#----------------------------------------------------------

drivers = []
interfaces = {}
iot_devices = {}

class InterfaceMetaClass(type):
    def __new__(cls, clsname, bases, attrs):
        if clsname in interfaces:
            return interfaces[clsname]
        new_interface = super(InterfaceMetaClass, cls).__new__(cls, clsname, bases, attrs)
        interfaces[clsname] = new_interface
        return new_interface

class Interface(Thread, metaclass=InterfaceMetaClass):
    _loop_delay = 3  # Delay (in seconds) between calls to get_devices or 0 if it should be called only once
    _detected_devices = {}
    connection_type = ''

    def __init__(self):
        super(Interface, self).__init__()
        self.drivers = sorted([d for d in drivers if d.connection_type == self.connection_type], key=lambda d: d.priority, reverse=True)

    def run(self):
        while self.connection_type and self.drivers:
            self.update_iot_devices(self.get_devices())
            if not self._loop_delay:
                break
            time.sleep(self._loop_delay)

    def update_iot_devices(self, devices={}):
        added = devices.keys() - self._detected_devices
        removed = self._detected_devices - devices.keys()
        self._detected_devices = devices.keys()

        for path in removed:
            if path in iot_devices:
                iot_devices[path].disconnect()
                _logger.info('Device %s is now disconnected', path)

        for path in added:
            for driver in self.drivers:
                if driver.supported(device=devices[path]):
                    _logger.info('Device %s is now connected', path)
                    d = driver(device=devices[path])
                    d.daemon = True
                    d.start()
                    iot_devices[path] = d
                    break

    def get_devices(self):
        raise NotImplementedError()

class DriverMetaClass(type):
    def __new__(cls, clsname, bases, attrs):
        newclass = super(DriverMetaClass, cls).__new__(cls, clsname, bases, attrs)
        if hasattr(newclass, 'priority'):
            newclass.priority += 1
        else:
            newclass.priority = 0
        drivers.append(newclass)
        return newclass

class Driver(Thread, metaclass=DriverMetaClass):
    """
    Hook to register the driver into the drivers list
    """
    connection_type = ""

    def __init__(self, device):
        super(Driver, self).__init__()
        self.dev = device
        self.data = {'value': ''}
        self._device_manufacturer = ''

    @property
    def device_name(self):
        return self._device_name

    @property
    def device_identifier(self):
        return self.dev.identifier

    @property
    def device_manufacturer(self):
        return self._device_manufacturer

    @property
    def device_connection(self):
        """
        On specific driver override this method to give connection type of device
        return string
        possible value : direct - network - bluetooth - serial - hdmi
        """
        return self._device_connection

    @property
    def device_type(self):
        """
        On specific driver override this method to give type of device
        return string
        possible value : printer - camera - keyboard - scanner - display - device
        """
        return self._device_type

    @classmethod
    def supported(cls, device):
        """
        On specific driver override this method to check if device is supported or not
        return True or False
        """
        pass

    def get_message(self):
        return ''

    def action(self, data):
        """
        On specific driver override this method to make a action with device (take picture, printing,...)
        """
        raise NotImplementedError()

    def disconnect(self):
        del iot_devices[self.device_identifier]


#----------------------------------------------------------
# Device manager
#----------------------------------------------------------

class EventManager(object):
    def __init__(self):
        self.sessions = {}

    def _delete_expired_sessions(self, max_time=70):
        '''
        Clears sessions that are no longer called.

        :param max_time: time a session can stay unused before being deleted
        '''
        now = time.time()
        expired_sessions = [session for session in self.sessions if now - self.sessions[session]['time_request'] > max_time]
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
        for session in self.sessions:
            if device.device_identifier in self.sessions[session]['devices']:
                self.sessions[session]['result'] = device.data
                self.sessions[session]['result']['device_id'] = device.device_identifier
                self.sessions[session]['event'].set()


event_manager = EventManager()


#----------------------------------------------------------
# Manager
#----------------------------------------------------------

class Manager(Thread):

    def load_iot_handlers(self):
        """
        This method loads local files: 'odoo/addons/hw_drivers/iot_handlers/drivers' and
        'odoo/addons/hw_drivers/iot_handlers/interfaces'
        And execute these python drivers and interfaces
        """
        helpers.download_iot_handlers()
        for directory in ['interfaces', 'drivers']:
            path = get_resource_path('hw_drivers', 'iot_handlers', directory)
            filesList = os.listdir(path)
            for file in filesList:
                path_file = os.path.join(path, file)
                spec = util.spec_from_file_location(file, path_file)
                if spec:
                    module = util.module_from_spec(spec)
                    spec.loader.exec_module(module)
        http.addons_manifest = {}
        http.root = http.Root()

    def send_alldevices(self):
        """
        This method send IoT Box and devices informations to Odoo database
        """
        server = helpers.get_odoo_server_url()
        if server:
            subject = helpers.read_file_first_line('odoo-subject.conf')
            if subject:
                domain = helpers.get_ip().replace('.', '-') + subject.strip('*')
            else:
                domain = helpers.get_ip()
            iot_box = {
                'name': socket.gethostname(),
                'identifier': helpers.get_mac_address(),
                'ip': domain,
                'token': helpers.get_token(),
                'version': helpers.get_version()
                }
            devices_list = {}
            for device in iot_devices:
                identifier = iot_devices[device].device_identifier
                devices_list[identifier] = {
                    'name': iot_devices[device].device_name,
                    'type': iot_devices[device].device_type,
                    'manufacturer': iot_devices[device].device_manufacturer,
                    'connection': iot_devices[device].device_connection,
                }
            data = {
                'params': {
                    'iot_box' : iot_box,
                    'devices' : devices_list,
                }
            }
            # disable certifiacte verification
            urllib3.disable_warnings()
            http = urllib3.PoolManager(cert_reqs='CERT_NONE')
            try:
                http.request(
                    'POST',
                    server + "/iot/setup",
                    body = json.dumps(data).encode('utf8'),
                    headers = {'Content-type': 'application/json', 'Accept': 'text/plain'}
                )
            except Exception as e:
                _logger.error('Could not reach configured server')
                _logger.error('A error encountered : %s ' % e)
        else:
            _logger.warning('Odoo server not set')

    def run(self):
        """
        Thread that will check connected/disconnected device, load drivers if needed and contact the odoo server with the updates
        """
        helpers.check_git_branch()
        helpers.check_certificate()
        self.send_alldevices()
        self.load_iot_handlers()
        self.previous_iot_devices = []
        for interface in interfaces.values():
            i = interface()
            i.daemon = True
            i.start()
        while 1:
            if iot_devices != self.previous_iot_devices:
                self.send_alldevices()
                self.previous_iot_devices = iot_devices.copy()
            time.sleep(3)

# Must be started from main thread
DBusGMainLoop(set_as_default=True)

m = Manager()
m.daemon = True
m.start()
