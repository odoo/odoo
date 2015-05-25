#!/usr/bin/python

# This is a list of esc/pos compatible usb printers. The vendor and product ids can be found by
# typing lsusb in a linux terminal, this will give you the ids in the form ID VENDOR:PRODUCT

device_list_usb = [
    { 'vendor' : 0x04b8, 'product' : 0x0e03, 'name' : 'Epson TM-T20' },
    { 'vendor' : 0x04b8, 'product' : 0x0202, 'name' : 'Epson TM-T70' },
    { 'vendor' : 0x04b8, 'product' : 0x0e15, 'name' : 'Epson TM-T20II' },
]

# This is a list of esc/pos compatible file printers. Mostly they are raw file printers, which means
# they are connected via usb but create a virtual file /dev/usb/lp0 or sort of

device_list_file = [
    { 'devfile' : "/dev/usb/lp0", 'name' : 'File printer /dev/usb/lp0' }
]
