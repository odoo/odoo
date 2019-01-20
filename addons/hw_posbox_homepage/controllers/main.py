# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import json
import jinja2
import subprocess
import socket
import sys
import netifaces as ni
import odoo
from odoo import http
import zipfile
import io
import os
from odoo.tools import misc
import urllib3

from uuid import getnode as get_mac
from odoo.addons.hw_proxy.controllers import main as hw_proxy

_logger = logging.getLogger(__name__)

if hasattr(sys, 'frozen'):
    # When running on compiled windows binary, we don't have access to package loader.
    path = os.path.realpath(os.path.join(os.path.dirname(__file__), '..', 'views'))
    loader = jinja2.FileSystemLoader(path)
else:
    loader = jinja2.PackageLoader('odoo.addons.hw_posbox_homepage', "views")

jinja_env = jinja2.Environment(loader=loader, autoescape=True)
jinja_env.filters["json"] = json.dumps

homepage_template = jinja_env.get_template('homepage.html')
server_config_template = jinja_env.get_template('server_config.html')
wifi_config_template = jinja_env.get_template('wifi_config.html')
driver_list_template = jinja_env.get_template('driver_list.html')
remote_connect_template = jinja_env.get_template('remote_connect.html')
configure_wizard_template = jinja_env.get_template('configure_wizard.html')

