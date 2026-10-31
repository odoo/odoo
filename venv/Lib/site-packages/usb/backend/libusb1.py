# Copyright 2009-2017 Wander Lairson Costa
# Copyright 2009-2021 PyUSB contributors
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are
# met:
#
# 1. Redistributions of source code must retain the above copyright
# notice, this list of conditions and the following disclaimer.
#
# 2. Redistributions in binary form must reproduce the above copyright
# notice, this list of conditions and the following disclaimer in the
# documentation and/or other materials provided with the distribution.
#
# 3. Neither the name of the copyright holder nor the names of its
# contributors may be used to endorse or promote products derived from
# this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

from ctypes import *
import usb.util
import sys
import logging
from usb._debug import methodtrace
import usb._interop as _interop
import usb._objfinalizer as _objfinalizer
import errno
import math
from usb.core import USBError, USBTimeoutError
import usb.libloader

__author__ = 'Wander Lairson Costa'

__all__ = [
            'get_backend',
            'LIBUSB_SUCCESS',
            'LIBUSB_ERROR_IO',
            'LIBUSB_ERROR_INVALID_PARAM',
            'LIBUSB_ERROR_ACCESS',
            'LIBUSB_ERROR_NO_DEVICE',
            'LIBUSB_ERROR_NOT_FOUND',
            'LIBUSB_ERROR_BUSY',
            'LIBUSB_ERROR_TIMEOUT',
            'LIBUSB_ERROR_OVERFLOW',
            'LIBUSB_ERROR_PIPE',
            'LIBUSB_ERROR_INTERRUPTED',
            'LIBUSB_ERROR_NO_MEM',
            'LIBUSB_ERROR_NOT_SUPPORTED',
            'LIBUSB_ERROR_OTHER',
            'LIBUSB_TRANSFER_COMPLETED',
            'LIBUSB_TRANSFER_ERROR',
            'LIBUSB_TRANSFER_TIMED_OUT',
            'LIBUSB_TRANSFER_CANCELLED',
            'LIBUSB_TRANSFER_STALL',
            'LIBUSB_TRANSFER_NO_DEVICE',
            'LIBUSB_TRANSFER_OVERFLOW',
        ]

_logger = logging.getLogger('usb.backend.libusb1')

# libusb.h

# transfer_type codes
# Control endpoint
_LIBUSB_TRANSFER_TYPE_CONTROL = 0,
# Isochronous endpoint
_LIBUSB_TRANSFER_TYPE_ISOCHRONOUS = 1
# Bulk endpoint
_LIBUSB_TRANSFER_TYPE_BULK = 2
# Interrupt endpoint
_LIBUSB_TRANSFER_TYPE_INTERRUPT = 3

# return codes

LIBUSB_SUCCESS = 0
LIBUSB_ERROR_IO = -1
LIBUSB_ERROR_INVALID_PARAM = -2
LIBUSB_ERROR_ACCESS = -3
LIBUSB_ERROR_NO_DEVICE = -4
LIBUSB_ERROR_NOT_FOUND = -5
LIBUSB_ERROR_BUSY = -6
LIBUSB_ERROR_TIMEOUT = -7
LIBUSB_ERROR_OVERFLOW = -8
LIBUSB_ERROR_PIPE = -9
LIBUSB_ERROR_INTERRUPTED = -10
LIBUSB_ERROR_NO_MEM = -11
LIBUSB_ERROR_NOT_SUPPORTED = -12
LIBUSB_ERROR_OTHER = -99

# map return codes to strings
_str_error_map = {
    LIBUSB_SUCCESS:'Success (no error)',
    LIBUSB_ERROR_IO:'Input/output error',
    LIBUSB_ERROR_INVALID_PARAM:'Invalid parameter',
    LIBUSB_ERROR_ACCESS:'Access denied (insufficient permissions)',
    LIBUSB_ERROR_NO_DEVICE:'No such device (it may have been disconnected)',
    LIBUSB_ERROR_NOT_FOUND:'Entity not found',
    LIBUSB_ERROR_BUSY:'Resource busy',
    LIBUSB_ERROR_TIMEOUT:'Operation timed out',
    LIBUSB_ERROR_OVERFLOW:'Overflow',
    LIBUSB_ERROR_PIPE:'Pipe error',
    LIBUSB_ERROR_INTERRUPTED:'System call interrupted (perhaps due to signal)',
    LIBUSB_ERROR_NO_MEM:'Insufficient memory',
    LIBUSB_ERROR_NOT_SUPPORTED:'Operation not supported or unimplemented on this platform',
    LIBUSB_ERROR_OTHER:'Unknown error'
}

