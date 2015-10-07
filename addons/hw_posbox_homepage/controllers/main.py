# -*- coding: utf-8 -*-
import logging
import os
import time
import werkzeug
import subprocess
from os import listdir

import openerp
from openerp import http
from openerp.http import request
from openerp.tools.translate import _

_logger = logging.getLogger(__name__)

index_template = """
<!DOCTYPE HTML>
<html>
    <head>
        <title>Odoo's PosBox</title>
        <style>
        body {
            width: 480px;
            margin: 60px auto;
            font-family: sans-serif;
            text-align: justify;
            color: #6B6B6B;
        }
        </style>
    </head>
    <body>
        <h1>Your PosBox is up and running</h1>
        <p>
        The PosBox is an hardware adapter that allows you to use 
        receipt printers and barcode scanners with Odoo's Point of
        Sale, <b>version 8.0 or later</b>. You can start an <a href='https://www.odoo.com/start'>online free trial</a>,
        or <a href='https://www.odoo.com/start?download'>download and install</a> it yourself.
        </p>
        <p>
        For more information on how to setup the Point of Sale with
        the PosBox, please refer to <a href='/hw_proxy/static/doc/manual.pdf'>the manual</a>.
        </p>
        <p>
        To see the status of the connected hardware, please refer 
        to the <a href='/hw_proxy/status'>hardware status page</a>.
        </p>
        <p>
        Wi-Fi can be configured by visiting the <a href='/wifi'>Wi-Fi configuration page</a>.
        </p>
        <p>
        The PosBox software installed on this posbox is <b>version 13</b>,
        the posbox version number is independent from Odoo. You can upgrade
        the software on the <a href='/hw_proxy/upgrade/'>upgrade page</a>.
        </p>
        <p>For any other question, please contact the Odoo support at <a href='mailto:support@odoo.com'>support@odoo.com</a>
        </p>
    </body>
</html>

"""


class PosboxHomepage(openerp.addons.web.controllers.main.Home):
    @http.route('/', type='http', auth='none', website=True)
    def index(self):
        #return request.render('hw_posbox_homepage.index',mimetype='text/html')
        return index_template

    @http.route('/wifi', type='http', auth='none', website=True)
    def wifi(self):
        wifi_template = """
<!DOCTYPE HTML>
<html>
    <head>
        <title>Wifi configuration</title>
        <style>
        body {
            width: 480px;
            margin: 60px auto;
            font-family: sans-serif;
            text-align: justify;
            color: #6B6B6B;
        }
        </style>
    </head>
    <body>
        <h1>Configure wifi</h1>
        <p>
        Here you can configure how the posbox should connect to wireless networks.
        Currently only Open and WPA networks are supported. When enabling the persistent checkbox,
        the chosen network will be saved and the posbox will attempt to connect to it every time it boots.
        </p>
        <form action='/wifi_connect' method='POST'>
            <table>
                <tr>
                    <td>
                        ESSID:
                    </td>
                    <td>
                        <select name="essid">
"""
        try:
            f = open('/tmp/scanned_networks.txt', 'r')
            for line in f:
                line = line.rstrip()
                line = werkzeug.utils.escape(line)
                wifi_template += '<option value="' + line + '">' + line + '</option>\n'
            f.close()
        except IOError:
            _logger.warning("No /tmp/scanned_networks.txt")
        wifi_template += """
                        </select>
                    </td>
                </tr>
                <tr>
                    <td>
                        Password:
                    </td>
                    <td>
                        <input type="password" name="password" placeholder="optional"/>
                    </td>
                </tr>
                <tr>
                    <td>
                        Persistent:
                    </td>
                    <td>
                        <input type="checkbox" name="persistent"/>
                    </td>
                </tr>
                <tr>
                    <td/>
                    <td>
                        <input type="submit" value="connect"/>
                    </td>
                </tr>
            </table>
        </form>
        <p>
                You can clear the persistent configuration by clicking below:
                <form action='/wifi_clear'>
                        <input type="submit" value="Clear persistent network configuration"/>
                </form>
        </p>
        <form>
    </body>
</html>
"""
        return wifi_template

    @http.route('/wifi_connect', type='http', auth='none', cors='*')
    def connect_to_wifi(self, essid, password, persistent=False):
        if persistent:
                persistent = "1"
        else:
                persistent = ""

        subprocess.call(['/home/pi/odoo/addons/point_of_sale/tools/posbox/configuration/connect_to_wifi.sh', essid, password, persistent])
        return "connecting to " + essid

    @http.route('/wifi_clear', type='http', auth='none', cors='*')
    def clear_wifi_configuration(self):
        os.system('/home/pi/odoo/addons/point_of_sale/tools/posbox/configuration/clear_wifi_configuration.sh')
        return "configuration cleared"
