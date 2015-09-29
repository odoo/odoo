# -*- coding: utf-8 -*-
import logging
import commands
import json
import os
import os.path
import openerp
import time
import random
import subprocess
import json
import werkzeug
import werkzeug.wrappers
_logger = logging.getLogger(__name__)


from openerp import http
from openerp.http import request

# Those are the builtin raspberry pi USB modules, they should
# not appear in the list of connected devices.
BANNED_DEVICES = set([
	"0424:9514",	# Standard Microsystem Corp. Builtin Ethernet module
	"1d6b:0002",	# Linux Foundation 2.0 root hub
	"0424:ec00",	# Standard Microsystem Corp. Other Builtin Ethernet module
])


# drivers modules must add to drivers an object with a get_status() method 
# so that 'status' can return the status of all active drivers
drivers = {}

class Proxy(http.Controller):

    def get_status(self):
        statuses = {}
        for driver in drivers:
            statuses[driver] = drivers[driver].get_status()
        return statuses

    @http.route('/hw_proxy/hello', type='http', auth='none', cors='*')
    def hello(self):
        return "ping"

    @http.route('/hw_proxy/handshake', type='json', auth='none', cors='*')
    def handshake(self):
        return True

    @http.route('/hw_proxy/status', type='http', auth='none', cors='*')
    def status_http(self):
        resp = """
<!DOCTYPE HTML>
<html>
    <head>
        <title>Odoo's PosBox</title>
        <style>
        body {
            width: 480px;
            margin: 60px auto;
            font-family: sans-serif;
            text-align: justify;
            color: #6B6B6B;
        }
        .device {
            border-bottom: solid 1px rgb(216,216,216);
            padding: 9px;
        }
        .device:nth-child(2n) {
            background:rgb(240,240,240);
        }
        </style>
    </head>
    <body>
        <h1>Hardware Status</h1>
        <p>The list of enabled drivers and their status</p>
"""
        statuses = self.get_status()
        for driver in statuses:

            status = statuses[driver]

            if status['status'] == 'connecting':
                color = 'black'
            elif status['status'] == 'connected':
                color = 'green'
            else:
                color = 'red'

            resp += "<h3 style='color:"+color+";'>"+driver+' : '+status['status']+"</h3>\n"
            resp += "<ul>\n"
            for msg in status['messages']:
                resp += '<li>'+msg+'</li>\n'
            resp += "</ul>\n"
        resp += """
            <h2>Connected Devices</h2>
            <p>The list of connected USB devices as seen by the posbox</p>
        """
        devices = commands.getoutput("lsusb").split('\n')
        count   = 0
        resp += "<div class='devices'>\n"
        for device in devices:
            device_name = device[device.find('ID')+2:]
            device_id   = device_name.split()[0]
            if not (device_id in BANNED_DEVICES):
            	resp+= "<div class='device' data-device='"+device+"'>"+device_name+"</div>\n"
                count += 1
        
        if count == 0:
            resp += "<div class='device'>No USB Device Found</div>"

        resp += "</div>\n</body>\n</html>\n\n"

        return request.make_response(resp,{
            'Cache-Control': 'no-cache', 
            'Content-Type': 'text/html; charset=utf-8',
            'Access-Control-Allow-Origin':  '*',
            'Access-Control-Allow-Methods': 'GET',
            })

    @http.route('/hw_proxy/status_json', type='json', auth='none', cors='*')
    def status_json(self):
        return self.get_status()

    @http.route('/hw_proxy/scan_item_success', type='json', auth='none', cors='*')
    def scan_item_success(self, ean):
        """
        A product has been scanned with success
        """
        print 'scan_item_success: ' + str(ean)

    @http.route('/hw_proxy/scan_item_error_unrecognized', type='json', auth='none', cors='*')
    def scan_item_error_unrecognized(self, ean):
        """
        A product has been scanned without success
        """
        print 'scan_item_error_unrecognized: ' + str(ean)

    @http.route('/hw_proxy/help_needed', type='json', auth='none', cors='*')
    def help_needed(self):
        """
        The user wants an help (ex: light is on)
        """
        print "help_needed"

    @http.route('/hw_proxy/help_canceled', type='json', auth='none', cors='*')
    def help_canceled(self):
        """
        The user stops the help request
        """
        print "help_canceled"

    @http.route('/hw_proxy/payment_request', type='json', auth='none', cors='*')
    def payment_request(self, price):
        """
        The PoS will activate the method payment 
        """
        print "payment_request: price:"+str(price)
        return 'ok'

    @http.route('/hw_proxy/payment_status', type='json', auth='none', cors='*')
    def payment_status(self):
        print "payment_status"
        return { 'status':'waiting' } 

    @http.route('/hw_proxy/payment_cancel', type='json', auth='none', cors='*')
    def payment_cancel(self):
        print "payment_cancel"

    @http.route('/hw_proxy/transaction_start', type='json', auth='none', cors='*')
    def transaction_start(self):
        print 'transaction_start'

    @http.route('/hw_proxy/transaction_end', type='json', auth='none', cors='*')
    def transaction_end(self):
        print 'transaction_end'

    @http.route('/hw_proxy/cashier_mode_activated', type='json', auth='none', cors='*')
    def cashier_mode_activated(self):
        print 'cashier_mode_activated'

    @http.route('/hw_proxy/cashier_mode_deactivated', type='json', auth='none', cors='*')
    def cashier_mode_deactivated(self):
        print 'cashier_mode_deactivated'

    @http.route('/hw_proxy/open_cashbox', type='json', auth='none', cors='*')
    def open_cashbox(self):
        print 'open_cashbox'

    @http.route('/hw_proxy/print_receipt', type='json', auth='none', cors='*')
    def print_receipt(self, receipt):
        print 'print_receipt' + str(receipt)

    @http.route('/hw_proxy/is_scanner_connected', type='json', auth='none', cors='*')
    def is_scanner_connected(self, receipt):
        print 'is_scanner_connected?' 
        return False

    @http.route('/hw_proxy/scanner', type='json', auth='none', cors='*')
    def scanner(self, receipt):
        print 'scanner' 
        time.sleep(10)
        return ''

    @http.route('/hw_proxy/log', type='json', auth='none', cors='*')
    def log(self, arguments):
        _logger.info(' '.join(str(v) for v in arguments))

    @http.route('/hw_proxy/print_pdf_invoice', type='json', auth='none', cors='*')
    def print_pdf_invoice(self, pdfinvoice):
        print 'print_pdf_invoice' + str(pdfinvoice)
