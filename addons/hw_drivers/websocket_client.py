import websocket
import asyncio
import base64
import json
import logging
import urllib3

from threading import Thread
from odoo.addons.hw_drivers import main
from odoo.addons.hw_drivers.tools import helpers
import time


_logger = logging.getLogger(__name__)
connected = False

def on_message(ws, messages):
    """
        When a message is receive, this function is triggered
        The message is load and if his type is 'print', is sent to the printer
    """
    messages = json.loads(messages)
    print(messages)
    for document in messages:
        if (document['message']['type'] != 'print'):
            print("not a print")
            return
        payload = document['message']['payload']
    #Check if the print is for this box
        if (payload['iotDevice']['identifier'] not in main.iot_devices
                or payload['iotDevice']['iotIp'] != helpers.get_ip()): #doubt here
            print("Not this printer")
            return
        main.iot_devices[payload['iotDevice']['identifier']].print_raw(
            base64.b64decode(payload['document']))
        print("SENDING")   
    #Send answer via json route
        urllib3.disable_warnings()
        http = urllib3.PoolManager(cert_reqs='CERT_NONE')
        server = helpers.get_odoo_server_url() #Clean later
        try:
            http.request(
                'POST',
                server + "/iot/printer/status",
                body=json.dumps({'params': {'report_id' : payload['report_id'],}}).encode('utf8'),
                headers={
                    'Content-type': 'application/json',
                    'Accept': 'text/plain',
                },
            )
        except Exception as e:
            _logger.error('Could not reach configured server')
            _logger.error('A error encountered : %s ' % e)

        #ws.send(sendo)


def on_open(ws):
    """
        When the client is setup, this function send a message to subscribe to the 'iot_box' websocket channel
    """
    print('OPEN')
    ws.send(
        '{"event_name":"subscribe","data":{"channels":["broadcast", "iot_channel"],"last":0}}'
    )

def on_error(ws, error):
    _logger.error(error)


def on_close(ws, close_status_code, close_msg):
    print('CLOSE')
    return


class WebsocketClient(Thread):

    def __init__(self, url):
        print('init of WebsocketClient')
        self.url = url.replace("http", "ws")
        Thread.__init__(self)

    def start_client(self):
        self.ws = websocket.WebSocketApp(self.url + "/websocket",
                                         on_open=on_open,
                                         on_message=on_message,
                                         on_error=on_error,
                                         on_close=on_close)
        while 1:
            self.ws.run_forever()
            time.sleep(1)

    def run(self):
        print('run of WebsocketClient')
        self.start_client()