# map return code to errno values
_libusb_errno = {
    0:None,
    LIBUSB_ERROR_IO:errno.__dict__.get('EIO', None),
    LIBUSB_ERROR_INVALID_PARAM:errno.__dict__.get('EINVAL', None),
    LIBUSB_ERROR_ACCESS:errno.__dict__.get('EACCES', None),
    LIBUSB_ERROR_NO_DEVICE:errno.__dict__.get('ENODEV', None),
    LIBUSB_ERROR_NOT_FOUND:errno.__dict__.get('ENOENT', None),
    LIBUSB_ERROR_BUSY:errno.__dict__.get('EBUSY', None),
    LIBUSB_ERROR_TIMEOUT:errno.__dict__.get('ETIMEDOUT', None),
    LIBUSB_ERROR_OVERFLOW:errno.__dict__.get('EOVERFLOW', None),
    LIBUSB_ERROR_PIPE:errno.__dict__.get('EPIPE', None),
    LIBUSB_ERROR_INTERRUPTED:errno.__dict__.get('EINTR', None),
    LIBUSB_ERROR_NO_MEM:errno.__dict__.get('ENOMEM', None),
    LIBUSB_ERROR_NOT_SUPPORTED:errno.__dict__.get('ENOSYS', None),
    LIBUSB_ERROR_OTHER:None
}

# Transfer status codes:
# Note that this does not indicate
# that the entire amount of requested data was transferred.
LIBUSB_TRANSFER_COMPLETED = 0
LIBUSB_TRANSFER_ERROR = 1
LIBUSB_TRANSFER_TIMED_OUT = 2
LIBUSB_TRANSFER_CANCELLED = 3
LIBUSB_TRANSFER_STALL = 4
LIBUSB_TRANSFER_NO_DEVICE = 5
LIBUSB_TRANSFER_OVERFLOW = 6

# map return codes to strings
_str_transfer_error = {
    LIBUSB_TRANSFER_COMPLETED:'Success (no error)',
    LIBUSB_TRANSFER_ERROR:'Transfer failed',
    LIBUSB_TRANSFER_TIMED_OUT:'Transfer timed out',
    LIBUSB_TRANSFER_CANCELLED:'Transfer was cancelled',
    LIBUSB_TRANSFER_STALL:'For bulk/interrupt endpoints: halt condition '\
                          'detected (endpoint stalled). For control '\
                          'endpoints: control request not supported.',
    LIBUSB_TRANSFER_NO_DEVICE:'Device was disconnected',
    LIBUSB_TRANSFER_OVERFLOW:'Device sent more data than requested'
}

# map transfer codes to errno codes
_transfer_errno = {
    LIBUSB_TRANSFER_COMPLETED:0,
    LIBUSB_TRANSFER_ERROR:errno.__dict__.get('EIO', None),
    LIBUSB_TRANSFER_TIMED_OUT:errno.__dict__.get('ETIMEDOUT', None),
    LIBUSB_TRANSFER_CANCELLED:errno.__dict__.get('EAGAIN', None),
    LIBUSB_TRANSFER_STALL:errno.__dict__.get('EIO', None),
    LIBUSB_TRANSFER_NO_DEVICE:errno.__dict__.get('ENODEV', None),
    LIBUSB_TRANSFER_OVERFLOW:errno.__dict__.get('EOVERFLOW', None)
}

def _strerror(errcode):
    try:
        return _lib.libusb_strerror(errcode).decode('utf8')
    except AttributeError:
        return _str_error_map[errcode]

# Data structures

class _libusb_endpoint_descriptor(Structure):
    _fields_ = [('bLength', c_uint8),
                ('bDescriptorType', c_uint8),
                ('bEndpointAddress', c_uint8),
                ('bmAttributes', c_uint8),
                ('wMaxPacketSize', c_uint16),
                ('bInterval', c_uint8),
                ('bRefresh', c_uint8),
                ('bSynchAddress', c_uint8),
                ('extra', POINTER(c_ubyte)),
                ('extra_length', c_int)]

class _libusb_interface_descriptor(Structure):
    _fields_ = [('bLength', c_uint8),
                ('bDescriptorType', c_uint8),
                ('bInterfaceNumber', c_uint8),
                ('bAlternateSetting', c_uint8),
                ('bNumEndpoints', c_uint8),
                ('bInterfaceClass', c_uint8),
                ('bInterfaceSubClass', c_uint8),
                ('bInterfaceProtocol', c_uint8),
                ('iInterface', c_uint8),
                ('endpoint', POINTER(_libusb_endpoint_descriptor)),
                ('extra', POINTER(c_ubyte)),
                ('extra_length', c_int)]

