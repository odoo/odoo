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
    import serial
except ImportError:
    _logger.error('Odoo module hw_scale depends on the pyserial python module')
    serial = None


class Scale(Thread):
    def __init__(self):
        Thread.__init__(self)
        self.lock = Lock()
        self.scalelock = Lock()
        self.status = {'status':'connecting', 'messages':[]}
        self.input_dir = '/dev/serial/by-path/'
        self.weight = 0
        self.weight_info = 'ok'
        self.device = None
        self.probed_device_paths = []
        self.path_to_scale = ''

    def lockedstart(self):
        with self.lock:
            if not self.isAlive():
                self.daemon = True
                self.start()

    def set_status(self, status, message = None):
        if status == self.status['status']:
            if message != None and message != self.status['messages'][-1]:
                self.status['messages'].append(message)

                if status == 'error' and message:
                    _logger.error('Scale Error: '+message)
                elif status == 'disconnected' and message:
                    _logger.warning('Disconnected Scale: '+message)
        else:
            self.status['status'] = status
            if message:
                self.status['messages'] = [message]
            else:
                self.status['messages'] = []

            if status == 'error' and message:
                _logger.error('Scale Error: '+message)
            elif status == 'disconnected' and message:
                _logger.info('Disconnected Scale: %s', message)

    def _get_raw_response(self, connection):
        response = ""
        while True:
            byte = connection.read(1)

            if byte:
                response += byte
            else:
                return response

    def get_device(self):
        try:
            if not os.path.exists(self.input_dir):
                self.set_status('disconnected','Scale Not Found')
                return None
            devices = [ device for device in listdir(self.input_dir)]

            if len(devices) > 0:
                for device in devices:
                    path = self.input_dir + device

                    # don't keep probing devices that are not a scale,
                    # only keep probing if in the past the device was
                    # confirmed to be a scale
                    if path not in self.probed_device_paths or path == self.path_to_scale:
                        _logger.debug('Probing: ' + path)
                        connection = serial.Serial(path,
                                                   baudrate = 9600,
                                                   bytesize = serial.SEVENBITS,
                                                   stopbits = serial.STOPBITS_ONE,
                                                   parity   = serial.PARITY_EVEN,
                                                   timeout  = 1,
                                                   writeTimeout = 1)

                        connection.write("W")
                        self.probed_device_paths.append(path)

                        if self._get_raw_response(connection):
                            _logger.debug(path + ' is scale')
                            self.path_to_scale = path
                            self.set_status('connected','Connected to '+device)
                            connection.timeout = 0.02
                            connection.writeTimeout = 0.02
                            return connection
                    else:
                        _logger.debug('Already probed: ' + path)

            self.set_status('disconnected','Scale Not Found')
            return None
        except Exception as e:
            self.set_status('error',str(e))
            return None

    def get_weight(self):
        self.lockedstart()
        return self.weight

    def get_weight_info(self):
        self.lockedstart()
        return self.weight_info
    
    def get_status(self):
        self.lockedstart()
        return self.status

    def read_weight(self):
        with self.scalelock:
            if self.device:
                try:
                    self.device.write('W')
                    time.sleep(0.2)
                    answer = []

                    while True:
                        char = self.device.read(1)
                        if not char: 
                            break
                        else:
                            answer.append(char)

                    if '?' in answer:
                        stat = ord(answer[answer.index('?')+1])
                        if stat == 0: 
                            self.weight_info = 'ok'
                        else:
                            self.weight_info = []
                            if stat & 1 :
                                self.weight_info.append('moving')
                            if stat & 1 << 1:
                                self.weight_info.append('over_capacity')
                            if stat & 1 << 2:
                                self.weight_info.append('negative')
                                self.weight = 0.0
                            if stat & 1 << 3:
                                self.weight_info.append('outside_zero_capture_range')
                            if stat & 1 << 4:
                                self.weight_info.append('center_of_zero')
                            if stat & 1 << 5:
                                self.weight_info.append('net_weight')
                    else:
                        answer = answer[1:-1]
                        if 'N' in answer:
                            answer = answer[0:-1]
                        try:
                            self.weight = float(''.join(answer))
                        except ValueError as v:
                            self.set_status('error','No data Received, please power-cycle the scale');
                            self.device = None
                        
                except Exception as e:
                    self.set_status('error',str(e))
                    self.device = None

    def set_zero(self):
        with self.scalelock:
            if self.device:
                try: 
                    self.device.write('Z')
                except Exception as e:
                    self.set_status('error',str(e))
                    self.device = None

    def set_tare(self):
        with self.scalelock:
            if self.device:
                try: 
                    self.device.write('T')
                except Exception as e:
                    self.set_status('error',str(e))
                    self.device = None

    def clear_tare(self):
        with self.scalelock:
            if self.device:
                try: 
                    self.device.write('C')
                except Exception as e:
                    self.set_status('error',str(e))
                    self.device = None

    def run(self):
        self.device   = None

        while True: 
            if self.device:
                self.read_weight()
                time.sleep(0.15)
            else:
                with self.scalelock:
                    self.device = self.get_device()
                if not self.device:
                    time.sleep(5)

scale_thread = None
if serial:
    scale_thread = Scale()
    hw_proxy.drivers['scale'] = scale_thread

class ScaleDriver(hw_proxy.Proxy):
    @http.route('/hw_proxy/scale_read/', type='json', auth='none', cors='*')
    def scale_read(self):
        if scale_thread:
            return {'weight': scale_thread.get_weight(), 'unit':'kg', 'info': scale_thread.get_weight_info()}
        return None

    @http.route('/hw_proxy/scale_zero/', type='json', auth='none', cors='*')
    def scale_zero(self):
        if scale_thread:
            scale_thread.set_zero()
        return True

    @http.route('/hw_proxy/scale_tare/', type='json', auth='none', cors='*')
    def scale_tare(self):
        if scale_thread:
            scale_thread.set_tare()
        return True

    @http.route('/hw_proxy/scale_clear_tare/', type='json', auth='none', cors='*')
    def scale_clear_tare(self):
        if scale_thread:
            scale_thread.clear_tare()
        return True
        
        
