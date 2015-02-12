# -*- coding: utf-8 -*-
import commands
import logging
import simplejson
import os
import os.path
import io
import base64
import openerp
import time
import random
import math
import md5
import openerp.addons.hw_proxy.controllers.main as hw_proxy
import pickle
import re
import subprocess
import traceback

try: 
    from .. escpos import *
    from .. escpos.exceptions import *
    from .. escpos.printer import Usb
except ImportError:
    escpos = printer = None

from threading import Thread, Lock
from Queue import Queue, Empty

try:
    import usb.core
except ImportError:
    usb = None

from PIL import Image

from openerp import http
from openerp.http import request
from openerp.tools.translate import _

_logger = logging.getLogger(__name__)


class EscposDriver(Thread):
    def __init__(self):
        Thread.__init__(self)
        self.queue = Queue()
        self.lock  = Lock()
        self.status = {'status':'connecting', 'messages':[]}

    def supported_devices(self):
        if not os.path.isfile('escpos_devices.pickle'):
            return supported_devices.device_list
        else:
            try:
                f = open('escpos_devices.pickle','r')
                return pickle.load(f)
                f.close()
            except Exception as e:
                self.set_status('error',str(e))
                return supported_devices.device_list

    def add_supported_device(self,device_string):
        r = re.compile('[0-9A-Fa-f]{4}:[0-9A-Fa-f]{4}');
        match = r.search(device_string)
        if match:
            match = match.group().split(':')
            vendor = int(match[0],16)
            product = int(match[1],16)
            name = device_string.split('ID')
            if len(name) >= 2:
                name = name[1]
            else:
                name = name[0]
            _logger.info('ESC/POS: adding support for device: '+match[0]+':'+match[1]+' '+name)
            
            device_list = supported_devices.device_list[:]
            if os.path.isfile('escpos_devices.pickle'):
                try:
                    f = open('escpos_devices.pickle','r')
                    device_list = pickle.load(f)
                    f.close()
                except Exception as e:
                    self.set_status('error',str(e))
            device_list.append({
                'vendor': vendor,
                'product': product,
                'name': name,
            })

            try:
                f = open('escpos_devices.pickle','w+')
                f.seek(0)
                pickle.dump(device_list,f)
                f.close()
            except Exception as e:
                self.set_status('error',str(e))

    def connected_usb_devices(self):
        connected = []
        
        for device in self.supported_devices():
            if usb.core.find(idVendor=device['vendor'], idProduct=device['product']) != None:
                connected.append(device)
        return connected

    def lockedstart(self):
        with self.lock:
            if not self.isAlive():
                self.daemon = True
                self.start()
    
    def get_escpos_printer(self):
  
        printers = self.connected_usb_devices()
        if len(printers) > 0:
            self.set_status('connected','Connected to '+printers[0]['name'])
            return Usb(printers[0]['vendor'], printers[0]['product'])
        else:
            self.set_status('disconnected','Printer Not Found')
            return None

    def get_status(self):
        self.push_task('status')
        return self.status

    def open_cashbox(self,printer):
        printer.cashdraw(2)
        printer.cashdraw(5)

    def set_status(self, status, message = None):
        _logger.info(status+' : '+ (message or 'no message'))
        if status == self.status['status']:
            if message != None and (len(self.status['messages']) == 0 or message != self.status['messages'][-1]):
                self.status['messages'].append(message)
        else:
            self.status['status'] = status
            if message:
                self.status['messages'] = [message]
            else:
                self.status['messages'] = []

        if status == 'error' and message:
            _logger.error('ESC/POS Error: '+message)
        elif status == 'disconnected' and message:
            _logger.warning('ESC/POS Device Disconnected: '+message)

    def run(self):

        if not escpos:
            _logger.error('ESC/POS cannot initialize, please verify system dependencies.')
            return
        while True:
            try:
                error = True
                timestamp, task, data = self.queue.get(True)

                printer = self.get_escpos_printer()

                if printer == None:
                    if task != 'status':
                        self.queue.put((timestamp,task,data))
                    error = False
                    time.sleep(5)
                    continue
                elif task == 'receipt': 
                    if timestamp >= time.time() - 1 * 60 * 60:
                        self.print_receipt_body(printer,data)
                        printer.cut()
                elif task == 'xml_receipt':
                    if timestamp >= time.time() - 1 * 60 * 60:
                        printer.receipt(data)
                elif task == 'cashbox':
                    if timestamp >= time.time() - 12:
                        self.open_cashbox(printer)
                elif task == 'printstatus':
                    self.print_status(printer)
                elif task == 'status':
                    pass
                error = False

            except NoDeviceError as e:
                print "No device found %s" %str(e)
            except HandleDeviceError as e:
                print "Impossible to handle the device due to previous error %s" % str(e)
            except TicketNotPrinted as e:
                print "The ticket does not seems to have been fully printed %s" % str(e)
            except NoStatusError as e:
                print "Impossible to get the status of the printer %s" % str(e)
            except Exception as e:
                self.set_status('error', str(e))
                errmsg = str(e) + '\n' + '-'*60+'\n' + traceback.format_exc() + '-'*60 + '\n'
                _logger.error(errmsg);
            finally:
                if error: 
                    self.queue.put((timestamp, task, data))
                if printer:
                    printer.close()

    def push_task(self,task, data = None):
        self.lockedstart()
        self.queue.put((time.time(),task,data))

    def print_status(self,eprint):
        localips = ['0.0.0.0','127.0.0.1','127.0.1.1']
        ips =  [ c.split(':')[1].split(' ')[0] for c in commands.getoutput("/sbin/ifconfig").split('\n') if 'inet addr' in c ]
        ips =  [ ip for ip in ips if ip not in localips ] 
        eprint.text('\n\n')
        eprint.set(align='center',type='b',height=2,width=2)
        eprint.text('PosBox Status\n')
        eprint.text('\n')
        eprint.set(align='center')

        if len(ips) == 0:
            eprint.text('ERROR: Could not connect to LAN\n\nPlease check that the PosBox is correc-\ntly connected with a network cable,\n that the LAN is setup with DHCP, and\nthat network addresses are available')
        elif len(ips) == 1:
            eprint.text('IP Address:\n'+ips[0]+'\n')
        else:
            eprint.text('IP Addresses:\n')
            for ip in ips:
                eprint.text(ip+'\n')

        if len(ips) >= 1:
            eprint.text('\nHomepage:\nhttp://'+ips[0]+':8069\n')

        eprint.text('\n\n')
        eprint.cut()

    def print_receipt_body(self,eprint,receipt):

        def check(string):
            return string != True and bool(string) and string.strip()
        
        def price(amount):
            return ("{0:."+str(receipt['precision']['price'])+"f}").format(amount)
        
        def money(amount):
            return ("{0:."+str(receipt['precision']['money'])+"f}").format(amount)

        def quantity(amount):
            if math.floor(amount) != amount:
                return ("{0:."+str(receipt['precision']['quantity'])+"f}").format(amount)
            else:
                return str(amount)

        def printline(left, right='', width=40, ratio=0.5, indent=0):
            lwidth = int(width * ratio) 
            rwidth = width - lwidth 
            lwidth = lwidth - indent
            
            left = left[:lwidth]
            if len(left) != lwidth:
                left = left + ' ' * (lwidth - len(left))

            right = right[-rwidth:]
            if len(right) != rwidth:
                right = ' ' * (rwidth - len(right)) + right

            return ' ' * indent + left + right + '\n'
        
        def print_taxes():
            taxes = receipt['tax_details']
            for tax in taxes:
                eprint.text(printline(tax['tax']['name'],price(tax['amount']), width=40,ratio=0.6))

        # Receipt Header
        if receipt['company']['logo']:
            eprint.set(align='center')
            eprint.print_base64_image(receipt['company']['logo'])
            eprint.text('\n')
        else:
            eprint.set(align='center',type='b',height=2,width=2)
            eprint.text(receipt['company']['name'] + '\n')

        eprint.set(align='center',type='b')
        if check(receipt['company']['contact_address']):
            eprint.text(receipt['company']['contact_address'] + '\n')
        if check(receipt['company']['phone']):
            eprint.text('Tel:' + receipt['company']['phone'] + '\n')
        if check(receipt['company']['vat']):
            eprint.text('VAT:' + receipt['company']['vat'] + '\n')
        if check(receipt['company']['email']):
            eprint.text(receipt['company']['email'] + '\n')
        if check(receipt['company']['website']):
            eprint.text(receipt['company']['website'] + '\n')
        if check(receipt['header']):
            eprint.text(receipt['header']+'\n')
        if check(receipt['cashier']):
            eprint.text('-'*32+'\n')
            eprint.text('Served by '+receipt['cashier']+'\n')

        # Orderlines
        eprint.text('\n\n')
        eprint.set(align='center')
        for line in receipt['orderlines']:
            pricestr = price(line['price_display'])
            if line['discount'] == 0 and line['unit_name'] == 'Unit(s)' and line['quantity'] == 1:
                eprint.text(printline(line['product_name'],pricestr,ratio=0.6))
            else:
                eprint.text(printline(line['product_name'],ratio=0.6))
                if line['discount'] != 0:
                    eprint.text(printline('Discount: '+str(line['discount'])+'%', ratio=0.6, indent=2))
                if line['unit_name'] == 'Unit(s)':
                    eprint.text( printline( quantity(line['quantity']) + ' x ' + price(line['price']), pricestr, ratio=0.6, indent=2))
                else:
                    eprint.text( printline( quantity(line['quantity']) + line['unit_name'] + ' x ' + price(line['price']), pricestr, ratio=0.6, indent=2))

        # Subtotal if the taxes are not included
        taxincluded = True
        if money(receipt['subtotal']) != money(receipt['total_with_tax']):
            eprint.text(printline('','-------'));
            eprint.text(printline(_('Subtotal'),money(receipt['subtotal']),width=40, ratio=0.6))
            print_taxes()
            #eprint.text(printline(_('Taxes'),money(receipt['total_tax']),width=40, ratio=0.6))
            taxincluded = False


        # Total
        eprint.text(printline('','-------'));
        eprint.set(align='center',height=2)
        eprint.text(printline(_('         TOTAL'),money(receipt['total_with_tax']),width=40, ratio=0.6))
        eprint.text('\n\n');
        
        # Paymentlines
        eprint.set(align='center')
        for line in receipt['paymentlines']:
            eprint.text(printline(line['journal'], money(line['amount']), ratio=0.6))

        eprint.text('\n');
        eprint.set(align='center',height=2)
        eprint.text(printline(_('        CHANGE'),money(receipt['change']),width=40, ratio=0.6))
        eprint.set(align='center')
        eprint.text('\n');

        # Extra Payment info
        if receipt['total_discount'] != 0:
            eprint.text(printline(_('Discounts'),money(receipt['total_discount']),width=40, ratio=0.6))
        if taxincluded:
            print_taxes()
            #eprint.text(printline(_('Taxes'),money(receipt['total_tax']),width=40, ratio=0.6))

        # Footer
        if check(receipt['footer']):
            eprint.text('\n'+receipt['footer']+'\n\n')
        eprint.text(receipt['name']+'\n')
        eprint.text(      str(receipt['date']['date']).zfill(2)
                    +'/'+ str(receipt['date']['month']+1).zfill(2)
                    +'/'+ str(receipt['date']['year']).zfill(4)
                    +' '+ str(receipt['date']['hour']).zfill(2)
                    +':'+ str(receipt['date']['minute']).zfill(2) )


