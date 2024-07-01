import logging
import pprint
import time

from odoo.addons.hw_drivers.tools import helpers
from odoo.addons.hw_drivers import main


_logger = logging.getLogger(__name__)


def iot_device_action(message):
    payload = message['message']['payload']
    iot_mac = helpers.get_mac_address()
    if iot_mac in payload['iotDevice']['iotIdentifiers']:
        for device in payload['iotDevice']['identifiers']:
            device_identifier = device['identifier']
            if device_identifier in main.iot_devices:
                start_operation_time = time.perf_counter()
                _logger.debug("device '%s' action started with: %s", device_identifier, pprint.pformat(payload))
                main.iot_devices[device_identifier].action(payload)
                _logger.info("device '%s' action finished - %.*f", device_identifier, 3, time.perf_counter() - start_operation_time)
    else:
        # likely intended as IoT share the same channel
        _logger.debug("message ignored due to different iot mac: %s", iot_mac)


def iot_box_action(message):
    payload = message['message']['payload']
    iot_mac = helpers.get_mac_address()
    if iot_mac in payload['iotIdentifiers'] and payload['action'] in ['reboot_box', 'restart_odoo']:
        _logger.debug("IoT box action '%s' started", payload['action'])
        helpers.restart_odoo_or_reboot(payload['action'])


def print_confirmation(message):
    _logger.debug("Print confirmation received: %s", message)


websocket_handlers = {
    "iot_device_action": iot_device_action,
    "iot_box_action": iot_box_action,
    "print_confirmation": print_confirmation
}
