
import logging
import os
import subprocess
import threading

from werkzeug.exceptions import InternalServerError

from odoo import http
from odoo.http import Response
from odoo.addons.hw_drivers.tools import helpers
from odoo.addons.hw_posbox_homepage.controllers.jinja import render_template


_logger = logging.getLogger(__name__)


class IoTTechnicalUpgradePage(http.Controller):
    def __init__(self):
        super().__init__()
        self.updating = threading.Lock()

    def clean_partition(self):
        subprocess.check_call(['sudo', 'bash', '-c', '. /home/pi/odoo/addons/point_of_sale/tools/posbox/configuration/upgrade.sh; cleanup'])

    @http.route('/hw_proxy/upgrade', type='http', auth='none')
    def upgrade(self):
        commit = subprocess.check_output(["git", "--work-tree=/home/pi/odoo/", "--git-dir=/home/pi/odoo/.git", "log", "-1"]).decode('utf-8').replace("\n", "<br/>")
        flashToVersion = helpers.check_image()
        actualVersion = helpers.get_version()
        if flashToVersion:
            flashToVersion = '%s.%s' % (flashToVersion.get('major', ''), flashToVersion.get('minor', ''))
        return render_template("technical/update.jinja2",
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

    def _raise_error(self, message):
        _logger.error(message)
        return InternalServerError(message)

    @http.route('/hw_proxy/perform_flashing_create_partition', type='http', auth='none')
    def perform_flashing_create_partition(self):
        try:
            response = subprocess.check_output(['sudo', 'bash', '-c', '. /home/pi/odoo/addons/point_of_sale/tools/posbox/configuration/upgrade.sh; create_partition']).decode().split('\n')[-2]
            if response in ['Error_Card_Size', 'Error_Upgrade_Already_Started']:
                return self._raise_error(response)
            return Response('success', status=200)
        except subprocess.CalledProcessError as e:
            return self._raise_error(e.output)
        except Exception as e:
            _logger.exception('Could not perform flashing create partition')
            return self._raise_error(str(e))

    @http.route('/hw_proxy/perform_flashing_download_raspios', type='http', auth='none')
    def perform_flashing_download_raspios(self):
        try:
            response = subprocess.check_output(['sudo', 'bash', '-c', '. /home/pi/odoo/addons/point_of_sale/tools/posbox/configuration/upgrade.sh; download_raspios']).decode().split('\n')[-2]
            if response == 'Error_Raspios_Download':
                return self._raise_error(response)
            return Response('success', status=200)
        except subprocess.CalledProcessError as e:
            return self._raise_error(e.output)
        except Exception as e:
            self.clean_partition()
            _logger.exception('Could not perform flashing download raspios')
            return self._raise_error(str(e))

    @http.route('/hw_proxy/perform_flashing_copy_raspios', type='http', auth='none')
    def perform_flashing_copy_raspios(self):
        try:
            response = subprocess.check_output(['sudo', 'bash', '-c', '. /home/pi/odoo/addons/point_of_sale/tools/posbox/configuration/upgrade.sh; copy_raspios']).decode().split('\n')[-2]
            if response == 'Error_Iotbox_Download':
                return self._raise_error(response)
            return Response('success', status=200)
        except subprocess.CalledProcessError as e:
            return self._raise_error(e.output)
        except Exception as e:
            self.clean_partition()
            _logger.exception('Could not perform flashing copy raspios')
            return self._raise_error(str(e))
