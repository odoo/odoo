import json
import logging
import pprint
import requests
import time
import urllib.parse
import websocket

from threading import Thread

from odoo.addons.hw_drivers import main
from odoo.addons.hw_drivers.tools import helpers
from odoo.addons.hw_drivers.server_logger import close_server_log_sender_handler

_logger = logging.getLogger(__name__)
websocket.enableTrace(True, level=logging.getLevelName(_logger.getEffectiveLevel()))


@helpers.require_db
def send_to_controller(device_type, params, server_url=None):
    """Confirm the operation's completion by sending a response back to the Odoo server

    :param device_type: the type of device that the operation was performed on
    :param params: the parameters to send back to the server
    :param server_url: URL of the Odoo server (provided by decorator).
    """
    routes = {
        "printer": "/iot/printer/status",
    }
    params['iot_mac'] = helpers.get_mac_address()
    server_url += routes[device_type]
    try:
        response = requests.post(server_url, json={'params': params}, timeout=5)
        response.raise_for_status()
    except requests.exceptions.RequestException:
        _logger.exception('Could not reach confirmation status URL: %s', server_url)


def on_message(ws, messages):
    """
        Synchronously handle messages received by the websocket.
    """
    messages = json.loads(messages)
    _logger.debug("websocket received a message: %s", pprint.pformat(messages))
    iot_mac = helpers.get_mac_address()
    for message in messages:
        message_type = message['message']['type']
        payload = message['message']['payload']
        if message_type == 'iot_action':
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
        elif message_type == 'server_clear':
            if iot_mac in payload['iotIdentifiers']:
                helpers.disconnect_from_server()
                close_server_log_sender_handler()
        elif message_type != 'print_confirmation':  # intended to be ignored
            _logger.warning("message type not supported: %s", message_type)


def on_error(ws, error):
    _logger.error("websocket received an error: %s", error)


def on_close(ws, close_status_code, close_msg):
    _logger.debug("websocket closed with status: %s", close_status_code)


@helpers.require_db
class WebsocketClient(Thread):
    channel = ""

    def on_open(self, ws):
        """
            When the client is setup, this function send a message to subscribe to the iot websocket channel
        """
        ws.send(
            json.dumps({'event_name': 'subscribe', 'data': {'channels': [self.channel], 'last': 0, 'mac_address': helpers.get_mac_address()}})
        )

    def __init__(self, channel, server_url=None):
        """This class will not be instantiated if no db is connected.

        :param str channel: the channel to subscribe to
        :param str server_url: URL of the Odoo server (provided by decorator).
        """
        self.channel = channel
        url_parsed = urllib.parse.urlsplit(server_url)
        scheme = url_parsed.scheme.replace("http", "ws", 1)
        self.url = urllib.parse.urlunsplit((scheme, url_parsed.netloc, 'websocket', '', ''))
        super().__init__()

    def run(self):
        self.ws = websocket.WebSocketApp(self.url,
            header={"User-Agent": "OdooIoTBox/1.0"},
            on_open=self.on_open, on_message=on_message,
            on_error=on_error, on_close=on_close)

        # The IoT synchronised servers can stop in 2 ways that we need to handle:
        #  A. Gracefully:
        #   In this case a disconnection signal is sent to the IoT-box
        #   The websocket is properly closed, but it needs to be established a new connection when
        #   the server will be back.
        #
        # B. Forced/killed:
        #   In this case there is no disconnection signal received
        #
        #   This will also happen with the graceful quit as `reconnect` will trigger if the server
        #   is offline while attempting the new connection
        while True:
            try:
                run_res = self.ws.run_forever(reconnect=10)
                _logger.debug("websocket run_forever return with %s", run_res)
            except Exception:
                _logger.exception("An unexpected exception happened when running the websocket")
            _logger.debug('websocket will try to restart in 10 seconds')
            time.sleep(10)
