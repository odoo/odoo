""" ESC/POS Exceptions classes """

import os

class Error(Exception):
    """ Base class for ESC/POS errors """
    def __init__(self, msg, status=None):
        Exception.__init__(self)
        self.msg = msg
        self.resultcode = 1
        if status is not None:
            self.resultcode = status

    def __str__(self):
        return self.msg

# Result/Exit codes
# 0  = success
# 10 = No Barcode type defined
# 20 = Barcode size values are out of range
# 30 = Barcode text not supplied
# 40 = Image height is too large
# 50 = No string supplied to be printed
# 60 = Invalid pin to send Cash Drawer pulse


class BarcodeTypeError(Error):
    def __init__(self, msg=""):
        Error.__init__(self, msg)
        self.msg = msg
        self.resultcode = 10

    def __str__(self):
        return "No Barcode type is defined"

class BarcodeSizeError(Error):
    def __init__(self, msg=""):
        Error.__init__(self, msg)
        self.msg = msg
        self.resultcode = 20

    def __str__(self):
        return "Barcode size is out of range"

class BarcodeCodeError(Error):
    def __init__(self, msg=""):
        Error.__init__(self, msg)
        self.msg = msg
        self.resultcode = 30

    def __str__(self):
        return "Code was not supplied"

class ImageSizeError(Error):
    def __init__(self, msg=""):
        Error.__init__(self, msg)
        self.msg = msg
        self.resultcode = 40

    def __str__(self):
        return "Image height is longer than 255px and can't be printed"

class TextError(Error):
    def __init__(self, msg=""):
        Error.__init__(self, msg)
        self.msg = msg
        self.resultcode = 50

    def __str__(self):
        return "Text string must be supplied to the text() method"


class CashDrawerError(Error):
    def __init__(self, msg=""):
        Error.__init__(self, msg)
        self.msg = msg
        self.resultcode = 60

    def __str__(self):
        return "Valid pin must be set to send pulse"

class NoStatusError(Error):
    def __init__(self, msg=""):
        Error.__init__(self, msg)
        self.msg = msg
        self.resultcode = 70

    def __str__(self):
        return "Impossible to get status from the printer: " + str(self.msg)

class TicketNotPrinted(Error):
    def __init__(self, msg=""):
        Error.__init__(self, msg)
        self.msg = msg
        self.resultcode = 80

    def __str__(self):
        return "A part of the ticket was not been printed: " + str(self.msg)

class NoDeviceError(Error):
    def __init__(self, msg=""):
        Error.__init__(self, msg)
        self.msg = msg
        self.resultcode = 90

    def __str__(self):
        return str(self.msg)

class HandleDeviceError(Error):
    def __init__(self, msg=""):
        Error.__init__(self, msg)
        self.msg = msg
        self.resultcode = 100

    def __str__(self):
        return str(self.msg)
