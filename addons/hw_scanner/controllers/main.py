# -*- coding: utf-8 -*-
import logging
import os
from os import listdir
from os.path import join
import openerp
import openerp.addons.hw_proxy.controllers.main as hw_proxy
from openerp.tools.translate import _

from openerp import http
from openerp.http import request

_logger = logging.getLogger(__name__)

from evdev import InputDevice, ecodes, categorize, list_devices
from select import select

class ScannerDriver(hw_proxy.Proxy):
    def __init__(self):
        self.input_dir = '/dev/input/by-id/'
        self.keymap = {
            2: ("1","!"),
            3: ("2","@"),
            4: ("3","#"),
            5: ("4","$"),
            6: ("5","%"),
            7: ("6","^"),
            8: ("7","&"),
            9: ("8","*"),
            10:("9","("), 
            11:("0",")"), 
            12:("-","_"), 
            13:("=","+"), 
            # 14 BACKSPACE
            # 15 TAB 
            16:("q","Q"), 
            17:("w","W"),
            18:("e","E"),
            19:("r","R"),
            20:("t","T"),
            21:("y","Y"),
            22:("u","U"),
            23:("i","I"),
            24:("o","O"),
            25:("p","P"),
            26:("[","{"),
            27:("]","}"),
            # 28 ENTER
            # 29 LEFT_CTRL
            30:("a","A"),
            31:("s","S"),
            32:("d","D"),
            33:("f","F"),
            34:("g","G"),
            35:("h","H"),
            36:("j","J"),
            37:("k","K"),
            38:("l","L"),
            39:(";",":"),
            40:("'","\""),
            41:("`","~"),
            # 42 LEFT SHIFT
            43:("\\","|"),
            44:("z","Z"),
            45:("x","X"),
            46:("c","C"),
            47:("v","V"),
            48:("b","B"),
            49:("n","N"),
            50:("m","M"),
            51:(",","<"),
            52:(".",">"),
            53:("/","?"),
            # 54 RIGHT SHIFT
            57:(" "," "),
        }

    def get_device(self):
        devices   = [ device for device in listdir(self.input_dir)]
        keyboards = [ device for device in devices if 'kbd' in device ]
        scanners  = [ device for device in devices if ('barcode' in device.lower()) or ('scanner' in device.lower()) ]
        if len(scanners) > 0:
            return InputDevice(join(self.input_dir,scanners[0]))
        elif len(keyboards) > 0:
            return InputDevice(join(self.input_dir,keyboards[0]))
        else:
            return None

    @http.route('/hw_proxy/is_scanner_connected', type='http', auth='admin')
    def is_scanner_connected(self):
        return self.get_device() != None
    
    @http.route('/hw_proxy/scanner', type='http', auth='admin')
    def scanner(self):
        device = self.get_device()
        barcode = []
        shift   = False
        if not device:
            return ''
        else:
            device.grab()
        while True:
            r,w,x = select([device],[],[],10)
            if len(r) == 0: # timeout
                device.ungrab()
                return ''
            for event in device.read():
                if event.type == ecodes.EV_KEY:
                    if event.value == 1: # keydown events
                        print categorize(event)
                        if event.code in self.keymap: 
                            if shift:
                                barcode.append(self.keymap[event.code][1])
                            else:
                                barcode.append(self.keymap[event.code][0])
                        elif event.code == 42 or event.code == 54: # SHIFT
                            shift = True
                        elif event.code == 28: # ENTER
                            device.ungrab()
                            return ''.join(barcode);
                    elif event.value == 0: #keyup events
                        if event.code == 42 or event.code == 54: # LEFT SHIFT
                            shift = False

        
