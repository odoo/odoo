#!/usr/bin/python3
import logging
import time
from threading import Thread, Event
from usb import core
from gatt import DeviceManager as Gatt_DeviceManager
import subprocess
import netifaces
import json
from re import sub
import urllib3
import os
import socket
from importlib import util
import v4l2
from fcntl import ioctl
from cups import Connection as cups_connection
from glob import glob
from base64 import b64decode
from pathlib import Path
import socket

from odoo import http, _
from odoo.modules.module import get_resource_path

_logger = logging.getLogger(__name__)


#----------------------------------------------------------
# Helper
#----------------------------------------------------------

def get_mac_address():
    try:
        return netifaces.ifaddresses('eth0')[netifaces.AF_LINK][0]['addr']
    except:
        return netifaces.ifaddresses('wlan0')[netifaces.AF_LINK][0]['addr']

def get_ip():
    try:
        return netifaces.ifaddresses('eth0')[netifaces.AF_INET][0]['addr']
    except:
        return netifaces.ifaddresses('wlan0')[netifaces.AF_INET][0]['addr']

def read_file_first_line(filename):
    path = Path.home() / filename
    if path.exists():
        with path.open('r') as f:
            return f.readline().strip('\n')
    return ''

def get_odoo_server_url():
    return read_file_first_line('odoo-remote-server.conf')

def get_token():
    return read_file_first_line('token')

def get_version():
    return '19_07'

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
        server = get_odoo_server_url()
        image = get_resource_path('hw_drivers', 'static/img', 'False.jpg')
        if server == '':
            token = b64decode(token).decode('utf-8')
            url, token = token.split('|')
            try:
                subprocess.check_call([get_resource_path('point_of_sale', 'tools/posbox/configuration/connect_to_server.sh'), url, '', token, 'noreboot'])
                m.send_alldevices()
                image = get_resource_path('hw_drivers', 'static/img', 'True.jpg')
            except subprocess.CalledProcessError as e:
                _logger.error('A error encountered : %s ' % e.output)
        if os.path.isfile(image):
            with open(image, 'rb') as f:
                return f.read()

#----------------------------------------------------------
# Drivers
#----------------------------------------------------------

drivers = []
bt_devices = {}
socket_devices = {}
iot_devices = {}

