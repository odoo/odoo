# -*- coding: utf-8 -*-
import logging
import simplejson
import os
import io
import base64
import openerp
import time
import random
import math
import openerp.addons.hw_proxy.controllers.main as hw_proxy
import subprocess
import usb.core
from openerp.tools.translate import _
from .. import escpos
from ..escpos import printer
from PIL import Image

from openerp import http
from openerp.http import request
from openerp.addons.web.controllers.main import manifest_list, module_boot, html_template

_logger = logging.getLogger(__name__)

class EscposDriver(hw_proxy.Proxy):
    
    supported_printers = [
        { 'vendor' : 0x04b8, 'product' : 0x0e03, 'name' : 'Epson TM-T20' }
    ]

    def connected_usb_devices(self,devices):
        connected = []
        for device in devices:
            if usb.core.find(idVendor=device['vendor'], idProduct=device['product']) != None:
                connected.append(device)
        return connected
    
    def get_escpos_printer(self):
        printers = self.connected_usb_devices(self.supported_printers)
        if len(printers) > 0:
            return escpos.printer.Usb(printers[0]['vendor'], printers[0]['product'])
        else:
            return None
    
    @http.route('/hw_proxy/open_cashbox', type='json', auth='admin')
    def open_cashbox(self):
        print 'ESC/POS: OPEN CASHBOX'
        eprint = self.get_escpos_printer()
        if eprint != None:
            eprint.cashdraw(2)
            eprint.cashdraw(5)
        
    @http.route('/hw_proxy/print_receipt', type='json', auth='admin')
    def print_receipt(self, receipt):
        print 'ESC/POS: PRINT RECEIPT'
        eprint = self.get_escpos_printer()
        if eprint != None:
            self.print_receipt_body(eprint,receipt)
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

        logo = None

        if receipt['company']['logo']:
            img = receipt['company']['logo']
            img = img[img.find(',')+1:]
            f = io.BytesIO('img')
            f.write(base64.decodestring(img))
            f.seek(0)
            logo_rgba = Image.open(f)
            logo = Image.new('RGB', logo_rgba.size, (255,255,255))
            logo.paste(logo_rgba, mask=logo_rgba.split()[3]) 
            width = 300
            wfac  = width/float(logo_rgba.size[0])
            height = int(logo_rgba.size[1]*wfac)
            logo   = logo.resize((width,height), Image.ANTIALIAS)

        # Receipt Header
        if logo:
            eprint._convert_image(logo)
            eprint.text('\n')
        else:
            eprint.set(align='center',type='b',height=2,width=2)
            eprint.text(receipt['company']['name'] + '\n')

        eprint.set(align='center',type='b')
        if check(receipt['shop']['name']):
            eprint.text(receipt['shop']['name'] + '\n')
        if check(receipt['company']['contact_address']):
            eprint.text(receipt['company']['contact address'] + '\n')
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
        
