#!/usr/bin/python3
import logging
import time
from threading import Thread
import usb
import gatt
import subprocess
import netifaces as ni
import json
import re
from odoo import http
import urllib3
from odoo.http import request as httprequest
import datetime

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s %(levelname)s %(name)s: %(message)s')
_logger = logging.getLogger('dispatcher')

owner_dict = {}
last_ping = {}

class StatusController(http.Controller):

    @http.route('/hw_drivers/owner/check', type='json', auth='none', cors='*', csrf=False)
    def check_cantakeowner(self): #, devices, tab
        data = httprequest.jsonrequest
        for device in data['devices']:
            if owner_dict.get(device) and owner_dict[device] != data['tab']:
                before_date = datetime.datetime.now() - datetime.timedelta(seconds=10)
                if last_ping.get(owner_dict[device]) and last_ping.get(owner_dict[device]) > before_date:
                    return 'no'
                else:
                    old_tab = owner_dict[device]
                    for dev2 in owner_dict:
                        if owner_dict[dev2] == old_tab:
                            owner_dict[dev2] = ''
        return 'yes'

    @http.route('/hw_drivers/owner/take', type='json', auth='none', cors='*', csrf=False)
    def take_ownership(self): #, devices, tab
        data = httprequest.jsonrequest
        for device in data['devices']:
            owner_dict[device] = data['tab']
            last_ping[data['tab']] = datetime.datetime.now()
        return data['tab']

    @http.route('/hw_drivers/owner/ping', type='json', auth='none', cors='*', csrf=False)
    def ping_trigger(self): #, tab
        data = httprequest.jsonrequest
        ping_dict = {}
        last_ping[data['tab']] = datetime.datetime.now()
        for dev in data['devices']:
            if owner_dict.get(dev) and owner_dict[dev] == data['tab']:
                for driver_path in drivers:
                    if driver_path.find(dev) == 0 and drivers[driver_path].ping_value:
                        ping_dict[dev] = drivers[driver_path].ping_value
                        drivers[driver_path].ping_value = ''  # or set it to nothing
            else:
                ping_dict[dev] = 'STOP'
        return ping_dict

    @http.route('/hw_drivers/box/connect', type='json', auth='none', cors='*', csrf=False)
    def connect_box(self):
        data = httprequest.jsonrequest
        server = ""  # read from file
        try:
            f = open('/home/pi/odoo-remote-server.conf', 'r')
            for line in f:
                server += line
            f.close()
            server = server.split('\n')[0]
        except:
            server = ''
        if server:
            return 'This IoTBox has already been connected'
        else:
            iotname = ''
            token = data['token'].split('|')[1]
            url = data['token'].split('|')[0]
            reboot = 'noreboot'
            subprocess.call(['/home/pi/odoo/addons/point_of_sale/tools/posbox/configuration/connect_to_server.sh', url, iotname, token, reboot])
            send_iot_box_device(False)
            return 'IoTBox connected'

    @http.route('/hw_drivers/drivers/status', type='http', auth='none', cors='*')
    def status(self):
        result = "<html><head></head><body>List of drivers and values: <br/> <ul>"
        for path in drivers:
            result += "<li>" + path + ":" + str(drivers[path].value) + "</li>"
        result += "</ul>"
        result +=" </body></html>"
        return result

    @http.route('/hw_drivers/driverdetails/<string:identifier>', type='http', auth='none', cors='*')
    def statusdetail(self, identifier):
        for device in drivers:
            if device.find(identifier) != -1:
                return str(drivers[device].value)
        return ''

    @http.route('/hw_drivers/driveraction/<string:identifier>', type='json', auth='none', cors='*', csrf=False)
    def driveraction(self, identifier):
        data = httprequest.jsonrequest
        result = 'device not found'
        if data.get('action') == 'print':
            with open('/tmp/toprinter', 'w') as file:
                file.write(data['data'])
            subprocess.call("cat /tmp/toprinter | base64 -d | lp -d " + identifier, shell=True)
            result = 'ok'
        if data.get('action') == 'camera':
            cameras = subprocess.check_output("v4l2-ctl --list-devices", shell=True).decode('utf-8').split('\n\n')
            adrress = '/dev/video0'
            for camera in cameras:
                if camera:
                    camera = camera.split('\n\t')
                    serial = re.sub('[^a-zA-Z0-9 ]+', '', camera[0].split(': ')[0]).replace(' ','_')
                    if serial == data.get('identifier'):
                        adrress = camera[1]
            picture = subprocess.check_output("v4l2-ctl --list-formats-ext|grep 'Size'|awk '{print $3}'|sort -rn|awk NR==1", shell=True).decode('utf-8')
            subprocess.call("fswebcam -d " + adrress + " /tmp/testimage -r " + picture, shell=True)
            image_bytes = subprocess.check_output('cat /tmp/testimage | base64',shell=True)
            result = {'image': image_bytes}
        return result

    @http.route('/hw_drivers/send_iot_box', type='http', auth='none', cors='*')
    def send_iot_box(self):
        send_iot_box_device(False)
        return 'ok'

