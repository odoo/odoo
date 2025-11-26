import logging
import time

from odoo.addons.iot_drivers import main
from odoo.addons.iot_drivers.tools import helpers, system
from odoo.addons.iot_drivers.tools.system import IS_WINDOWS, IOT_IDENTIFIER
from odoo.addons.iot_drivers.server_logger import server_logger

_logger = logging.getLogger(__name__)


def handle_message(message_type: str, **kwargs: dict) -> dict:
    """General handler for messages received from the Odoo server either
    via WebSocket or HTTP.

    :param message_type: The type of message received.
    :param kwargs: Additional parameters passed with the message.
    :return: A dictionary response based on the message type and processing.
    """
    device_identifier = kwargs.get('device_identifier', IOT_IDENTIFIER)
    base_response = {
        'owner': kwargs.get('session_id', '0'),  # TODO: remove 'owner' in future versions
        'session_id': kwargs.get('session_id', '0'),
        'iot_box_identifier': IOT_IDENTIFIER,
        'device_identifier': device_identifier,
        'time': time.time(),
    }

    _logger.info("Received message of type %s", message_type)

    match message_type:
        case 'iot_action':
            if device_identifier not in main.iot_devices:
                # Notify the controller that the device is not connected
                _logger.warning("No IoT device with identifier '%s' found", device_identifier)
                return {**base_response, 'status': 'disconnected'}
            start_operation_time = time.perf_counter()
            _logger.info("device '%s' action started", device_identifier)
            res = main.iot_devices[device_identifier].action(kwargs)
            _logger.info("device '%s' action finished - %.*f", device_identifier, 3, time.perf_counter() - start_operation_time)
            return {**base_response, **res}
        case 'server_clear':
            helpers.disconnect_from_server()
            if server_logger:
                server_logger.close()
        case 'server_update':
            system.update_conf({
                'remote_server': kwargs['server_url']
            })
            helpers.get_odoo_server_url.cache_clear()
        case 'restart_odoo':
            helpers.odoo_restart(2)
            return {
                **base_response,
                'status': 'success',
            }
        case 'remote_debug':
            if IS_WINDOWS:
                return {}
            if not kwargs.get("status"):
                system.toggle_remote_connection(kwargs.get("token", ""))
                time.sleep(1)
            return {
                **base_response,
                'device_identifier': None,
                'status': 'success',
                'result': {'enabled': system.is_ngrok_enabled()}
            }
        case "test_protocol":
            return {
                **base_response,
                'status': 'success',
            }
        case "test_connection":
            return {
                **base_response,
                'status': 'success',
                'result': {
                    'lan_quality': helpers.check_network(),
                    'wan_quality': helpers.check_network("www.odoo.com"),
                }
            }
        case _:
            pass
    return {}