class _libusb_interface(Structure):
    _fields_ = [('altsetting', POINTER(_libusb_interface_descriptor)),
                ('num_altsetting', c_int)]

class _libusb_config_descriptor(Structure):
    _fields_ = [('bLength', c_uint8),
                ('bDescriptorType', c_uint8),
                ('wTotalLength', c_uint16),
                ('bNumInterfaces', c_uint8),
                ('bConfigurationValue', c_uint8),
                ('iConfiguration', c_uint8),
                ('bmAttributes', c_uint8),
                ('bMaxPower', c_uint8),
                ('interface', POINTER(_libusb_interface)),
                ('extra', POINTER(c_ubyte)),
                ('extra_length', c_int)]

class _libusb_device_descriptor(Structure):
    _fields_ = [('bLength', c_uint8),
                ('bDescriptorType', c_uint8),
                ('bcdUSB', c_uint16),
                ('bDeviceClass', c_uint8),
                ('bDeviceSubClass', c_uint8),
                ('bDeviceProtocol', c_uint8),
                ('bMaxPacketSize0', c_uint8),
                ('idVendor', c_uint16),
                ('idProduct', c_uint16),
                ('bcdDevice', c_uint16),
                ('iManufacturer', c_uint8),
                ('iProduct', c_uint8),
                ('iSerialNumber', c_uint8),
                ('bNumConfigurations', c_uint8)]


# Isochronous packet descriptor.
class _libusb_iso_packet_descriptor(Structure):
    _fields_ = [('length', c_uint),
                ('actual_length', c_uint),
                ('status', c_int)] # enum libusb_transfer_status

_libusb_device_handle = c_void_p

class _libusb_transfer(Structure):
    pass
_libusb_transfer_p = POINTER(_libusb_transfer)

_libusb_transfer_cb_fn_p = CFUNCTYPE(None, _libusb_transfer_p)

_libusb_transfer._fields_ = [('dev_handle', _libusb_device_handle),
                             ('flags', c_uint8),
                             ('endpoint', c_uint8),
                             ('type', c_uint8),
                             ('timeout', c_uint),
                             ('status', c_int), # enum libusb_transfer_status
                             ('length', c_int),
                             ('actual_length', c_int),
                             ('callback', _libusb_transfer_cb_fn_p),
                             ('user_data', py_object),
                             ('buffer', c_void_p),
                             ('num_iso_packets', c_int),
                             ('iso_packet_desc', _libusb_iso_packet_descriptor)
]

def _get_iso_packet_list(transfer):
    list_type = _libusb_iso_packet_descriptor * transfer.num_iso_packets
    return list_type.from_address(addressof(transfer.iso_packet_desc))

_lib = None
_lib_object = None

def _load_library(find_library=None):
    # Windows backend uses stdcall calling convention
    #
    # On FreeBSD 8/9, libusb 1.0 and libusb 0.1 are in the same shared
    # object libusb.so, so if we found libusb library name, we must assure
    # it is 1.0 version. We just try to get some symbol from 1.0 version
    if sys.platform == 'win32':
        win_cls = WinDLL
    else:
        win_cls = None

    return usb.libloader.load_locate_library(
                ('usb-1.0', 'libusb-1.0', 'usb'),
                'cygusb-1.0.dll', 'Libusb 1',
                win_cls=win_cls,
                find_library=find_library, check_symbols=('libusb_init',))

