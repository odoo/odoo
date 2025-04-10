# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import os
import subprocess
import threading

from odoo.http import Response
from odoo.addons.hw_drivers.tools import helpers, route
from odoo.addons.web.controllers.home import Home

_logger = logging.getLogger(__name__)


class IoTboxHomepage(Home):
    def __init__(self):
        super(IoTboxHomepage,self).__init__()
        self.updating = threading.Lock()

    def clean_partition(self):
        subprocess.check_call(['sudo', 'bash', '-c', '. /home/pi/odoo/addons/iot_box_image/configuration/upgrade.sh; cleanup'])

    @route.iot_route('/hw_proxy/perform_upgrade', type='http')
    def perform_upgrade(self):
        self.updating.acquire()
        os.system('/home/pi/odoo/addons/iot_box_image/configuration/checkout.sh')
        self.updating.release()
        return 'SUCCESS'

    @route.iot_route('/hw_proxy/get_version', type='http')
    def check_version(self):
        return helpers.get_version()

    @route.iot_route('/hw_proxy/perform_flashing_create_partition', type='http')
    def perform_flashing_create_partition(self):
        try:
            response = subprocess.check_output(['sudo', 'bash', '-c', '. /home/pi/odoo/addons/iot_box_image/configuration/upgrade.sh; create_partition']).decode().split('\n')[-2]
            if response in ['Error_Card_Size', 'Error_Upgrade_Already_Started']:
                raise Exception(response)
            return Response('success', status=200)
        except subprocess.CalledProcessError as e:
            raise Exception(e.output)
        except Exception as e:
            _logger.exception("Flashing create partition failed")
            return Response(str(e), status=500)

    @route.iot_route('/hw_proxy/perform_flashing_download_raspios', type='http')
    def perform_flashing_download_raspios(self):
        try:
            response = subprocess.check_output(['sudo', 'bash', '-c', '. /home/pi/odoo/addons/iot_box_image/configuration/upgrade.sh; download_raspios']).decode().split('\n')[-2]
            if response == 'Error_Raspios_Download':
                raise Exception(response)
            return Response('success', status=200)
        except subprocess.CalledProcessError as e:
            raise Exception(e.output)
        except Exception as e:
            self.clean_partition()
            _logger.exception("Flashing download raspios failed")
            return Response(str(e), status=500)

    @route.iot_route('/hw_proxy/perform_flashing_copy_raspios', type='http')
    def perform_flashing_copy_raspios(self):
        try:
            response = subprocess.check_output(['sudo', 'bash', '-c', '. /home/pi/odoo/addons/iot_box_image/configuration/upgrade.sh; copy_raspios']).decode().split('\n')[-2]
            if response == 'Error_Iotbox_Download':
                raise Exception(response)
            return Response('success', status=200)
        except subprocess.CalledProcessError as e:
            raise Exception(e.output)
        except Exception as e:
            self.clean_partition()
            _logger.exception("Flashing copy raspios failed")
            return Response(str(e), status=500)