driver = EscposDriver()

driver.push_task('printstatus')

hw_proxy.drivers['escpos'] = driver

class EscposProxy(hw_proxy.Proxy):
    
    @http.route('/hw_proxy/open_cashbox', type='json', auth='none', cors='*')
    def open_cashbox(self):
        _logger.info('ESC/POS: OPEN CASHBOX') 
        driver.push_task('cashbox')
        
    @http.route('/hw_proxy/print_receipt', type='json', auth='none', cors='*')
    def print_receipt(self, receipt):
        _logger.info('ESC/POS: PRINT RECEIPT') 
        driver.push_task('receipt',receipt)

    @http.route('/hw_proxy/print_xml_receipt', type='json', auth='none', cors='*')
    def print_xml_receipt(self, receipt):
        _logger.info('ESC/POS: PRINT XML RECEIPT') 
        driver.push_task('xml_receipt',receipt)

    @http.route('/hw_proxy/escpos/add_supported_device', type='http', auth='none', cors='*')
    def add_supported_device(self, device_string):
        _logger.info('ESC/POS: ADDED NEW DEVICE:'+device_string) 
        driver.add_supported_device(device_string)
        return "The device:\n"+device_string+"\n has been added to the list of supported devices.<br/><a href='/hw_proxy/status'>Ok</a>"

    @http.route('/hw_proxy/escpos/reset_supported_devices', type='http', auth='none', cors='*')
    def reset_supported_devices(self):
        try:
            os.remove('escpos_devices.pickle')
        except Exception as e:
            pass
        return 'The list of supported devices has been reset to factory defaults.<br/><a href="/hw_proxy/status">Ok</a>'

    
