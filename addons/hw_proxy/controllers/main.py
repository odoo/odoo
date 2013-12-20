# -*- coding: utf-8 -*-
import logging
import simplejson
import os
import openerp
import time
import random
import subprocess
import usb.core
import escpos 
import escpos.printer

from openerp import http
from openerp.http import request
from openerp.addons.web.controllers.main import manifest_list, module_boot, html_template

_logger = logging.getLogger(__name__)

class Proxy(http.Controller):
    def __init__(self):
        self.scale = 'closed'
        self.scale_weight = 0.0
        pass

    def connected_usb_devices(self,devices):
        connected = []
        for device in devices:
            if usb.core.find(idVendor=device['vendor'], idProduct=device['product']) != None:
                connected.append(device)
        return connected

    @http.route('/hw_proxy/test_connection', type='json', auth='admin')
    def test_connection(self):
        _logger.info('Received Connection Test from the Point of Sale');

    @http.route('/hw_proxy/scan_item_success', type='json', auth='admin')
    def scan_item_success(self, ean):
        """
        A product has been scanned with success
        """
        print 'scan_item_success: ' + str(ean)

    @http.route('/hw_proxy/scan_item_error_unrecognized', type='json', auth='admin')
    def scan_item_error_unrecognized(self, ean):
        """
        A product has been scanned without success
        """
        print 'scan_item_error_unrecognized: ' + str(ean)

    @http.route('/hw_proxy/help_needed', type='json', auth='admin')
    def help_needed(self):
        """
        The user wants an help (ex: light is on)
        """
        print "help_needed"

    @http.route('/hw_proxy/help_canceled', type='json', auth='admin')
    def help_canceled(self):
        """
        The user stops the help request
        """
        print "help_canceled"

    @http.route('/hw_proxy/weighting_start', type='json', auth='admin')
    def weighting_start(self):
        if self.scale == 'closed':
            print "Opening (Fake) Connection to Scale..."
            self.scale = 'open'
            self.scale_weight = 0.0
            time.sleep(0.1)
            print "... Scale Open."
        else:
            print "WARNING: Scale already Connected !!!"

    @http.route('/hw_proxy/weighting_read_kg', type='json', auth='admin')
    def weighting_read_kg(self):
        if self.scale == 'open':
            print "Reading Scale..."
            time.sleep(0.025)
            self.scale_weight += 0.01
            print "... Done."
            return self.scale_weight
        else:
            print "WARNING: Reading closed scale !!!"
            return 0.0

    @http.route('/hw_proxy/weighting_end', type='json', auth='admin')
    def weighting_end(self):
        if self.scale == 'open':
            print "Closing Connection to Scale ..."
            self.scale = 'closed'
            self.scale_weight = 0.0
            time.sleep(0.1)
            print "... Scale Closed."
        else:
            print "WARNING: Scale already Closed !!!"

    @http.route('/hw_proxy/payment_request', type='json', auth='admin')
    def payment_request(self, price):
        """
        The PoS will activate the method payment 
        """
        print "payment_request: price:"+str(price)
        return 'ok'

    @http.route('/hw_proxy/payment_status', type='json', auth='admin')
    def payment_status(self):
        print "payment_status"
        return { 'status':'waiting' } 

    @http.route('/hw_proxy/payment_cancel', type='json', auth='admin')
    def payment_cancel(self):
        print "payment_cancel"

    @http.route('/hw_proxy/transaction_start', type='json', auth='admin')
    def transaction_start(self):
        print 'transaction_start'

    @http.route('/hw_proxy/transaction_end', type='json', auth='admin')
    def transaction_end(self):
        print 'transaction_end'

    @http.route('/hw_proxy/cashier_mode_activated', type='json', auth='admin')
    def cashier_mode_activated(self):
        print 'cashier_mode_activated'

    @http.route('/hw_proxy/cashier_mode_deactivated', type='json', auth='admin')
    def cashier_mode_deactivated(self):
        print 'cashier_mode_deactivated'

    @http.route('/hw_proxy/open_cashbox', type='json', auth='admin')
    def open_cashbox(self):
        print 'open_cashbox'

    @http.route('/hw_proxy/print_receipt', type='json', auth='admin')
    def print_receipt(self, receipt):
        print 'print_receipt' + str(receipt)

    @http.route('/hw_proxy/log', type='json', auth='admin')
    def log(self, arguments):
        _logger.info(' '.join(str(v) for v in arguments))

    @http.route('/hw_proxy/print_pdf_invoice', type='json', auth='admin')
    def print_pdf_invoice(self, pdfinvoice):
        print 'print_pdf_invoice' + str(pdfinvoice)


