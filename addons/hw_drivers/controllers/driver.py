#!/usr/bin/python3
import logging
import time
from threading import Thread, Event, Lock
from usb import core
from gatt import DeviceManager as Gatt_DeviceManager
import subprocess
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
import ctypes

from odoo import http, _
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
        if server == '':
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
                helpers.check_certificate()
                m.send_alldevices()
                m.load_drivers()
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
        # Some drivers must be tried only when all the others have been ruled out. These are kept at the bottom of the list.
        if newclass.is_tested_last:
            drivers.append(newclass)
        else:
            drivers.insert(0, newclass)
        return newclass

class Driver(Thread, metaclass=DriverMetaClass):
    """
    Hook to register the driver into the drivers list
    """
    connection_type = ""
    is_tested_last = False

    def __init__(self, device):
        super(Driver, self).__init__()
        self.dev = device
        self.data = {'value': ''}
        self.gatt_device = False
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


class IoTDevice(object):

    def __init__(self, dev, connection_type):
        self.dev = dev
        self.connection_type = connection_type

event_manager = EventManager()


#----------------------------------------------------------
# Manager
#----------------------------------------------------------

class Manager(Thread):

    def load_drivers(self):
        """
        This method loads local files: 'odoo/addons/hw_drivers/drivers'
        And execute these python drivers
        """
        helpers.download_drivers()
        path = get_resource_path('hw_drivers', 'drivers')
        driversList = os.listdir(path)
        self.devices = {}
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

    def get_connected_displays(self):
        display_devices = {}
        hdmi = subprocess.check_output(['tvservice', '-n']).decode('utf-8').replace('\n', '')
        if hdmi.find('=') != -1 and hdmi.split('=')[1] != "Unk-Composite dis":
            hdmi_serial = sub('[^a-zA-Z0-9 ]+', '', hdmi.split('=')[1]).replace(' ', '_')
            iot_device = IoTDevice({
                'identifier': hdmi_serial,
                'name': hdmi.split('=')[1],
            }, 'display')
            display_devices[hdmi_serial] = iot_device

        if not len(display_devices):
            # No display connected, create "fake" device to be accessed from another computer
            display_devices['distant_display'] = IoTDevice({
                'identifier': "distant_display",
                'name': "Distant Display",
            }, 'display')

        return display_devices

    def serial_loop(self):
        serial_devices = {}
        for identifier in glob('/dev/serial/by-path/*'):
            iot_device = IoTDevice({'identifier': identifier, }, 'serial')
            serial_devices[identifier] = iot_device
        return serial_devices

    def usb_loop(self):
        """
        Loops over the connected usb devices, assign them an identifier, instantiate
        an `IoTDevice` for them.

        USB devices are identified by a combination of their `idVendor` and
        `idProduct`. We can't be sure this combination in unique per equipment.
        To still allow connecting multiple similar equipments, we complete the
        identifier by a counter. The drawbacks are we can't be sure the equipments
        will get the same identifiers after a reboot or a disconnect/reconnect.

        :return: a dict of the `IoTDevices` instances indexed by their identifier.
        """
        usb_devices = {}
        devs = core.find(find_all=True)
        cpt = 2
        for dev in devs:
            dev.identifier =  "usb_%04x:%04x" % (dev.idVendor, dev.idProduct)
            if dev.identifier in usb_devices:
                dev.identifier += '_%s' % cpt
                cpt += 1
            iot_device = IoTDevice(dev, 'usb')
            usb_devices[dev.identifier] = iot_device
        return usb_devices

    def video_loop(self):
        camera_devices = {}
        videos = glob('/dev/video*')
        for video in videos:
            with open(video, 'w') as path:
                dev = v4l2.v4l2_capability()
                ioctl(path, v4l2.VIDIOC_QUERYCAP, dev)
                dev.interface = video
                dev.identifier = dev.bus_info.decode('utf-8')
                iot_device = IoTDevice(dev, 'video')
                camera_devices[dev.identifier] = iot_device
        return camera_devices

    def printer_loop(self):
        printer_devices = {}
        with cups_lock:
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
        helpers.check_certificate()
        updated_devices = {}
        self.send_alldevices()
        self.load_drivers()
        # The list of devices doesn't change after the Raspberry has booted
        display_devices = self.get_connected_displays()
        cpt = 0
        while 1:
            updated_devices = self.usb_loop()
            updated_devices.update(self.video_loop())
            updated_devices.update(mpdm.devices)
            updated_devices.update(display_devices)
            updated_devices.update(bt_devices)
            updated_devices.update(socket_devices)
            updated_devices.update(self.serial_loop())
            if cpt % 40 == 0:
                printer_devices = self.printer_loop()
                cpt = 0
            updated_devices.update(printer_devices)
            cpt += 1
            added = updated_devices.keys() - self.devices.keys()
            removed = self.devices.keys() - updated_devices.keys()
            self.devices = updated_devices
            send_devices = False
            for path in [device_rm for device_rm in removed if device_rm in iot_devices]:
                iot_devices[path].disconnect()
                _logger.info('Device %s is now disconnected', path)
                send_devices = True
            for path in [device_add for device_add in added if device_add not in iot_devices]:
                for driverclass in [d for d in drivers if d.connection_type == self.devices[path].connection_type]:
                    if driverclass.supported(device = updated_devices[path].dev):
                        _logger.info('Device %s is now connected', path)
                        d = driverclass(device = updated_devices[path].dev)
                        d.daemon = True
                        d.start()
                        iot_devices[path] = d
                        send_devices = True
                        break
            if send_devices:
                self.send_alldevices()
            time.sleep(3)

