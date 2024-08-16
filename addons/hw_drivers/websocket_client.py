import json
import logging
import pprint
import time
import urllib.parse
import urllib3
import websocket

from threading import Thread

from odoo.addons.hw_drivers import main
from odoo.addons.hw_drivers.tools import helpers

_logger = logging.getLogger(__name__)
websocket.enableTrace(True, level=logging.getLevelName(_logger.getEffectiveLevel()))

def send_to_controller(device_type, params):
    """
    Confirm the operation's completion by sending a response back to the Odoo server
    """
    routes = {
        "printer": "/iot/printer/status",
    }
    params['iot_mac'] = helpers.get_mac_address()
    server_url = helpers.get_odoo_server_url() + routes[device_type]
    try:
        urllib3.disable_warnings()
        http = urllib3.PoolManager(cert_reqs='CERT_NONE')
        http.request(
            'POST',
            server_url,
            body=json.dumps({'params': params}).encode('utf8'),
            headers={
                'Content-type': 'application/json',
                'Accept': 'text/plain',
            },
        )
    except Exception:
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
        if message_type == 'iot_action':
            payload = message['message']['payload']
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
        elif message_type != 'print_confirmation':  # intended to be ignored
            _logger.warning("message type not supported: %s", message_type)


def on_error(ws, error):
    _logger.error("websocket received an error: %s", error)


def on_close(ws, close_status_code, close_msg):
    _logger.debug("websocket closed with status: %s", close_status_code)


class WebsocketClient(Thread):
    iot_channel = ""

    def on_open(self, ws):
        """
            When the client is setup, this function send a message to subscribe to the iot websocket channel
        """
        ws.send(
            json.dumps({'event_name': 'subscribe', 'data': {'channels': [self.iot_channel], 'last': 0, 'mac_address': helpers.get_mac_address()}})
        )

    def __init__(self, url):
        url_parsed = urllib.parse.urlsplit(url)
        scheme = url_parsed.scheme.replace("http", "ws", 1)
        self.url = urllib.parse.urlunsplit((scheme, url_parsed.netloc, 'websocket', '', ''))
        Thread.__init__(self)

    def run(self):
        self.ws = websocket.WebSocketApp(self.url,
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