def _setup_prototypes(lib):
    # void libusb_set_debug (libusb_context *ctx, int level)
    lib.libusb_set_debug.argtypes = [c_void_p, c_int]

    # int libusb_init (libusb_context **context)
    lib.libusb_init.argtypes = [POINTER(c_void_p)]

    # void libusb_exit (struct libusb_context *ctx)
    lib.libusb_exit.argtypes = [c_void_p]

    # ssize_t libusb_get_device_list (libusb_context *ctx,
    #                                 libusb_device ***list)
    lib.libusb_get_device_list.argtypes = [
            c_void_p,
            POINTER(POINTER(c_void_p))
        ]

    # libusb_device *libusb_get_parent (libusb_device *dev)
    lib.libusb_get_parent.argtypes = [c_void_p]
    lib.libusb_get_parent.restype = c_void_p

    # void libusb_free_device_list (libusb_device **list,
    #                               int unref_devices)
    lib.libusb_free_device_list.argtypes = [
            POINTER(c_void_p),
            c_int
        ]

    # libusb_device *libusb_ref_device (libusb_device *dev)
    lib.libusb_ref_device.argtypes = [c_void_p]
    lib.libusb_ref_device.restype = c_void_p

    # void libusb_unref_device(libusb_device *dev)
    lib.libusb_unref_device.argtypes = [c_void_p]

    # int libusb_open(libusb_device *dev, libusb_device_handle **handle)
    lib.libusb_open.argtypes = [c_void_p, POINTER(_libusb_device_handle)]

    # void libusb_close(libusb_device_handle *dev_handle)
    lib.libusb_close.argtypes = [_libusb_device_handle]

    # int libusb_set_configuration(libusb_device_handle *dev,
    #                              int configuration)
    lib.libusb_set_configuration.argtypes = [_libusb_device_handle, c_int]

    # int libusb_get_configuration(libusb_device_handle *dev,
    #                              int *config)
    lib.libusb_get_configuration.argtypes = [_libusb_device_handle, POINTER(c_int)]

    # int libusb_claim_interface(libusb_device_handle *dev,
    #                               int interface_number)
    lib.libusb_claim_interface.argtypes = [_libusb_device_handle, c_int]

    # int libusb_release_interface(libusb_device_handle *dev,
    #                              int interface_number)
    lib.libusb_release_interface.argtypes = [_libusb_device_handle, c_int]

    # int libusb_set_interface_alt_setting(libusb_device_handle *dev,
    #                                      int interface_number,
    #                                      int alternate_setting)
    lib.libusb_set_interface_alt_setting.argtypes = [
            _libusb_device_handle,
            c_int,
            c_int
        ]

    # int libusb_reset_device (libusb_device_handle *dev)
    lib.libusb_reset_device.argtypes = [_libusb_device_handle]

    # int libusb_kernel_driver_active(libusb_device_handle *dev,
    #                                 int interface)
    lib.libusb_kernel_driver_active.argtypes = [
            _libusb_device_handle,
            c_int
        ]

    # int libusb_detach_kernel_driver(libusb_device_handle *dev,
    #                                 int interface)
    lib.libusb_detach_kernel_driver.argtypes = [
            _libusb_device_handle,
            c_int
        ]

    # int libusb_attach_kernel_driver(libusb_device_handle *dev,
    #                                 int interface)
    lib.libusb_attach_kernel_driver.argtypes = [
            _libusb_device_handle,
            c_int
        ]

    # int libusb_get_device_descriptor(
    #                   libusb_device *dev,
    #                   struct libusb_device_descriptor *desc
    #               )
    lib.libusb_get_device_descriptor.argtypes = [
            c_void_p,
            POINTER(_libusb_device_descriptor)
        ]

    # int libusb_get_config_descriptor(
    #           libusb_device *dev,
    #           uint8_t config_index,
    #           struct libusb_config_descriptor **config
    #       )
    lib.libusb_get_config_descriptor.argtypes = [
            c_void_p,
            c_uint8,
            POINTER(POINTER(_libusb_config_descriptor))
        ]

    # void  libusb_free_config_descriptor(
    #           struct libusb_config_descriptor *config
    #   )
    lib.libusb_free_config_descriptor.argtypes = [
            POINTER(_libusb_config_descriptor)
        ]

    # int libusb_get_string_descriptor_ascii(libusb_device_handle *dev,
    #                                         uint8_t desc_index,
    #                                         unsigned char *data,
    #                                         int length)
    lib.libusb_get_string_descriptor_ascii.argtypes = [
            _libusb_device_handle,
            c_uint8,
            POINTER(c_ubyte),
            c_int
        ]

    # int libusb_control_transfer(libusb_device_handle *dev_handle,
    #                             uint8_t bmRequestType,
    #                             uint8_t bRequest,
    #                             uint16_t wValue,
    #                             uint16_t wIndex,
    #                             unsigned char *data,
    #                             uint16_t wLength,
    #                             unsigned int timeout)
    lib.libusb_control_transfer.argtypes = [
            _libusb_device_handle,
            c_uint8,
            c_uint8,
            c_uint16,
            c_uint16,
            POINTER(c_ubyte),
            c_uint16,
            c_uint
        ]

    #int libusb_bulk_transfer(
    #           struct libusb_device_handle *dev_handle,
    #           unsigned char endpoint,
    #           unsigned char *data,
    #           int length,
    #           int *transferred,
    #           unsigned int timeout
    #       )
    lib.libusb_bulk_transfer.argtypes = [
                _libusb_device_handle,
                c_ubyte,
                POINTER(c_ubyte),
                c_int,
                POINTER(c_int),
                c_uint
            ]

    # int libusb_interrupt_transfer(
    #               libusb_device_handle *dev_handle,
    #               unsigned char endpoint,
    #               unsigned char *data,
    #               int length,
    #               int *actual_length,
    #               unsigned int timeout
    #           );
    lib.libusb_interrupt_transfer.argtypes = [
                    _libusb_device_handle,
                    c_ubyte,
                    POINTER(c_ubyte),
                    c_int,
                    POINTER(c_int),
                    c_uint
                ]

    # libusb_transfer* libusb_alloc_transfer(int iso_packets);
    lib.libusb_alloc_transfer.argtypes = [c_int]
    lib.libusb_alloc_transfer.restype = POINTER(_libusb_transfer)

    # void libusb_free_transfer(struct libusb_transfer *transfer)
    lib.libusb_free_transfer.argtypes = [POINTER(_libusb_transfer)]

    # int libusb_submit_transfer(struct libusb_transfer *transfer);
    lib.libusb_submit_transfer.argtypes = [POINTER(_libusb_transfer)]

    if hasattr(lib, 'libusb_strerror'):
        # const char *libusb_strerror(enum libusb_error errcode)
        lib.libusb_strerror.argtypes = [c_uint]
        lib.libusb_strerror.restype = c_char_p

    # int libusb_clear_halt(libusb_device_handle *dev, unsigned char endpoint)
    lib.libusb_clear_halt.argtypes = [_libusb_device_handle, c_ubyte]

    # void libusb_set_iso_packet_lengths(
    #               libusb_transfer* transfer,
    #               unsigned int length
    #           );
    def libusb_set_iso_packet_lengths(transfer_p, length):
        r"""This function is inline in the libusb.h file, so we must implement
            it.

        lib.libusb_set_iso_packet_lengths.argtypes = [
                        POINTER(_libusb_transfer),
                        c_int
                    ]
        """
        transfer = transfer_p.contents
        for iso_packet_desc in _get_iso_packet_list(transfer):
            iso_packet_desc.length = length
    lib.libusb_set_iso_packet_lengths = libusb_set_iso_packet_lengths

    #int libusb_get_max_iso_packet_size(libusb_device* dev,
    #                                   unsigned char endpoint);
    lib.libusb_get_max_iso_packet_size.argtypes = [c_void_p,
                                                   c_ubyte]

    # void libusb_fill_iso_transfer(
    #               struct libusb_transfer* transfer,
    #               libusb_device_handle*  dev_handle,
    #               unsigned char endpoint,
    #               unsigned char* buffer,
    #               int length,
    #               int num_iso_packets,
    #               libusb_transfer_cb_fn   callback,
    #               void * user_data,
    #               unsigned int timeout
    #           );
    def libusb_fill_iso_transfer(_libusb_transfer_p, dev_handle, endpoint, buffer, length,
                                 num_iso_packets, callback, user_data, timeout):
        r"""This function is inline in the libusb.h file, so we must implement
            it.

        lib.libusb_fill_iso_transfer.argtypes = [
                       _libusb_transfer,
                       _libusb_device_handle,
                       c_ubyte,
                       POINTER(c_ubyte),
                       c_int,
                       c_int,
                       _libusb_transfer_cb_fn_p,
                       c_void_p,
                       c_uint
                   ]
        """
        transfer = _libusb_transfer_p.contents
        transfer.dev_handle = dev_handle
        transfer.endpoint = endpoint
        transfer.type = _LIBUSB_TRANSFER_TYPE_ISOCHRONOUS
        transfer.timeout = timeout
        transfer.buffer = cast(buffer, c_void_p)
        transfer.length = length
        transfer.num_iso_packets = num_iso_packets
        transfer.user_data = user_data
        transfer.callback = callback
    lib.libusb_fill_iso_transfer = libusb_fill_iso_transfer

    # uint8_t libusb_get_bus_number(libusb_device *dev)
    lib.libusb_get_bus_number.argtypes = [c_void_p]
    lib.libusb_get_bus_number.restype = c_uint8

    # uint8_t libusb_get_device_address(libusb_device *dev)
    lib.libusb_get_device_address.argtypes = [c_void_p]
    lib.libusb_get_device_address.restype = c_uint8

    try:
        # uint8_t libusb_get_device_speed(libusb_device *dev)
        lib.libusb_get_device_speed.argtypes = [c_void_p]
        lib.libusb_get_device_speed.restype = c_uint8
    except AttributeError:
        pass

    try:
        # uint8_t libusb_get_port_number(libusb_device *dev)
        lib.libusb_get_port_number.argtypes = [c_void_p]
        lib.libusb_get_port_number.restype = c_uint8
    except AttributeError:
        pass

    try:
        # int libusb_get_port_numbers(libusb_device *dev,
        #                             uint8_t* port_numbers,
        #                             int port_numbers_len)
        lib.libusb_get_port_numbers.argtypes = [
                c_void_p,
                POINTER(c_uint8),
                c_int
            ]
        lib.libusb_get_port_numbers.restype = c_int
    except AttributeError:
        pass

    #int libusb_handle_events(libusb_context *ctx);
    lib.libusb_handle_events.argtypes = [c_void_p]

