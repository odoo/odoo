import json
import logging
import pprint
import requests
import time
import urllib.parse
import websocket

from threading import Thread

from odoo.addons.iot_drivers.tools import communication, helpers, system
from odoo.addons.iot_drivers.tools.system import IOT_IDENTIFIER
from odoo.addons.iot_drivers.webrtc_client import webrtc_client

_logger = logging.getLogger(__name__)
websocket.enableTrace(True, level=logging.getLevelName(_logger.getEffectiveLevel()))


@helpers.require_db
def send_to_controller(params, method="send_websocket", server_url=None):
    """Confirm the operation's completion by sending a response back to the Odoo server

    :param params: the parameters to send back to the server
    :param method: method to call on the IoT box controller
    :param server_url: URL of the Odoo server (provided by decorator).
    """
    request_path = f"{server_url}/iot/box/{method}"
    try:
        response = requests.post(request_path, json={'params': params}, timeout=5)
        response.raise_for_status()
    except requests.exceptions.RequestException:
        _logger.exception('Could not reach database URL: %s', request_path)


def on_error(ws, error):
    _logger.error("websocket received an error: %s", error)


@helpers.require_db
class WebsocketClient(Thread):
    def on_open(self, ws):
        """
            When the client is setup, this function send a message to subscribe
        """
        ws.send(json.dumps({
            'event_name': 'subscribe',
            'data': {
                'channels': [],
                'last': self.last_message_id,
                'iot_token': helpers.get_token(),
            }
        }))

    def on_message(self, ws, messages):
        """Synchronously handle messages received by the websocket."""
        for message in json.loads(messages):
            _logger.debug("websocket received a message: %s", pprint.pformat(message))
            self.last_message_id = message["id"]
            payload = message['message']['payload']
            message_type = message['message']['type']

            if payload.get('iot_identifier') != IOT_IDENTIFIER:
                continue

            if message_type == 'webrtc_offer':
                answer = webrtc_client.offer(payload['offer'])
                send_to_controller({
                    'iot_box_identifier': IOT_IDENTIFIER,
                    'answer': answer,
                }, method="webrtc_answer")
            else:
                result = communication.handle_message(message_type, **payload)
                if result:
                    send_to_controller(result)

    def on_close(self, ws, close_status_code, close_msg):
        _logger.debug("websocket closed with status: %s", close_status_code)

    def __init__(self, server_url=None):
        """This class will not be instantiated if no db is connected.

        :param str server_url: URL of the Odoo server (provided by decorator).
        """
        self.server_url = server_url
        url_parsed = urllib.parse.urlsplit(server_url)
        scheme = url_parsed.scheme.replace("http", "ws", 1)
        self.websocket_url = urllib.parse.urlunsplit((scheme, url_parsed.netloc, 'websocket', '', ''))
        self.db_name = system.get_conf('db_name') or ''
        self.session_id = ''
        self.last_message_id = 0
        super().__init__()

    def run(self):
        if self.db_name:
            session_response = requests.get(
                self.server_url + "/web/login?db=" + self.db_name,
                allow_redirects=False,
                timeout=10,
            )
            if session_response.status_code in [200, 302]:
                self.session_id = session_response.cookies['session_id']
            else:
                _logger.error("Failed to get session ID, status %s", session_response.status_code)

        self.ws = websocket.WebSocketApp(self.websocket_url,
            header={"User-Agent": "OdooIoTBox/1.0", "Cookie": f"session_id={self.session_id}"},
            on_open=self.on_open, on_message=self.on_message,
            on_error=on_error, on_close=self.on_close)

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