class DriverMetaClass(type):
    def __new__(cls, clsname, bases, attrs):
        newclass = super(DriverMetaClass, cls).__new__(cls, clsname, bases, attrs)
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
        self.gatt_device = False

    @property
    def device_name(self):
        return self._device_name

    @property
    def device_identifier(self):
        return self._device_identifier

    @property
    def device_connection(self):
        """
        On specific driver override this method to give connection type of device
        return string
        possible value : direct - network - bluetooth
        """
        return self._device_connection

    @property
    def device_type(self):
        """
        On specific driver override this method to give type of device
        return string
        possible value : printer - camera - device
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


class IoTDevice(object):

    def __init__(self, dev, connection_type):
        self.dev = dev
        self.connection_type = connection_type

event_manager = EventManager()


#----------------------------------------------------------
# Manager
#----------------------------------------------------------

class Manager(Thread):

    def __init__(self):
        super(Manager, self).__init__()
        self.load_drivers()

    def load_drivers(self):
        """
        This method loads local files: 'odoo/addons/hw_drivers/drivers'
        And execute these python drivers
        """
        path = get_resource_path('hw_drivers', 'drivers')
        driversList = os.listdir(path)
        for driver in driversList:
            path_file = os.path.join(path, driver)
            spec = util.spec_from_file_location(driver, path_file)
            if spec:
                module = util.module_from_spec(spec)
                spec.loader.exec_module(module)

    def send_alldevices(self):
        """
        This method send IoT Box and devices informations to Odoo database
        """
        server = get_odoo_server_url()
        if server:
            iot_box = {
                'name': socket.gethostname(),
                'identifier': get_mac_address(),
                'ip': get_ip(),
                'token': get_token(),
                'version': get_version()
                }
            devices_list = {}
            for device in iot_devices:
                identifier = iot_devices[device].device_identifier
                devices_list[identifier] = {
                    'name': iot_devices[device].device_name,
                    'type': iot_devices[device].device_type,
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

    def usb_loop(self):
        usb_devices = {}
        devs = core.find(find_all=True)
        for dev in devs:
            path =  "usb_%04x:%04x_%03d_%03d_" % (dev.idVendor, dev.idProduct, dev.bus, dev.address)
            iot_device = IoTDevice(dev, 'usb')
            usb_devices[path] = iot_device
        return usb_devices

    def video_loop(self):
        camera_devices = {}
        videos = glob('/dev/video*')
        for video in videos:
            with open(video, 'w') as path:
                dev = v4l2.v4l2_capability()
                ioctl(path, v4l2.VIDIOC_QUERYCAP, dev)
                dev.interface = video
                iot_device = IoTDevice(dev, 'video')
                camera_devices[dev.bus_info.decode('utf-8')] = iot_device
        return camera_devices

    def printer_loop(self):
        printer_devices = {}
        devices = conn.getDevices()
        for path in [printer_lo for printer_lo in devices if devices[printer_lo]['device-make-and-model'] != 'Unknown']:
            if 'uuid=' in path:
                serial = sub('[^a-zA-Z0-9 ]+', '', path.split('uuid=')[1])
            elif 'serial=' in path:
                serial = sub('[^a-zA-Z0-9 ]+', '', path.split('serial=')[1])
            else:
                serial = sub('[^a-zA-Z0-9 ]+', '', path)
            devices[path]['identifier'] = serial
            devices[path]['url'] = path
            iot_device = IoTDevice(devices[path], 'printer')
            printer_devices[serial] = iot_device
        return printer_devices

    def run(self):
        """
        Thread that will check connected/disconnected device, load drivers if needed and contact the odoo server with the updates
        """
        devices = {}
        updated_devices = {}
        self.send_alldevices()
        cpt = 0
        while 1:
            updated_devices = self.usb_loop()
            updated_devices.update(self.video_loop())
            updated_devices.update(bt_devices)
            updated_devices.update(socket_devices)
            if cpt % 40 == 0:
                printer_devices = self.printer_loop()
                cpt = 0
            updated_devices.update(printer_devices)
            cpt += 1
            added = updated_devices.keys() - devices.keys()
            removed = devices.keys() - updated_devices.keys()
            devices = updated_devices
            for path in [device_rm for device_rm in removed if device_rm in iot_devices]:
                iot_devices[path].disconnect()
            for path in [device_add for device_add in added if device_add not in iot_devices]:
                for driverclass in [d for d in drivers if d.connection_type == devices[path].connection_type]:
                    if driverclass.supported(device = updated_devices[path].dev):
                        _logger.info('For device %s will be driven', path)
                        d = driverclass(device = updated_devices[path].dev)
                        d.daemon = True
                        d.start()
                        iot_devices[path] = d
                        self.send_alldevices()
                        break
            time.sleep(3)

class GattBtManager(Gatt_DeviceManager):

    def device_discovered(self, device):
        path = "bt_%s" % (device.mac_address,)
        if path not in bt_devices:
            device.manager = self
            iot_device = IoTDevice(device, 'bluetooth')
            bt_devices[path] = iot_device

class BtManager(Thread):

    def run(self):
        dm = GattBtManager(adapter_name='hci0')
        for device in [device_con for device_con in dm.devices() if device_con.is_connected()]:
            device.disconnect()
        dm.start_discovery()
        dm.run()

class SocketManager(Thread):

    def run(self):
        while True:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.bind(('', 9000))
            sock.listen(1)
            dev, addr = sock.accept()
            if addr and addr[0] not in socket_devices:
                iot_device = IoTDevice(type('', (), {'dev': dev}), 'socket')
                socket_devices[addr[0]] = iot_device

conn = cups_connection()
PPDs = conn.getPPDs()
printers = conn.getPrinters()

m = Manager()
m.daemon = True
m.start()

bm = BtManager()
bm.daemon = True
bm.start()

sm = SocketManager()
sm.daemon = True
sm.start()
