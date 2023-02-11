# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from traceback import format_exc

from dbus.mainloop.glib import DBusGMainLoop
import json
import logging
import socket
from threading import Thread
import time
import urllib3

from odoo.addons.hw_drivers.tools import helpers

_logger = logging.getLogger(__name__)

drivers = []
interfaces = {}
iot_devices = {}


class Manager(Thread):
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
                'version': helpers.get_version(),
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
            data = {'params': {'iot_box': iot_box, 'devices': devices_list,}}
            # disable certifiacte verification
            urllib3.disable_warnings()
            http = urllib3.PoolManager(cert_reqs='CERT_NONE')
            try:
                http.request(
                    'POST',
                    server + "/iot/setup",
                    body=json.dumps(data).encode('utf8'),
                    headers={
                        'Content-type': 'application/json',
                        'Accept': 'text/plain',
                    },
                )
            except Exception as e:
                _logger.error('Could not reach configured server')
                _logger.error('A error encountered : %s ' % e)
        else:
            _logger.warning('Odoo server not set')

    def run(self):
        """
        Thread that will load interfaces and drivers and contact the odoo server with the updates
        """

        helpers.check_git_branch()
        helpers.check_certificate()

        # We first add the IoT Box to the connected DB because IoT handlers cannot be downloaded if
        # the identifier of the Box is not found in the DB. So add the Box to the DB.
        self.send_alldevices()
        helpers.download_iot_handlers()
        helpers.load_iot_handlers()

        # Start the interfaces
        for interface in interfaces.values():
            i = interface()
            i.daemon = True
            i.start()

        # Check every 3 secondes if the list of connected devices has changed and send the updated
        # list to the connected DB.
        self.previous_iot_devices = []
        while 1:
            try:
                if iot_devices != self.previous_iot_devices:
                    self.send_alldevices()
                    self.previous_iot_devices = iot_devices.copy()
                time.sleep(3)
            except:
                # No matter what goes wrong, the Manager loop needs to keep running
                _logger.error(format_exc())


# Must be started from main thread
DBusGMainLoop(set_as_default=True)

manager = Manager()
manager.daemon = True
manager.start()