# check a libusb function call
def _check(ret):
    if hasattr(ret, 'value'):
        ret = ret.value

    if ret < 0:
        if ret == LIBUSB_ERROR_NOT_SUPPORTED:
            raise NotImplementedError(_strerror(ret))
        elif ret == LIBUSB_ERROR_TIMEOUT:
            raise USBTimeoutError(_strerror(ret), ret, _libusb_errno[ret])
        else:
            raise USBError(_strerror(ret), ret, _libusb_errno[ret])

    return ret

# wrap a device
class _Device(_objfinalizer.AutoFinalizedObject):
    def __init__(self, devid):
        self.devid = _lib.libusb_ref_device(devid)
    def _finalize_object(self):
        _lib.libusb_unref_device(self.devid)

# wrap a descriptor and keep a reference to another object
# Thanks to Thomas Reitmayr.
class _WrapDescriptor(object):
    def __init__(self, desc, obj = None):
        self.obj = obj
        self.desc = desc
    def __getattr__(self, name):
        return getattr(self.desc, name)

# wrap a configuration descriptor
class _ConfigDescriptor(_objfinalizer.AutoFinalizedObject):
    def __init__(self, desc):
        self.desc = desc
    def _finalize_object(self):
        _lib.libusb_free_config_descriptor(self.desc)
    def __getattr__(self, name):
        return getattr(self.desc.contents, name)


