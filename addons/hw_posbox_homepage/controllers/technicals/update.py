
import logging
import os
import subprocess
import threading

from odoo import http
from odoo.http import Response
from odoo.addons.hw_drivers.tools import helpers
from odoo.addons.hw_posbox_homepage.controllers.technical import IoTTechnicalPage, get_menu

_logger = logging.getLogger(__name__)


class IoTBoxTechnicalUpgradePage(http.Controller, IoTTechnicalPage):
    _menu = get_menu(__name__)

    def __init__(self):
        super().__init__()
        self.updating = threading.Lock()

    def clean_partition(self):
        subprocess.check_call(['sudo', 'bash', '-c', '. /home/pi/odoo/addons/point_of_sale/tools/posbox/configuration/upgrade.sh; cleanup'])

    @http.route(_menu.url, type='http', auth='none')
    def upgrade(self):
        commit = subprocess.check_output(["git", "--work-tree=/home/pi/odoo/", "--git-dir=/home/pi/odoo/.git", "log", "-1"]).decode('utf-8').replace("\n", "<br/>")
        flashToVersion = helpers.check_image()
        actualVersion = helpers.get_version()
        if flashToVersion:
            flashToVersion = '%s.%s' % (flashToVersion.get('major', ''), flashToVersion.get('minor', ''))
        return self.render(
            loading_message='Updating IoT box',
            commit=commit,
            flashToVersion=flashToVersion,
            actualVersion=actualVersion,
        )

    @http.route('/hw_proxy/perform_upgrade', type='http', auth='none')
    def perform_upgrade(self):
        self.updating.acquire()
        os.system('/home/pi/odoo/addons/point_of_sale/tools/posbox/configuration/posbox_update.sh')
        self.updating.release()
        return 'SUCCESS'

    @http.route('/hw_proxy/get_version', type='http', auth='none')
    def check_version(self):
        return helpers.get_version()

    @http.route('/hw_proxy/perform_flashing_create_partition', type='http', auth='none')
    def perform_flashing_create_partition(self):
        try:
            response = subprocess.check_output(['sudo', 'bash', '-c', '. /home/pi/odoo/addons/point_of_sale/tools/posbox/configuration/upgrade.sh; create_partition']).decode().split('\n')[-2]
            if response in ['Error_Card_Size', 'Error_Upgrade_Already_Started']:
                raise Exception(response)
            return Response('success', status=200)
        except subprocess.CalledProcessError as e:
            raise Exception(e.output)
        except Exception as e:
            _logger.exception('Could not perform flashing create partition')
            return Response(str(e), status=500)

    @http.route('/hw_proxy/perform_flashing_download_raspios', type='http', auth='none')
    def perform_flashing_download_raspios(self):
        try:
            response = subprocess.check_output(['sudo', 'bash', '-c', '. /home/pi/odoo/addons/point_of_sale/tools/posbox/configuration/upgrade.sh; download_raspios']).decode().split('\n')[-2]
            if response == 'Error_Raspios_Download':
                raise Exception(response)
            return Response('success', status=200)
        except subprocess.CalledProcessError as e:
            raise Exception(e.output)
        except Exception as e:
            self.clean_partition()
            _logger.exception('Could not perform flashing download raspios')
            return Response(str(e), status=500)

    @http.route('/hw_proxy/perform_flashing_copy_raspios', type='http', auth='none')
    def perform_flashing_copy_raspios(self):
        try:
            response = subprocess.check_output(['sudo', 'bash', '-c', '. /home/pi/odoo/addons/point_of_sale/tools/posbox/configuration/upgrade.sh; copy_raspios']).decode().split('\n')[-2]
            if response == 'Error_Iotbox_Download':
                raise Exception(response)
            return Response('success', status=200)
        except subprocess.CalledProcessError as e:
            raise Exception(e.output)
        except Exception as e:
            self.clean_partition()
            _logger.exception('Could not perform flashing copy raspios')
            return Response(str(e), status=500)
