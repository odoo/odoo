# -*- coding: utf-8 -*-
import logging
import os
import time
from os import listdir
from os.path import join
from threading import Thread, Lock
from select import select
from Queue import Queue, Empty

import openerp
import openerp.addons.hw_proxy.controllers.main as hw_proxy
from openerp import http
from openerp.http import request
from openerp.tools.translate import _

_logger = logging.getLogger(__name__)

try:
    import evdev
except ImportError:
    _logger.error('Odoo module hw_scanner depends on the evdev python module')
    evdev = None


class Scanner(Thread):
    def __init__(self):
        Thread.__init__(self)
        self.lock = Lock()
        self.status = {'status':'connecting', 'messages':[]}
        self.input_dir = '/dev/input/by-id/'
        self.barcodes = Queue()
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

    def lockedstart(self):
        with self.lock:
            if not self.isAlive():
                self.daemon = True
                self.start()

    def set_status(self, status, message = None):
        if status == self.status['status']:
            if message != None and message != self.status['messages'][-1]:
                self.status['messages'].append(message)
        else:
            self.status['status'] = status
            if message:
                self.status['messages'] = [message]
            else:
                self.status['messages'] = []

        if status == 'error' and message:
            _logger.error('Barcode Scanner Error: '+message)
        elif status == 'disconnected' and message:
            _logger.warning('Disconnected Barcode Scanner: '+message)

    def get_device(self):
        try:
            if not evdev:
                return None
            devices   = [ device for device in listdir(self.input_dir)]
            keyboards = [ device for device in devices if ('kbd' in device) and ('keyboard' not in device.lower())]
            scanners  = [ device for device in devices if ('barcode' in device.lower()) or ('scanner' in device.lower())]
            if len(scanners) > 0:
                self.set_status('connected','Connected to '+scanners[0])
                return evdev.InputDevice(join(self.input_dir,scanners[0]))
            elif len(keyboards) > 0:
                self.set_status('connected','Connected to '+keyboards[0])
                return evdev.InputDevice(join(self.input_dir,keyboards[0]))
            else:
                self.set_status('disconnected','Barcode Scanner Not Found')
                return None
        except Exception as e:
            self.set_status('error',str(e))
            return None

    def get_barcode(self):
        """ Returns a scanned barcode. Will wait at most 5 seconds to get a barcode, and will
            return barcode scanned in the past if they are not older than 5 seconds and have not
            been returned before. This is necessary to catch barcodes scanned while the POS is
            busy reading another barcode
        """

        self.lockedstart()

        while True:
            try:
                timestamp, barcode = self.barcodes.get(True, 5)
                if timestamp > time.time() - 5: 
                    return barcode
            except Empty:
                return ''
    
    def get_status(self):
        self.lockedstart()
        return self.status

    def run(self):
        """ This will start a loop that catches all keyboard events, parse barcode
            sequences and put them on a timestamped queue that can be consumed by
            the point of sale's requests for barcode events 
        """
        
        self.barcodes = Queue()
        
        barcode  = []
        shift    = False
        device   = None

        while True: # barcodes loop
            if device:  # ungrab device between barcodes and timeouts for plug & play
                try:
                    device.ungrab() 
                except Exception as e:
                    self.set_status('error',str(e))
            device = self.get_device()
            if not device:
                time.sleep(5)   # wait until a suitable device is plugged
            else:
                try:
                    device.grab()
                    shift = False
                    barcode = []

                    while True: # keycode loop
                        r,w,x = select([device],[],[],5)
                        if len(r) == 0: # timeout
                            break
                        events = device.read()

                        for event in events:
                            if event.type == evdev.ecodes.EV_KEY:
                                #_logger.debug('Evdev Keyboard event %s',evdev.categorize(event))
                                if event.value == 1: # keydown events
                                    if event.code in self.keymap: 
                                        if shift:
                                            barcode.append(self.keymap[event.code][1])
                                        else:
                                            barcode.append(self.keymap[event.code][0])
                                    elif event.code == 42 or event.code == 54: # SHIFT
                                        shift = True
                                    elif event.code == 28: # ENTER, end of barcode
                                        self.barcodes.put( (time.time(),''.join(barcode)) )
                                        barcode = []
                                elif event.value == 0: #keyup events
                                    if event.code == 42 or event.code == 54: # LEFT SHIFT
                                        shift = False

                except Exception as e:
                    self.set_status('error',str(e))

s = Scanner()

hw_proxy.drivers['scanner'] = s

class ScannerDriver(hw_proxy.Proxy):
    @http.route('/hw_proxy/scanner', type='json', auth='none', cors='*')
    def scanner(self):
        return s.get_barcode()
        
        