class GattBtManager(Gatt_DeviceManager):

    def device_discovered(self, device):
        path = "bt_%s" % (device.mac_address,)
        if path not in bt_devices:
            device.manager = self
            device.identifier = path
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
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                sock.bind(('', 9000))
                sock.listen(1)
                dev, addr = sock.accept()
                if addr and addr[0] not in socket_devices:
                    iot_device = IoTDevice(type('', (), {'dev': dev}), 'socket')
                    socket_devices[addr[0]] = iot_device
            except OSError as e:
                _logger.error(_('Error in SocketManager: %s') % (e.strerror))

class MPDManager(Thread):
    def __init__(self):
        super(MPDManager, self).__init__()
        self.devices = {}
        self.mpd_session = ctypes.c_void_p()

    def run(self):
        eftapi.EFT_CreateSession(ctypes.byref(self.mpd_session))
        eftapi.EFT_PutDeviceId(self.mpd_session, terminal_id.encode())
        while True:
            if self.terminal_connected(terminal_id):
                self.devices[terminal_id] = IoTDevice(terminal_id, 'mpd')
            elif terminal_id in self.devices:
                self.devices = {}
            time.sleep(20)

    def terminal_connected(self, terminal_id):
        eftapi.EFT_QueryStatus(self.mpd_session)
        eftapi.EFT_Complete(self.mpd_session, 1)  # Needed to read messages from driver
        device_status = ctypes.c_long()
        eftapi.EFT_GetDeviceStatusCode(self.mpd_session, ctypes.byref(device_status))
        return device_status.value in [0, 1]


conn = cups_connection()
PPDs = conn.getPPDs()
printers = conn.getPrinters()
cups_lock = Lock()  # We can only make one call to Cups at a time

mpdm = MPDManager()
terminal_id = helpers.read_file_first_line('odoo-six-payment-terminal.conf')
if terminal_id:
    try:
        subprocess.check_output(["pidof", "eftdvs"])  # Check if MPD server is running
    except subprocess.CalledProcessError:
        subprocess.Popen(["eftdvs", "/ConfigDir", "/usr/share/eftdvs/"])  # Start MPD server
    eftapi = ctypes.CDLL("eftapi.so")  # Library given by Six
    mpdm.daemon = True
    mpdm.start()
else:
    try:
        subprocess.check_call(["pkill", "-9", "eftdvs"])  # Check if MPD server is running
    except subprocess.CalledProcessError:
        pass

m = Manager()
m.daemon = True
m.start()

bm = BtManager()
bm.daemon = True
bm.start()

sm = SocketManager()
sm.daemon = True
sm.start()
