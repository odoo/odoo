import concurrent.futures
import itertools
import json
import logging
import pprint
import threading
import time
import urllib.parse
import urllib3
import websocket

from threading import Thread

from odoo.addons.hw_drivers import main
from odoo.addons.hw_drivers.tools import helpers
from odoo.tools.misc import dumpstacks

_logger = logging.getLogger(__name__)
websocket.enableTrace(True, level=logging.getLevelName(_logger.getEffectiveLevel()))


WS_REQUEST_POOL = concurrent.futures.ThreadPoolExecutor(30)  # max number of threads

WS_REQUEST_TIME_TIMEOUT = 5 * 60  # seconds
WS_REQUEST_COUNTER = itertools.count()
"""
unique incrementing identifier each time a new websocket message is received
"""


def _check_ws_request_pool():
    """Check if the request pool is not stuck with timeout-ing requests.
    We can't kill a thread, so if it is stuck we will log the thread stack trace
    every WS_REQUEST_TIME_TIMEOUT seconds.

    We use a concurrent.futures.ThreadPoolExecutor to handle the websocket messages.
    Scenario example:
     When a ws request R1 is received, it will create a thread T1 in the pool to handle the request
     When a second ws request is received R2:
      if R1 finished, T1 is "free" so it will be reused
      if R1 is still running, T1 will be busy so a second thread T2 will be created to handle R2
     ...
     until the maximum number of threads is reached (see `ThreadPoolExecutor._max_workers`).
     In this case they will wait until a thread is free.
    """
    while True:
        time.sleep(WS_REQUEST_TIME_TIMEOUT)

        timeouting_threads_ident = []
        for ws_thread in WS_REQUEST_POOL._threads:
            try:
                ws_thread_start_time = ws_thread.perf_t0
                ws_thread_ws_request = ws_thread.url
            except AttributeError:
                # thread values was not assigned yet
                continue
            if ws_thread_start_time is None:
                # thread in the thread pool that is currently not doing any ws operation
                # but still alive and waiting for a new ws request to handle
                continue
            time_elapsed = time.time() - ws_thread_start_time
            if time_elapsed > WS_REQUEST_TIME_TIMEOUT:
                timeouting_threads_ident.append(ws_thread.ident)
            else:
                _logger.debug("Websocket thread %s handling %s is busy since %.2f sec",
                              ws_thread, ws_thread_ws_request, time_elapsed)

        if timeouting_threads_ident:
            _logger.error("Websocket thread request pool is stuck with timeouting threads (%d/%d)",
                          len(timeouting_threads_ident), WS_REQUEST_POOL._max_workers)
            dumpstacks(thread_idents=timeouting_threads_ident, log_level=logging.ERROR)


threading.Thread(name='ws request pool checker', target=_check_ws_request_pool, daemon=True).start()


def send_to_controller(print_id, device_identifier):
    """
    Send back to odoo's server the completion of the operation
    """
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
                    'iot_mac': helpers.get_mac_address(),
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
        When a message is received by the websocket, this function is triggered
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
        The message is loaded and if its type is 'print', it is sent to the printer
    """
    current_thread = threading.current_thread()
    try:
        current_thread.perf_t0 = time.time()  # same value as the one odoo uses for perf logging
        current_thread.url = f"websocket request #{ws_request_id}"
        current_thread.query_time = 0

        messages = json.loads(ws_messages)
        _logger.debug("ws#%d: websocket thread %s:\n%s", ws_request_id, current_thread, pprint.pformat(messages))
        for document in messages:
            if (document['message']['type'] in ['print', 'iot_action']):
                payload = document['message']['payload']
                iot_mac = helpers.get_mac_address()
                intended_iot_macs = payload['iotDevice']['iotIdentifiers']
                if iot_mac in intended_iot_macs:
                    for device in payload['iotDevice']['identifiers']:
                        iot_device_identifier = device['identifier']
                        if iot_device_identifier in main.iot_devices:
                            _logger.debug("ws#%d: starting operation on device '%s'", ws_request_id, iot_device_identifier)
                            main.iot_devices[device["identifier"]]._action_default(payload)
                            _logger.info("ws#%d: operation finished on device '%s'", ws_request_id, iot_device_identifier)
                            send_to_controller(payload['print_id'], iot_device_identifier)
                else:
                    # Might be totally intended as all IoT will receive the message as they listen to the same channel
                    # but might be useful for troubleshooting purposes
                    _logger.debug("ws#%d: operation ignored as the IoT mac %s is not in the intended one: %s", ws_request_id, iot_mac, intended_iot_macs)
        _logger.debug("ws#%d: websocket finished", ws_request_id)
    finally:
        # let know the pool checker that the thread is free
        current_thread.perf_t0 = None
        current_thread.url = None


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