class IoTboxHomepage(odoo.addons.web.controllers.main.Home):

    def get_ip_iotbox(self):
        interfaces = ni.interfaces()
        for iface_id in interfaces:
            iface_obj = ni.ifaddresses(iface_id)
            ifconfigs = iface_obj.get(ni.AF_INET, [])
            for conf in ifconfigs:
                if conf.get('addr') and conf.get('addr') != '127.0.0.1':
                    ips = conf.get('addr')
                    break
        return ips

    def get_hw_screen_message(self):
        return """
        <p>
            The activate the customer display feature, you will need to reinstall the IoT Box software.
            You can find the latest images on the <a href="http://nightly.odoo.com/master/posbox/">Odoo Nightly builds</a> website.
            Make sure to download at least the version 16.<br/>
            Odoo version 11, or above, is required to use the customer display feature.
        </p>
        """

    def get_pos_device_status(self):
        statuses = {}
        for driver in hw_proxy.drivers:
            statuses[driver] = hw_proxy.drivers[driver].get_status()
        return statuses

    def get_server_status(self):
        server_template = ""
        try:
            f = open('/home/pi/odoo-remote-server.conf', 'r')
            for line in f:
                server_template += line
            f.close()
        except:
            return ''

        return server_template.split('\n')[0]

    def get_homepage_data(self):
        hostname = str(socket.gethostname())
        mac = get_mac()
        h = iter(hex(mac)[2:].zfill(12))
        ssid = subprocess.check_output('iwconfig 2>&1 | grep \'ESSID:"\' | sed \'s/.*"\\(.*\\)"/\\1/\'', shell=True).decode('utf-8').rstrip()
        wired = subprocess.check_output('cat /sys/class/net/eth0/operstate', shell=True).decode('utf-8').strip('\n')
        if wired == 'up':
            network = 'Ethernet'
        elif ssid:
            if self.get_ip_iotbox() == '10.11.12.1':
                network = 'Wifi access point'
            else:
                network = 'Wifi : ' + ssid
        else:
            network = 'Not Connected'

        pos_device = self.get_pos_device_status()
        iot_device = []
        for status in pos_device:
            if pos_device[status]['status'] == 'connected':
                iot_device.append({
                    'name': status,
                    'type': 'device',
                    'message': ' '.join(pos_device[status]['messages'])
                })

        hdmi_name = subprocess.check_output('tvservice -n', shell=True).decode('utf-8')
        if hdmi_name.find('=') != -1:
            hdmi_name = hdmi_name.split('=')[1]
            hdmi_message = subprocess.check_output('tvservice -s', shell=True).decode('utf-8')
            iot_device.append({
                    'name': 'display : ' + hdmi_name,
                    'type': 'device',
                    'message': hdmi_message
                })

        try:
            f = open('/tmp/devices', 'r')
            for line in f:
                url = 'http://' + self.get_ip_iotbox() + ':8069/hw_drivers/driverdetails/' + line.split('|')[0]
                urllib3.disable_warnings()
                http = urllib3.PoolManager(cert_reqs='CERT_NONE')
                value = ''
                try:
                    req = http.request('GET', url)
                except Exception as e:
                    req = ''
                    _logger.warning('Could not reach configured server')
                    _logger.error('A error encountered : %s ' % e)

                if req:
                    value = req.data.decode('utf-8')
                iot_device.append({
                                    'name': line.split('|')[1],
                                    'message': line.split('|')[0] + ' : ' + value,
                                    'type': 'device',
                                    })
            f.close()
        except:
            pass

        try:
            f = open('/tmp/printers', 'r')
            for line in f:
                iot_device.append({
                                    'name': line,
                                    'type': 'printer',
                                    })
            f.close()
        except:
            pass

        return {
            'hostname': hostname,
            'ip': self.get_ip_iotbox(),
            'mac': ":".join(i + next(h) for i in h),
            'iot_device_status': iot_device,
            'server_status': self.get_server_status() or 'Not Configured',
            'network_status': network,
            }

    @http.route('/', type='http', auth='none')
    def index(self):
        if (os.path.isfile('/home/pi/wifi_network.txt') == False or os.path.isfile('/home/pi/odoo-remote-server.conf') == False) and self.get_ip_iotbox() == '10.11.12.1':
            return configure_wizard_template.render({
                'title': 'Configure IoT Box',
                'breadcrumb': 'Configure IoT Box',
                'loading_message': 'Configuring your IoT Box',
                'ssid': self.get_wifi_essid(),
                'server': self.get_server_status(),
                'hostname': subprocess.check_output('hostname').decode('utf-8'),
                })
        else:
            return homepage_template.render(self.get_homepage_data())

    @http.route('/list_drivers', type='http', auth='none', website=True)
    def list_drivers(self):
        drivers_list = []
        for driver in os.listdir("/home/pi/odoo/addons/hw_drivers/drivers"):
            if driver != '__pycache__':
                drivers_list.append(driver)
        return driver_list_template.render({
            'title': "Odoo's IoT Box - Drivers list",
            'breadcrumb': 'Drivers list',
            'drivers_list': drivers_list,
        })

    @http.route('/load_drivers', type='http', auth='none', website=True)
    def load_drivers(self):
        subprocess.call("sudo mount -o remount,rw /", shell=True)
        subprocess.call("sudo mount -o remount,rw /root_bypass_ramdisks", shell=True)

        mac = subprocess.check_output("/sbin/ifconfig eth0 |grep -Eo ..\(\:..\){5}", shell=True).decode('utf-8').split('\n')[0]

        #response = requests.get(url, auth=(username, db_uuid.split('\n')[0]), stream=True)
        server = self.get_server_status()
        if server:
            urllib3.disable_warnings()
            pm = urllib3.PoolManager(cert_reqs='CERT_NONE')
            resp = False
            server = server + '/iot/get_drivers'
            try:
                resp = pm.request('POST',
                                   server,
                                   fields={'mac': mac})
            except Exception as e:
                req = ''
                _logger.warning('Could not reach configured server')
                _logger.error('A error encountered : %s ' % e)
            if resp and resp.data:
                zip_file = zipfile.ZipFile(io.BytesIO(resp.data))
                zip_file.extractall("/home/pi/odoo/addons/hw_drivers/drivers")
        subprocess.call("sudo service odoo restart", shell=True)
        subprocess.call("sudo mount -o remount,ro /", shell=True)
        subprocess.call("sudo mount -o remount,ro /root_bypass_ramdisks", shell=True)

        return "<meta http-equiv='refresh' content='20; url=http://" + self.get_ip_iotbox() + ":8069/list_drivers'>"

    def get_wifi_essid(self):
        wifi_options = []
        try:
            f = open('/tmp/scanned_networks.txt', 'r')
            for line in f:
                line = line.rstrip()
                line = misc.html_escape(line)
                if line not in wifi_options:
                    wifi_options.append(line)
            f.close()
        except IOError:
            _logger.warning("No /tmp/scanned_networks.txt")
        return wifi_options

    @http.route('/wifi', type='http', auth='none', website=True)
    def wifi(self):
        return wifi_config_template.render({
            'title': 'Wifi configuration',
            'breadcrumb': 'Configure Wifi',
            'loading_message': 'Connecting to Wifi',
            'ssid': self.get_wifi_essid(),
        })

    @http.route('/wifi_connect', type='http', auth='none', cors='*', csrf=False)
    def connect_to_wifi(self, essid, password, persistent=False):
        if persistent:
                persistent = "1"
        else:
                persistent = ""

        subprocess.call(['/home/pi/odoo/addons/point_of_sale/tools/posbox/configuration/connect_to_wifi.sh', essid, password, persistent])
        server = self.get_server_status()
        res_payload = {
            'message': 'Connecting to ' + essid,
        }
        if server:
            res_payload['server'] = {
                'url': server,
                'message': 'Redirect to Odoo Server'
            }

        return json.dumps(res_payload)

    @http.route('/wifi_clear', type='http', auth='none', cors='*', csrf=False)
    def clear_wifi_configuration(self):
        os.system('/home/pi/odoo/addons/point_of_sale/tools/posbox/configuration/clear_wifi_configuration.sh')

        return "<meta http-equiv='refresh' content='0; url=http://" + self.get_ip_iotbox() + ":8069'>"

    @http.route('/server_clear', type='http', auth='none', cors='*', csrf=False)
    def clear_server_configuration(self):
        os.system('/home/pi/odoo/addons/point_of_sale/tools/posbox/configuration/clear_server_configuration.sh')

        return "<meta http-equiv='refresh' content='0; url=http://" + self.get_ip_iotbox() + ":8069'>"

    @http.route('/drivers_clear', type='http', auth='none', cors='*', csrf=False)
    def clear_drivers_list(self):
        os.system('/home/pi/odoo/addons/point_of_sale/tools/posbox/configuration/clear_drivers_list.sh')

        return "<meta http-equiv='refresh' content='0; url=http://" + self.get_ip_iotbox() + ":8069/list_drivers'>"

    @http.route('/server_connect', type='http', auth='none', cors='*', csrf=False)
    def connect_to_server(self, token, iotname):
        url = token.split('|')[0]
        token = token.split('|')[1]
        reboot = 'reboot'
        subprocess.call(['/home/pi/odoo/addons/point_of_sale/tools/posbox/configuration/connect_to_server.sh', url, iotname, token, reboot])
        return 'http://' + self.get_ip_iotbox() + ':8069'

    @http.route('/steps', type='http', auth='none', cors='*', csrf=False)
    def step_by_step_configure_page(self):
        return configure_wizard_template.render({
            'title': 'Configure IoT Box',
            'breadcrumb': 'Configure IoT Box',
            'loading_message': 'Configuring your IoT Box',
            'ssid': self.get_wifi_essid(),
            'server': self.get_server_status(),
            'hostname': subprocess.check_output('hostname').decode('utf-8').strip('\n'),
        })

    @http.route('/step_configure', type='http', auth='none', cors='*', csrf=False)
    def step_by_step_configure(self, token, iotname, essid, password, persistent=False):
        if token:
            url = token.split('|')[0]
            token = token.split('|')[1]
        else:
            url = ''
        subprocess.call(['/home/pi/odoo/addons/point_of_sale/tools/posbox/configuration/connect_to_server_wifi.sh',url, iotname, token, essid, password, persistent])
        return url

    # Set server address
    @http.route('/server', type='http', auth='none', website=True)
    def server(self):
        return server_config_template.render({
            'title': 'IoT -> Odoo server configuration',
            'breadcrumb': 'Configure Odoo Server',
            'hostname': subprocess.check_output('hostname').decode('utf-8').strip('\n'),
            'server_status': self.get_server_status() or 'Not configured yet',
            'loading_message': 'Configure Domain Server'
        })

    @http.route('/remote_connect', type='http', auth='none', cors='*')
    def remote_connect(self):
        return remote_connect_template.render({
            'title': 'Remote debugging',
            'breadcrumb': 'Remote Debugging',
        })

    @http.route('/enable_ngrok', type='http', auth='none', cors='*', csrf=False)
    def enable_ngrok(self, auth_token):
        if subprocess.call(['pgrep', 'ngrok']) == 1:
            subprocess.Popen(['ngrok', 'tcp', '-authtoken', auth_token, '-log', '/tmp/ngrok.log', '22'])
            return 'starting with ' + auth_token
        else:
            return 'already running'
