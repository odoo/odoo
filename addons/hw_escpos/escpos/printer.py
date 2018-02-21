#!/usr/bin/python

import serial
import socket
import usb.core
import usb.util

from escpos import *
from constants import *
from exceptions import *
from time import sleep

class Usb(Escpos):
    """ Define USB printer """

    def __init__(self, idVendor, idProduct, interface=0, in_ep=None, out_ep=None):
        """
        @param idVendor  : Vendor ID
        @param idProduct : Product ID
        @param interface : USB device interface
        @param in_ep     : Input end point
        @param out_ep    : Output end point
        """

        self.errorText = "ERROR PRINTER\n\n\n\n\n\n"+PAPER_FULL_CUT

        self.idVendor  = idVendor
        self.idProduct = idProduct
        self.interface = interface
        self.in_ep     = in_ep
        self.out_ep    = out_ep
        self.open()

    def open(self):
        """ Search device on USB tree and set is as escpos device """
        
        self.device = usb.core.find(idVendor=self.idVendor, idProduct=self.idProduct)
        if self.device is None:
            raise NoDeviceError()
        try:
            if self.device.is_kernel_driver_active(self.interface):
                self.device.detach_kernel_driver(self.interface) 
            self.device.set_configuration()
            usb.util.claim_interface(self.device, self.interface)

            cfg = self.device.get_active_configuration()
            intf = cfg[(0,0)] # first interface
            if self.in_ep is None:
                # Attempt to detect IN/OUT endpoint addresses
                try:
                    is_IN = lambda e: usb.util.endpoint_direction(e.bEndpointAddress) == usb.util.ENDPOINT_IN
                    is_OUT = lambda e: usb.util.endpoint_direction(e.bEndpointAddress) == usb.util.ENDPOINT_OUT
                    endpoint_in = usb.util.find_descriptor(intf, custom_match=is_IN)
                    endpoint_out = usb.util.find_descriptor(intf, custom_match=is_OUT)
                    self.in_ep = endpoint_in.bEndpointAddress
                    self.out_ep = endpoint_out.bEndpointAddress
                except usb.core.USBError:
                    # default values for officially supported printers
                    self.in_ep = 0x82
                    self.out_ep = 0x01

        except usb.core.USBError as e:
            raise HandleDeviceError(e)

    def close(self):
        i = 0
        while True:
            try:
                if not self.device.is_kernel_driver_active(self.interface):
                    usb.util.release_interface(self.device, self.interface)
                    self.device.attach_kernel_driver(self.interface)
                    usb.util.dispose_resources(self.device)
                else:
                    self.device = None
                    return True
            except usb.core.USBError as e:
                i += 1
                if i > 10:
                    return False
        
            sleep(0.1)

    def _raw(self, msg):
        """ Print any command sent in raw format """
        if len(msg) != self.device.write(self.out_ep, msg, self.interface, timeout=5000):
            self.device.write(self.out_ep, self.errorText, self.interface)
            raise TicketNotPrinted()
    
    def __extract_status(self):
        maxiterate = 0
        rep = None
        while rep == None:
            maxiterate += 1
            if maxiterate > 10000:
                raise NoStatusError()
            r = self.device.read(self.in_ep, 20, self.interface).tolist()
            while len(r):
                rep = r.pop()
        return rep

    def get_printer_status(self):
        status = {
            'printer': {}, 
            'offline': {}, 
            'error'  : {}, 
            'paper'  : {},
        }

        self.device.write(self.out_ep, DLE_EOT_PRINTER, self.interface)
        printer = self.__extract_status()    
        self.device.write(self.out_ep, DLE_EOT_OFFLINE, self.interface)
        offline = self.__extract_status()
        self.device.write(self.out_ep, DLE_EOT_ERROR, self.interface)
        error = self.__extract_status()
        self.device.write(self.out_ep, DLE_EOT_PAPER, self.interface)
        paper = self.__extract_status()
            
        status['printer']['status_code']     = printer
        status['printer']['status_error']    = not ((printer & 147) == 18)
        status['printer']['online']          = not bool(printer & 8)
        status['printer']['recovery']        = bool(printer & 32)
        status['printer']['paper_feed_on']   = bool(printer & 64)
        status['printer']['drawer_pin_high'] = bool(printer & 4)
        status['offline']['status_code']     = offline
        status['offline']['status_error']    = not ((offline & 147) == 18)
        status['offline']['cover_open']      = bool(offline & 4)
        status['offline']['paper_feed_on']   = bool(offline & 8)
        status['offline']['paper']           = not bool(offline & 32)
        status['offline']['error']           = bool(offline & 64)
        status['error']['status_code']       = error
        status['error']['status_error']      = not ((error & 147) == 18)
        status['error']['recoverable']       = bool(error & 4)
        status['error']['autocutter']        = bool(error & 8)
        status['error']['unrecoverable']     = bool(error & 32)
        status['error']['auto_recoverable']  = not bool(error & 64)
        status['paper']['status_code']       = paper
        status['paper']['status_error']      = not ((paper & 147) == 18)
        status['paper']['near_end']          = bool(paper & 12)
        status['paper']['present']           = not bool(paper & 96)

        return status

    def __del__(self):
        """ Release USB interface """
        if self.device:
            self.close()
        self.device = None



class Serial(Escpos):
    """ Define Serial printer """

    def __init__(self, devfile="/dev/ttyS0", baudrate=9600, bytesize=8, timeout=1):
        """
        @param devfile  : Device file under dev filesystem
        @param baudrate : Baud rate for serial transmission
        @param bytesize : Serial buffer size
        @param timeout  : Read/Write timeout
        """
        self.devfile  = devfile
        self.baudrate = baudrate
        self.bytesize = bytesize
        self.timeout  = timeout
        self.open()


    def open(self):
        """ Setup serial port and set is as escpos device """
        self.device = serial.Serial(port=self.devfile, baudrate=self.baudrate, bytesize=self.bytesize, parity=serial.PARITY_NONE, stopbits=serial.STOPBITS_ONE, timeout=self.timeout, dsrdtr=True)

        if self.device is not None:
            print "Serial printer enabled"
        else:
            print "Unable to open serial printer on: %s" % self.devfile


    def _raw(self, msg):
        """ Print any command sent in raw format """
        self.device.write(msg)


    def __del__(self):
        """ Close Serial interface """
        if self.device is not None:
            self.device.close()



class Network(Escpos):
    """ Define Network printer """

    def __init__(self,host,port=9100):
        """
        @param host : Printer's hostname or IP address
        @param port : Port to write to
        """
        self.host = host
        self.port = port
        self.open()


    def open(self):
        """ Open TCP socket and set it as escpos device """
        self.device = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.device.connect((self.host, self.port))

        if self.device is None:
            print "Could not open socket for %s" % self.host


    def _raw(self, msg):
        self.device.send(msg)


    def __del__(self):
        """ Close TCP connection """
        self.device.close()