#----------------------------------------------------------
# Driver common interface
#----------------------------------------------------------
class Driver(Thread):
    ping_value = ""

    def supported(self):
        pass

    def value(self):
        pass

    def get_name(self):
        pass

    def get_connection(self):
        pass

    def action(self, action):
        pass

#----------------------------------------------------------
# Usb drivers
#----------------------------------------------------------
usbdrivers = []
drivers = {}

class UsbMetaClass(type):
    def __new__(cls, clsname, bases, attrs):
        newclass = super(UsbMetaClass, cls).__new__(cls, clsname, bases, attrs)
        usbdrivers.append(newclass)
        return newclass

class USBDriver(Driver,metaclass=UsbMetaClass):
    def __init__(self, dev):
        super(USBDriver, self).__init__()
        self.dev = dev
        self.value = ""

    def get_name(self):
        lsusb = str(subprocess.check_output('lsusb')).split("\\n")
        for usbpath in lsusb:  # Should filter on usb devices or inverse loops?
            device = self.dev
            if "%04x:%04x" % (device.idVendor, device.idProduct) in usbpath:
                return usbpath.split("%04x:%04x" % (device.idVendor, device.idProduct))[1]
        return str(device.idVendor) + ":" + str(device.idProduct)

    def get_connection(self):
        return 'direct'

    def value(self):
        return self.value


#----------------------------------------------------------
# Bluetooth
#----------------------------------------------------------
class GattBtManager(gatt.DeviceManager):

    def device_discovered(self, device):
        # TODO: need some kind of updated_devices mechanism or not?
        path = "bt_%s" % (device.mac_address,)
        if path not in drivers:
            for driverclass in btdrivers:
                d = driverclass(device = device, manager=self)
                if d.supported():
                    drivers[path] = d
                    d.connect()
                    send_iot_box_device(False)


class BtManager(Thread):
    gatt_manager = False

    def run(self):
        dm = GattBtManager(adapter_name='hci0')
        self.gatt_manager = dm
        dm.start_discovery()
        dm.run()

#----------------------------------------------------------
# Bluetooth drivers
#----------------------------------------------------------
btdrivers = []

class BtMetaClass(type):
    def __new__(cls, clsname, bases, attrs):
        newclass = super(BtMetaClass, cls).__new__(cls, clsname, bases, attrs)
        btdrivers.append(newclass)
        return newclass


class BtDriver(Driver, metaclass=BtMetaClass):


    def __init__(self, device, manager):
        super(BtDriver, self).__init__()
        self.dev = device
        self.manager = manager
        self.value = ''
        self.gatt_device = False

    def disconnect(self):
        path = "bt_%s" % (self.dev.mac_address,)
        del drivers[path]

    def get_name(self):
        return self.dev.alias()

    def value(self):
        return self.value

    def action(self, action):
        pass

    def get_connection(self):
        return 'bluetooth'

    def connect(self):
        pass






class USBDeviceManager(Thread):
    devices = {}
    def run(self):
        first_time = True
        send_iot_box_device(False)
        while 1:
            sendJSON = False
            devs = usb.core.find(find_all=True)
            updated_devices = {}
            for dev in devs:
                path =  "usb_%04x:%04x_%03d_%03d_" % (dev.idVendor, dev.idProduct, dev.bus, dev.address)
                updated_devices[path] = self.devices.get(path, dev)
            added = updated_devices.keys() - self.devices.keys()
            removed = self.devices.keys() - updated_devices.keys()
            self.devices = updated_devices
            if (removed):
                for path in list(drivers):
                    if (path in removed):
                        del drivers[path]
                        sendJSON = True
            for path in added:
                dev = updated_devices[path]
                for driverclass in usbdrivers:
                    d = driverclass(updated_devices[path])
                    if d.supported():
                        _logger.info('For device %s will be driven', path)
                        drivers[path] = d
                        # launch thread
                        d.daemon = True
                        d.start()
                        sendJSON = True
            if sendJSON or first_time:
                send_iot_box_device(send_printer = first_time)
                first_time = False
            time.sleep(3)
            