# iterator for libusb devices
class _DevIterator(_objfinalizer.AutoFinalizedObject):
    def __init__(self, ctx):
        self.dev_list = POINTER(c_void_p)()
        self.num_devs = _check(_lib.libusb_get_device_list(
                                    ctx,
                                    byref(self.dev_list))
                                )
    def __iter__(self):
        for i in range(self.num_devs):
            yield _Device(self.dev_list[i])
    def _finalize_object(self):
        _lib.libusb_free_device_list(self.dev_list, 1)

class _DeviceHandle(object):
    def __init__(self, dev):
        self.handle = _libusb_device_handle()
        self.devid = dev.devid
        _check(_lib.libusb_open(self.devid, byref(self.handle)))

class _IsoTransferHandler(_objfinalizer.AutoFinalizedObject):
    def __init__(self, dev_handle, ep, buff, timeout):
        address, length = buff.buffer_info()

        packet_length = _lib.libusb_get_max_iso_packet_size(dev_handle.devid, ep)
        packet_count = int(math.ceil(float(length) / packet_length))

        self.transfer = _lib.libusb_alloc_transfer(packet_count)

        _lib.libusb_fill_iso_transfer(self.transfer,
                                      dev_handle.handle,
                                      ep,
                                      cast(address, POINTER(c_ubyte)),
                                      length,
                                      packet_count,
                                      _libusb_transfer_cb_fn_p(self.__callback),
                                      None,
                                      timeout)

        self.__set_packets_length(length, packet_length)

    def _finalize_object(self):
        _lib.libusb_free_transfer(self.transfer)

    def submit(self, ctx = None):
        self.__callback_done = 0
        _check(_lib.libusb_submit_transfer(self.transfer))

        while not self.__callback_done:
            _check(_lib.libusb_handle_events(ctx))

        status = int(self.transfer.contents.status)
        if status != LIBUSB_TRANSFER_COMPLETED:
            raise usb.USBError(_str_transfer_error[status],
                               status,
                               _transfer_errno[status])

        return self.__compute_size_transf_data()

    def __compute_size_transf_data(self):
        return sum([t.actual_length for t in
                    _get_iso_packet_list(self.transfer.contents)])

    def __set_packets_length(self, n, packet_length):
        _lib.libusb_set_iso_packet_lengths(self.transfer, packet_length)
        r = n % packet_length
        if r:
            iso_packets = _get_iso_packet_list(self.transfer.contents)
            # When the device is disconnected, this list may
            # return with length 0
            if len(iso_packets):
                iso_packets[-1].length = r

    def __callback(self, transfer):
        self.__callback_done = 1

