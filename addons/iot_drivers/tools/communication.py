import logging
import platform
import pprint
import time

from odoo.addons.iot_drivers import main
from odoo.addons.iot_drivers.tools import helpers
from odoo.addons.iot_drivers.server_logger import close_server_log_sender_handler

_logger = logging.getLogger(__name__)


def handle_message(message_type: str, **kwargs: dict) -> dict:
    device_identifier = kwargs.get('device_identifier')
    base_response = {
        'session_id': kwargs.get('session_id', '0'),
        'iot_box_identifier': helpers.get_identifier(),
        'device_identifier': device_identifier,
        'time': time.time(),
    }

    match message_type:
        case 'iot_action':
            if device_identifier in main.iot_devices:
                _logger.info("Received message of type %s:\n%s", message_type, pprint.pformat(kwargs))
                main.iot_devices[device_identifier].action(kwargs)
                return {}
            # Notify the controller that the device is not connected
            return {**base_response, 'status': 'disconnected'}
        case 'server_clear':
            helpers.disconnect_from_server()
            close_server_log_sender_handler()
        case 'server_update':
            helpers.update_conf({
                'remote_server': kwargs['server_url']
            })
            helpers.get_odoo_server_url.cache_clear()
        case 'restart_odoo':
            helpers.odoo_restart()
        case 'remote_debug':
            if platform.system() == 'Windows':
                return {}
            if not kwargs.get("status"):
                helpers.toggle_remote_connection(kwargs.get("token", ""))
                time.sleep(1)
            return {
                **base_response,
                'device_identifier': None,
                'status': 'success',
                'result': {'enabled': helpers.is_ngrok_enabled()}
            }
        case _:
            pass
    return {}