def send_iot_box_device(send_printer):
    maciotbox = subprocess.check_output("/sbin/ifconfig eth0 |grep -Eo ..\(\:..\){5}", shell=True).decode('utf-8').split('\n')[0]
    server = "" # read from file
    try:
        f = open('/home/pi/odoo-remote-server.conf', 'r')
        for line in f:
            server += line
        f.close()
    except: #In case the file does not exist
        server=''
    server = server.split('\n')[0]
    if server:
        url = server + "/iot/setup"
        interfaces = ni.interfaces()
        for iface_id in interfaces:
            iface_obj = ni.ifaddresses(iface_id)
            ifconfigs = iface_obj.get(ni.AF_INET, [])
            for conf in ifconfigs:
                if conf.get('addr') and conf.get('addr') != '127.0.0.1':
                    ips = conf.get('addr')
                    break

        # Build device JSON
        devicesList = {}
        for path in drivers:
            device_name = drivers[path].get_name()
            device_connection = drivers[path].get_connection()
            identifier = path.split('_')[0] + '_' + path.split('_')[1]
            devicesList[identifier] = {'name': device_name,
                                 'type': 'device',
                                 'connection': device_connection}

        # Build camera JSON
        try:
            cameras = subprocess.check_output("v4l2-ctl --list-devices", shell=True).decode('utf-8').split('\n\n')
            for camera in cameras:
                if camera:
                    camera = camera.split('\n\t')
                    serial = re.sub('[^a-zA-Z0-9 ]+', '', camera[0].split(': ')[0]).replace(' ','_')
                    devicesList[serial] = {
                                            'name': camera[0].split(': ')[0],
                                            'connection': 'direct',
                                            'type': 'camera'
                                        }
        except:
            pass

        # Build printer JSON
        printerList = {}
        if send_printer:
            printers = subprocess.check_output("sudo lpinfo -lv", shell=True).decode('utf-8').split('Device')
            printers_installed = ''
            try:
                printers_installed = subprocess.check_output("sudo lpstat -a", shell=True).decode('utf-8')
            except:
                pass
            for printer in printers:
                printerTab = printer.split('\n')
                if printer and printerTab[4].split('=')[1] != ' ' or 'lpd://' in printerTab[0]:
                    device_connection = printerTab[1].split('= ')[1]
                    model = ''
                    for device_id in printerTab[4].split('= ')[1].split(';'):
                        if any(x in device_id for x in ['MDL','MODEL']):
                            model = device_id.split(':')[1]
                    serial = re.sub('[^a-zA-Z0-9 ]+', '', model).replace(' ','_')
                    identifier = ''
                    if device_connection == 'direct':
                        identifier = serial + '_' + maciotbox  #name + macIOTBOX
                    elif device_connection == 'network' and 'socket' in printerTab[0]:
                        socketIP = printerTab[0].split('://')[1]
                        macprinter = subprocess.check_output("arp -a " + socketIP + " |awk NR==1'{print $4}'", shell=True).decode('utf-8').split('\n')[0]
                        identifier = macprinter  # macPRINTER
                    elif device_connection == 'network' and 'lpd' in printerTab[0]:
                        identifier = re.sub('[^a-zA-Z0-9 ]+', '', printerTab[0].split('://')[1])
                        model = printerTab[2].split('= ')[1]
                    elif device_connection == 'network' and 'dnssd' in printerTab[0]:
                        hostname_printer = subprocess.check_output("ippfind -n \"" + model + "\" | awk \'{split($0,a,\"/\"); print a[3]}\' | awk \'{split($0,b,\":\"); print b[1]}\'", shell=True).decode('utf-8').split('\n')[0]
                        if hostname_printer:
                            macprinter = subprocess.check_output("arp -a " + hostname_printer + " |awk NR==1'{print $4}'", shell=True).decode('utf-8').split('\n')[0]
                            identifier = macprinter  # macprinter

                    identifier = identifier.replace(':','_')
                    if identifier and identifier not in printerList:
                        printerList[identifier] = {
                                            'name': model,
                                            'connection': device_connection,
                                            'type': 'printer'
                        }

                        if identifier not in printers_installed:
                            # install these printers
                            try:
                                ppd = subprocess.check_output("sudo lpinfo -m |grep '" + model + "'", shell=True).decode('utf-8').split('\n')
                                if len(ppd) > 2:
                                    subprocess.call("sudo lpadmin -p '" + identifier + "' -E -v '" + printerTab[0].split('= ')[1] + "'", shell=True)
                                else:
                                    subprocess.call("sudo lpadmin -p '" + identifier + "' -E -v '" + printerTab[0].split('= ')[1] + "' -m '" + ppd[0].split(' ')[0] + "'", shell=True)
                            except:
                                subprocess.call("sudo lpadmin -p '" + identifier + "' -E -v '" + printerTab[0].split('= ')[1] + "'", shell=True)
            subprocess.call('> /tmp/printers', shell=True)
            for printer in printerList:
                subprocess.call('echo "' + printerList[printer]['name'] + '" >> /tmp/printers', shell=True)

        if devicesList:
            subprocess.call('> /tmp/devices', shell=True)
            for device in devicesList:
                subprocess.call('echo "' + str(device) + '|' + devicesList[device]['name'] + '" >> /tmp/devices', shell=True)

        #build JSON with all devices
        hostname = subprocess.check_output('hostname').decode('utf-8').split('\n')[0]
        token = "" # read from file
        try:
            f = open('/home/pi/token', 'r')
            for line in f:
                token += line
            f.close()
        except: #In case the file does not exist
            token=''
        token = token.split('\n')[0]
        data = {'name': hostname,'identifier': maciotbox, 'ip': ips, 'token': token}
        devicesList.update(printerList)
        data['devices'] = devicesList
        data_json = json.dumps(data).encode('utf8')
        headers = {'Content-type': 'application/json', 'Accept': 'text/plain'}
        urllib3.disable_warnings()
        http = urllib3.PoolManager(cert_reqs='CERT_NONE')
        req = False
        try:
            req = http.request('POST',
                                url,
                                body=data_json,
                                headers=headers)
        except Exception as e:
            _logger.warning('Could not reach configured server')
            _logger.error('A error encountered : %s ' % e)