# implementation of libusb 1.0 backend
class _LibUSB(usb.backend.IBackend):
    @methodtrace(_logger)
    def __init__(self, lib):
        usb.backend.IBackend.__init__(self)
        self.lib = lib
        self.ctx = c_void_p()
        _check(self.lib.libusb_init(byref(self.ctx)))

    @methodtrace(_logger)
    def _finalize_object(self):
        if self.ctx:
            self.lib.libusb_exit(self.ctx)


    @methodtrace(_logger)
    def enumerate_devices(self):
        return _DevIterator(self.ctx)

    @methodtrace(_logger)
    def get_parent(self, dev):
        _parent = self.lib.libusb_get_parent(dev.devid)
        if _parent is None:
            return None
        else:
            return _Device(_parent)

    @methodtrace(_logger)
    def get_device_descriptor(self, dev):
        dev_desc = _libusb_device_descriptor()
        _check(self.lib.libusb_get_device_descriptor(dev.devid, byref(dev_desc)))
        dev_desc.bus = self.lib.libusb_get_bus_number(dev.devid)
        dev_desc.address = self.lib.libusb_get_device_address(dev.devid)

        # Only available in newer versions of libusb
        try:
            dev_desc.speed = self.lib.libusb_get_device_speed(dev.devid)
        except AttributeError:
            dev_desc.speed = None

        # Only available in newer versions of libusb
        try:
            dev_desc.port_number = self.lib.libusb_get_port_number(dev.devid)
        except AttributeError:
            dev_desc.port_number = None

        # Only available in newer versions of libusb
        try:
            buff = (c_uint8 * 7)()  # USB 3.0 maximum depth is 7
            written = dev_desc.port_numbers = self.lib.libusb_get_port_numbers(
                    dev.devid, buff, len(buff))
            if written > 0:
                dev_desc.port_numbers = tuple(buff[:written])
            else:
                dev_desc.port_numbers = None
        except AttributeError:
            dev_desc.port_numbers = None

        return dev_desc

    @methodtrace(_logger)
    def get_configuration_descriptor(self, dev, config):
        cfg = POINTER(_libusb_config_descriptor)()
        _check(self.lib.libusb_get_config_descriptor(
                dev.devid,
                config, byref(cfg)))
        config_desc = _ConfigDescriptor(cfg)
        config_desc.extra_descriptors = (
                config_desc.extra[:config_desc.extra_length])
        return config_desc

    @methodtrace(_logger)
    def get_interface_descriptor(self, dev, intf, alt, config):
        cfg = self.get_configuration_descriptor(dev, config)
        if intf >= cfg.bNumInterfaces:
            raise IndexError('Invalid interface index ' + str(intf))
        i = cfg.interface[intf]
        if alt >= i.num_altsetting:
            raise IndexError('Invalid alternate setting index ' + str(alt))
        intf_desc = i.altsetting[alt]
        intf_desc.extra_descriptors = intf_desc.extra[:intf_desc.extra_length]
        return _WrapDescriptor(intf_desc, cfg)

    @methodtrace(_logger)
    def get_endpoint_descriptor(self, dev, ep, intf, alt, config):
        i = self.get_interface_descriptor(dev, intf, alt, config)
        if ep > i.bNumEndpoints:
            raise IndexError('Invalid endpoint index ' + str(ep))
        ep_desc = i.endpoint[ep]
        ep_desc.extra_descriptors = ep_desc.extra[:ep_desc.extra_length]
        return _WrapDescriptor(ep_desc, i)

    @methodtrace(_logger)
    def open_device(self, dev):
        return _DeviceHandle(dev)

    @methodtrace(_logger)
    def close_device(self, dev_handle):
        self.lib.libusb_close(dev_handle.handle)

    @methodtrace(_logger)
    def set_configuration(self, dev_handle, config_value):
        _check(self.lib.libusb_set_configuration(dev_handle.handle, config_value))

    @methodtrace(_logger)
    def get_configuration(self, dev_handle):
        config = c_int()
        _check(self.lib.libusb_get_configuration(dev_handle.handle, byref(config)))
        return config.value

    @methodtrace(_logger)
    def set_interface_altsetting(self, dev_handle, intf, altsetting):
        _check(self.lib.libusb_set_interface_alt_setting(
                                dev_handle.handle,
                                intf,
                                altsetting))

    @methodtrace(_logger)
    def claim_interface(self, dev_handle, intf):
        _check(self.lib.libusb_claim_interface(dev_handle.handle, intf))

    @methodtrace(_logger)
    def release_interface(self, dev_handle, intf):
        _check(self.lib.libusb_release_interface(dev_handle.handle, intf))

    @methodtrace(_logger)
    def bulk_write(self, dev_handle, ep, intf, data, timeout):
        return self.__write(self.lib.libusb_bulk_transfer,
                            dev_handle,
                            ep,
                            intf,
                            data,
                            timeout)

    @methodtrace(_logger)
    def bulk_read(self, dev_handle, ep, intf, buff, timeout):
        return self.__read(self.lib.libusb_bulk_transfer,
                           dev_handle,
                           ep,
                           intf,
                           buff,
                           timeout)

    @methodtrace(_logger)
    def intr_write(self, dev_handle, ep, intf, data, timeout):
        return self.__write(self.lib.libusb_interrupt_transfer,
                            dev_handle,
                            ep,
                            intf,
                            data,
                            timeout)

    @methodtrace(_logger)
    def intr_read(self, dev_handle, ep, intf, buff, timeout):
        return self.__read(self.lib.libusb_interrupt_transfer,
                           dev_handle,
                           ep,
                           intf,
                           buff,
                           timeout)

    @methodtrace(_logger)
    def iso_write(self, dev_handle, ep, intf, data, timeout):
        handler = _IsoTransferHandler(dev_handle, ep, data, timeout)
        return handler.submit(self.ctx)

    @methodtrace(_logger)
    def iso_read(self, dev_handle, ep, intf, buff, timeout):
        handler = _IsoTransferHandler(dev_handle, ep, buff, timeout)
        return handler.submit(self.ctx)

    @methodtrace(_logger)
    def ctrl_transfer(self,
                      dev_handle,
                      bmRequestType,
                      bRequest,
                      wValue,
                      wIndex,
                      data,
                      timeout):
        addr, length = data.buffer_info()
        length *= data.itemsize

        ret = _check(self.lib.libusb_control_transfer(
                                        dev_handle.handle,
                                        bmRequestType,
                                        bRequest,
                                        wValue,
                                        wIndex,
                                        cast(addr, POINTER(c_ubyte)),
                                        length,
                                        timeout))

        return ret

    @methodtrace(_logger)
    def clear_halt(self, dev_handle, ep):
        _check(self.lib.libusb_clear_halt(dev_handle.handle, ep))

    @methodtrace(_logger)
    def reset_device(self, dev_handle):
        _check(self.lib.libusb_reset_device(dev_handle.handle))

    @methodtrace(_logger)
    def is_kernel_driver_active(self, dev_handle, intf):
        return bool(_check(self.lib.libusb_kernel_driver_active(dev_handle.handle,
                        intf)))

    @methodtrace(_logger)
    def detach_kernel_driver(self, dev_handle, intf):
        _check(self.lib.libusb_detach_kernel_driver(dev_handle.handle, intf))

    @methodtrace(_logger)
    def attach_kernel_driver(self, dev_handle, intf):
        _check(self.lib.libusb_attach_kernel_driver(dev_handle.handle, intf))

    def __write(self, fn, dev_handle, ep, intf, data, timeout):
        address, length = data.buffer_info()
        length *= data.itemsize
        transferred = c_int()
        retval = fn(dev_handle.handle,
                  ep,
                  cast(address, POINTER(c_ubyte)),
                  length,
                  byref(transferred),
                  timeout)
        # do not assume LIBUSB_ERROR_TIMEOUT means no I/O.
        if not (transferred.value and retval == LIBUSB_ERROR_TIMEOUT):
            _check(retval)

        return transferred.value

    def __read(self, fn, dev_handle, ep, intf, buff, timeout):
        address, length = buff.buffer_info()
        length *= buff.itemsize
        transferred = c_int()
        retval = fn(dev_handle.handle,
                  ep,
                  cast(address, POINTER(c_ubyte)),
                  length,
                  byref(transferred),
                  timeout)
        # do not assume LIBUSB_ERROR_TIMEOUT means no I/O.
        if not (transferred.value and retval == LIBUSB_ERROR_TIMEOUT):
            _check(retval)
        return transferred.value

def get_backend(find_library=None):
    global _lib, _lib_object
    try:
        if _lib_object is None:
            _lib = _load_library(find_library=find_library)
            _setup_prototypes(_lib)
            _lib_object = _LibUSB(_lib)
        return _lib_object
    except usb.libloader.LibraryException:
        # exception already logged (if any)
        _logger.error('Error loading libusb 1.0 backend', exc_info=False)
        return None
    except Exception:
        _logger.error('Error loading libusb 1.0 backend', exc_info=True)
        return None
