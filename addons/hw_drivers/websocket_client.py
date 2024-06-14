import concurrent.futures
import itertools
import json
import logging
import pprint
import sys
import threading
import traceback
import time
import urllib.parse
import urllib3
import websocket

from threading import Thread

from odoo.addons.hw_drivers import main
from odoo.addons.hw_drivers.tools import helpers

_logger = logging.getLogger(__name__)
websocket.enableTrace(True, level=logging.getLevelName(_logger.getEffectiveLevel()))

WS_REQUEST_POOL = concurrent.futures.ThreadPoolExecutor(8)

WS_REQUEST_TIME_TIMEOUT = 5 * 60  # seconds
WS_REQUEST_COUNTER = itertools.count()
"""
unique incrementing identifier each time a new websocket message is received
"""

def _check_ws_request_pool():
    """Check if the request pool is not stuck with timeout-ing requests.
    We can't kill a thread, but if the situation is desperate we will restart the IoT.

    We use a concurrent.futures.ThreadPoolExecutor to handle the websocket messages.
    Ccenario example:
     When a ws request R1 is received, it will create a thread T1 in the pool to handle the request
     When a second ws request is received R2:
      if R1 finished, T1 is "free" so it will be reused
      if R1 is still running, T1 will be busy so a second thread T2 will be created to handle R2
     ...
     until the maximum number of threads is reached (see `ThreadPoolExecutor._max_workers`).
     In this case they will wait until a thread is free.
    """
    def thread_stack_trace(thread):
        frame = sys._current_frames().get(thread.ident, None)
        if frame:
            return ". Thread stack:\n" + ''.join(traceback.format_stack(frame))
        return ''

    while True:
        time.sleep(WS_REQUEST_TIME_TIMEOUT)
        for ws_thread in WS_REQUEST_POOL._threads:
            if not getattr(ws_thread, 'starting_time', None):
                # thread that was started by a previous ws request but currently idle
                continue
            thread_ws_request_id = getattr(ws_thread, 'ws_request_id', None)
            time_differece = time.time() - ws_thread.starting_time
            if time_differece > WS_REQUEST_TIME_TIMEOUT:
                _logger.error("Websocket thread %s handling ws request #%d is stuck (busy since %.2f sec)%s", ws_thread, thread_ws_request_id, time_differece, thread_stack_trace(ws_thread))
            else:
                _logger.debug("Websocket thread %s handling ws request #%d is busy since %.2f sec", ws_thread, thread_ws_request_id, time_differece)

threading.Thread(name='ws request pool checker', target=_check_ws_request_pool, daemon=True).start()


def send_to_controller(print_id, device_identifier):
    server = helpers.get_odoo_server_url()
    try:
        urllib3.disable_warnings()
        http = urllib3.PoolManager(cert_reqs='CERT_NONE')
        http.request(
            'POST',
            server + "/iot/printer/status",
            body=json.dumps(
                {'params': {
                    'print_id': print_id,
                    'device_identifier': device_identifier,
                    }}).encode('utf8'),
            headers={
                'Content-type': 'application/json',
                'Accept': 'text/plain',
            },
        )
    except Exception:
        _logger.exception('Could not reach configured server: %s', server)

def on_message(ws, messages):
    """
        When a message is receive by the websocket, this function is triggered
        We use threads to avoid blocking the main thread on a message with long processing, see:
        https://websocket-client.readthedocs.io/en/latest/threading.html
    """
    ws_request_id = next(WS_REQUEST_COUNTER)
    _logger.debug("websocket received new message #%d: %s", ws_request_id, messages)
    WS_REQUEST_POOL.submit(handle_ws_message, messages, ws_request_id)
    # Be very careful to NOT add sync calls like `ws_request.result()` here
    # The goal is to avoid blocking the main thread, so we can't wait for the result


def handle_ws_message(ws_messages, ws_request_id):
    """
        Handle the message received by the websocket synchronously.
        e.g:
        The message is load and if its type is 'print', is sent to the printer
    """
    current_thread = threading.current_thread()
    current_thread.starting_time = time.time()
    current_thread.ws_request_id = ws_request_id
    messages = json.loads(ws_messages)
    _logger.debug("websocket thread %s handling ws request #%d:\n%s", current_thread, ws_request_id, pprint.pformat(messages))
    for document in messages:
        if (document['message']['type'] == 'print'):
            payload = document['message']['payload']
            if helpers.get_mac_address() in payload['iotDevice']['iotIdentifiers']:
                #send box confirmation
                for device in payload['iotDevice']['identifiers']:
                    if device['identifier'] in main.iot_devices:
                        main.iot_devices[device["identifier"]]._action_default(payload)
                        send_to_controller(payload['print_id'], device['identifier'])
    _logger.debug("websocket finished handling message #%s", ws_request_id)
    # let know the pool checker that the thread is free
    current_thread.starting_time = None
    current_thread.ws_request_id = None


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
            json.dumps({'event_name': 'subscribe', 'data': {'channels': [self.iot_channel], 'last': 0}})
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
