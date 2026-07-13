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
import errno
import os
import usb.backend
import usb.util
import sys
from usb.core import USBError, USBTimeoutError
from usb._debug import methodtrace
import usb._interop as _interop
import logging
import usb.libloader

__author__ = 'Wander Lairson Costa'

__all__ = ['get_backend']

_logger = logging.getLogger('usb.backend.libusb0')

_USBFS_MAXDRIVERNAME = 255

# usb.h

if sys.platform.find('bsd') != -1 or sys.platform.find('mac') != -1 or \
        sys.platform.find('darwin') != -1 or sys.platform.find('sunos5') != -1:
    _PATH_MAX = 1024
elif sys.platform == 'win32' or sys.platform == 'cygwin':
    _PATH_MAX = 511
else:
    _PATH_MAX = os.pathconf('.', 'PC_PATH_MAX')

# libusb-win32 makes all structures packed, while
# default libusb only does for some structures
# _PackPolicy defines the structure packing according
# to the platform.
class _PackPolicy(object):
    pass

if sys.platform == 'win32' or sys.platform == 'cygwin':
    _PackPolicy._pack_ = 1

# Data structures

class _usb_descriptor_header(Structure):
    _pack_ = 1
    _fields_ = [('blength', c_uint8),
                ('bDescriptorType', c_uint8)]

class _usb_string_descriptor(Structure):
    _pack_ = 1
    _fields_ = [('bLength', c_uint8),
                ('bDescriptorType', c_uint8),
                ('wData', c_uint16)]

class _usb_endpoint_descriptor(Structure, _PackPolicy):
    _fields_ = [('bLength', c_uint8),
                ('bDescriptorType', c_uint8),
                ('bEndpointAddress', c_uint8),
                ('bmAttributes', c_uint8),
                ('wMaxPacketSize', c_uint16),
                ('bInterval', c_uint8),
                ('bRefresh', c_uint8),
                ('bSynchAddress', c_uint8),
                ('extra', POINTER(c_uint8)),
                ('extralen', c_int)]

class _usb_interface_descriptor(Structure, _PackPolicy):
    _fields_ = [('bLength', c_uint8),
                ('bDescriptorType', c_uint8),
                ('bInterfaceNumber', c_uint8),
                ('bAlternateSetting', c_uint8),
                ('bNumEndpoints', c_uint8),
                ('bInterfaceClass', c_uint8),
                ('bInterfaceSubClass', c_uint8),
                ('bInterfaceProtocol', c_uint8),
                ('iInterface', c_uint8),
                ('endpoint', POINTER(_usb_endpoint_descriptor)),
                ('extra', POINTER(c_uint8)),
                ('extralen', c_int)]

class _usb_interface(Structure, _PackPolicy):
    _fields_ = [('altsetting', POINTER(_usb_interface_descriptor)),
                ('num_altsetting', c_int)]

class _usb_config_descriptor(Structure, _PackPolicy):
    _fields_ = [('bLength', c_uint8),
                ('bDescriptorType', c_uint8),
                ('wTotalLength', c_uint16),
                ('bNumInterfaces', c_uint8),
                ('bConfigurationValue', c_uint8),
                ('iConfiguration', c_uint8),
                ('bmAttributes', c_uint8),
                ('bMaxPower', c_uint8),
                ('interface', POINTER(_usb_interface)),
                ('extra', POINTER(c_uint8)),
                ('extralen', c_int)]

class _usb_device_descriptor(Structure, _PackPolicy):
    _pack_ = 1
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

class _usb_device(Structure, _PackPolicy):
    pass

class _usb_bus(Structure, _PackPolicy):
    pass

_usb_device._fields_ = [('next', POINTER(_usb_device)),
                        ('prev', POINTER(_usb_device)),
                        ('filename', c_int8 * (_PATH_MAX + 1)),
                        ('bus', POINTER(_usb_bus)),
                        ('descriptor', _usb_device_descriptor),
                        ('config', POINTER(_usb_config_descriptor)),
                        ('dev', c_void_p),
                        ('devnum', c_uint8),
                        ('num_children', c_ubyte),
                        ('children', POINTER(POINTER(_usb_device)))]

_usb_bus._fields_ = [('next', POINTER(_usb_bus)),
                     ('prev', POINTER(_usb_bus)),
                     ('dirname', c_char * (_PATH_MAX + 1)),
                     ('devices', POINTER(_usb_device)),
                     ('location', c_uint32),
                     ('root_dev', POINTER(_usb_device))]

_usb_dev_handle = c_void_p

class _DeviceDescriptor:
    def __init__(self, dev):
        desc = dev.descriptor
        self.bLength = desc.bLength
        self.bDescriptorType = desc.bDescriptorType
        self.bcdUSB = desc.bcdUSB
        self.bDeviceClass = desc.bDeviceClass
        self.bDeviceSubClass = desc.bDeviceSubClass
        self.bDeviceProtocol = desc.bDeviceProtocol
        self.bMaxPacketSize0 = desc.bMaxPacketSize0
        self.idVendor = desc.idVendor
        self.idProduct = desc.idProduct
        self.bcdDevice = desc.bcdDevice
        self.iManufacturer = desc.iManufacturer
        self.iProduct = desc.iProduct
        self.iSerialNumber = desc.iSerialNumber
        self.bNumConfigurations = desc.bNumConfigurations
        self.address = dev.devnum
        self.bus = dev.bus[0].location

        self.port_number = None
        self.port_numbers = None
        self.speed = None

_lib = None

def _load_library(find_library=None):
    return usb.libloader.load_locate_library(
                ('usb-0.1', 'usb', 'libusb0'),
                'cygusb0.dll', 'Libusb 0',
                find_library=find_library
    )

def _setup_prototypes(lib):
    # usb_dev_handle *usb_open(struct usb_device *dev);
    lib.usb_open.argtypes = [POINTER(_usb_device)]
    lib.usb_open.restype = _usb_dev_handle

    # int usb_close(usb_dev_handle *dev);
    lib.usb_close.argtypes = [_usb_dev_handle]

    # int usb_get_string(usb_dev_handle *dev,
    #                    int index,
    #                    int langid,
    #                    char *buf,
    #                    size_t buflen);
    lib.usb_get_string.argtypes = [
            _usb_dev_handle,
            c_int,
            c_int,
            c_char_p,
            c_size_t
        ]

    # int usb_get_string_simple(usb_dev_handle *dev,
    #                           int index,
    #                           char *buf,
    #                           size_t buflen);
    lib.usb_get_string_simple.argtypes = [
            _usb_dev_handle,
            c_int,
            c_char_p,
            c_size_t
        ]

    # int usb_get_descriptor_by_endpoint(usb_dev_handle *udev,
    #                                    int ep,
    #                                    unsigned char type,
    #                                    unsigned char index,
    #                                    void *buf,
    #                                    int size);
    lib.usb_get_descriptor_by_endpoint.argtypes = [
                                _usb_dev_handle,
                                c_int,
                                c_ubyte,
                                c_ubyte,
                                c_void_p,
                                c_int
                            ]

    # int usb_get_descriptor(usb_dev_handle *udev,
    #                        unsigned char type,
    #                        unsigned char index,
    #                        void *buf,
    #                        int size);
    lib.usb_get_descriptor.argtypes = [
                    _usb_dev_handle,
                    c_ubyte,
                    c_ubyte,
                    c_void_p,
                    c_int
                ]

    # int usb_bulk_write(usb_dev_handle *dev,
    #                    int ep,
    #                    const char *bytes,
    #                    int size,
    #                    int timeout);
    lib.usb_bulk_write.argtypes = [
            _usb_dev_handle,
            c_int,
            c_char_p,
            c_int,
            c_int
        ]

    # int usb_bulk_read(usb_dev_handle *dev,
    #                   int ep,
    #                   char *bytes,
    #                   int size,
    #                   int timeout);
    lib.usb_bulk_read.argtypes = [
            _usb_dev_handle,
            c_int,
            c_char_p,
            c_int,
            c_int
        ]

    # int usb_interrupt_write(usb_dev_handle *dev,
    #                         int ep,
    #                         const char *bytes,
    #                         int size,
    #                         int timeout);
    lib.usb_interrupt_write.argtypes = [
            _usb_dev_handle,
            c_int,
            c_char_p,
            c_int,
            c_int
        ]

    # int usb_interrupt_read(usb_dev_handle *dev,
    #                        int ep,
    #                        char *bytes,
    #                        int size,
    #                        int timeout);
    lib.usb_interrupt_read.argtypes = [
            _usb_dev_handle,
            c_int,
            c_char_p,
            c_int,
            c_int
        ]

    # int usb_control_msg(usb_dev_handle *dev,
    #                     int requesttype,
    #                     int request,
    #                     int value,
    #                     int index,
    #                     char *bytes,
    #                     int size,
    #                     int timeout);
    lib.usb_control_msg.argtypes = [
            _usb_dev_handle,
            c_int,
            c_int,
            c_int,
            c_int,
            c_char_p,
            c_int,
            c_int
        ]

    # int usb_set_configuration(usb_dev_handle *dev, int configuration);
    lib.usb_set_configuration.argtypes = [_usb_dev_handle, c_int]

    # int usb_claim_interface(usb_dev_handle *dev, int interface);
    lib.usb_claim_interface.argtypes = [_usb_dev_handle, c_int]

    # int usb_release_interface(usb_dev_handle *dev, int interface);
    lib.usb_release_interface.argtypes = [_usb_dev_handle, c_int]

    # int usb_set_altinterface(usb_dev_handle *dev, int alternate);
    lib.usb_set_altinterface.argtypes = [_usb_dev_handle, c_int]

    # int usb_resetep(usb_dev_handle *dev, unsigned int ep);
    lib.usb_resetep.argtypes = [_usb_dev_handle, c_int]

    # int usb_clear_halt(usb_dev_handle *dev, unsigned int ep);
    lib.usb_clear_halt.argtypes = [_usb_dev_handle, c_int]

    # int usb_reset(usb_dev_handle *dev);
    lib.usb_reset.argtypes = [_usb_dev_handle]

    # char *usb_strerror(void);
    lib.usb_strerror.argtypes = []
    lib.usb_strerror.restype = c_char_p

    # void usb_set_debug(int level);
    lib.usb_set_debug.argtypes = [c_int]

    # struct usb_device *usb_device(usb_dev_handle *dev);
    lib.usb_device.argtypes = [_usb_dev_handle]
    lib.usb_device.restype = POINTER(_usb_device)

    # struct usb_bus *usb_get_busses(void);
    lib.usb_get_busses.restype = POINTER(_usb_bus)

    # linux only

    # int usb_get_driver_np(usb_dev_handle *dev,
    #                       int interface,
    #                       char *name,
    #                       unsigned int namelen);
    if hasattr(lib, 'usb_get_driver_np'):
        lib.usb_get_driver_np.argtypes = \
            [_usb_dev_handle, c_int, c_char_p, c_uint]

    # int usb_detach_kernel_driver_np(usb_dev_handle *dev, int interface);
    if hasattr(lib, 'usb_detach_kernel_driver_np'):
        lib.usb_detach_kernel_driver_np.argtypes = [_usb_dev_handle, c_int]

    # libusb-win32 only

    # int usb_isochronous_setup_async(usb_dev_handle *dev,
    #                                 void **context,
    #                                 unsigned char ep,
    #                                 int pktsize)
    if hasattr(lib, 'usb_isochronous_setup_async'):
        lib.usb_isochronous_setup_async.argtypes = \
            [_usb_dev_handle, POINTER(c_void_p), c_uint8, c_int]

    # int usb_bulk_setup_async(usb_dev_handle *dev,
    #                          void **context,
    #                          unsigned char ep)
    if hasattr(lib, 'usb_bulk_setup_async'):
        lib.usb_bulk_setup_async.argtypes = \
            [_usb_dev_handle, POINTER(c_void_p), c_uint8]

    # int usb_interrupt_setup_async(usb_dev_handle *dev,
    #                               void **context,
    #                               unsigned char ep)
    if hasattr(lib, 'usb_interrupt_setup_async'):
        lib.usb_interrupt_setup_async.argtypes = \
            [_usb_dev_handle, POINTER(c_void_p), c_uint8]

    # int usb_submit_async(void *context, char *bytes, int size)
    if hasattr(lib, 'usb_submit_async'):
        lib.usb_submit_async.argtypes = [c_void_p, c_char_p, c_int]

    # int usb_reap_async(void *context, int timeout)
    if hasattr(lib, 'usb_reap_async'):
        lib.usb_reap_async.argtypes = [c_void_p, c_int]

    # int usb_reap_async_nocancel(void *context, int timeout)
    if hasattr(lib, 'usb_reap_async_nocancel'):
        lib.usb_reap_async_nocancel.argtypes = [c_void_p, c_int]

    # int usb_cancel_async(void *context)
    if hasattr(lib, 'usb_cancel_async'):
        lib.usb_cancel_async.argtypes = [c_void_p]

    # int usb_free_async(void **context)
    if hasattr(lib, 'usb_free_async'):
        lib.usb_free_async.argtypes = [POINTER(c_void_p)]

def _check(ret):
    if ret is None:
        errmsg = _lib.usb_strerror()
    else:
        if hasattr(ret, 'value'):
            ret = ret.value

        if ret < 0:
            errmsg = _lib.usb_strerror()
            # No error means that we need to get the error
            # message from the return code
            # Thanks to Nicholas Wheeler to point out the problem...
            # Also see issue #2860940
            if errmsg.lower() == 'no error':
                errmsg = os.strerror(-ret)
        else:
            return ret

    if ret is not None and -ret == errno.ETIMEDOUT:
        raise USBTimeoutError(errmsg, ret, -ret)
    raise USBError(errmsg, ret)

def _has_iso_transfer():
    return hasattr(_lib, 'usb_isochronous_setup_async')

# implementation of libusb 0.1.x backend
class _LibUSB(usb.backend.IBackend):
    @methodtrace(_logger)
    def enumerate_devices(self):
        _check(_lib.usb_find_busses())
        _check(_lib.usb_find_devices())
        bus = _lib.usb_get_busses()
        while bool(bus):
            dev = bus[0].devices
            while bool(dev):
                yield dev[0]
                dev = dev[0].next
            bus = bus[0].next

    @methodtrace(_logger)
    def get_device_descriptor(self, dev):
        return _DeviceDescriptor(dev)

    @methodtrace(_logger)
    def get_configuration_descriptor(self, dev, config):
        if config >= dev.descriptor.bNumConfigurations:
            raise IndexError('Invalid configuration index ' + str(config))
        config_desc = dev.config[config]
        config_desc.extra_descriptors = config_desc.extra[:config_desc.extralen]
        return config_desc

    @methodtrace(_logger)
    def get_interface_descriptor(self, dev, intf, alt, config):
        cfgdesc = self.get_configuration_descriptor(dev, config)
        if intf >= cfgdesc.bNumInterfaces:
            raise IndexError('Invalid interface index ' + str(intf))
        interface = cfgdesc.interface[intf]
        if alt >= interface.num_altsetting:
            raise IndexError('Invalid alternate setting index ' + str(alt))
        intf_desc = interface.altsetting[alt]
        intf_desc.extra_descriptors = intf_desc.extra[:intf_desc.extralen]
        return intf_desc

    @methodtrace(_logger)
    def get_endpoint_descriptor(self, dev, ep, intf, alt, config):
        interface = self.get_interface_descriptor(dev, intf, alt, config)
        if ep >= interface.bNumEndpoints:
            raise IndexError('Invalid endpoint index ' + str(ep))
        ep_desc = interface.endpoint[ep]
        ep_desc.extra_descriptors = ep_desc.extra[:ep_desc.extralen]
        return ep_desc

    @methodtrace(_logger)
    def open_device(self, dev):
        return _check(_lib.usb_open(dev))

    @methodtrace(_logger)
    def close_device(self, dev_handle):
        _check(_lib.usb_close(dev_handle))

    @methodtrace(_logger)
    def set_configuration(self, dev_handle, config_value):
        _check(_lib.usb_set_configuration(dev_handle, config_value))

    @methodtrace(_logger)
    def get_configuration(self, dev_handle):
        bmRequestType = usb.util.build_request_type(
                                usb.util.CTRL_IN,
                                usb.util.CTRL_TYPE_STANDARD,
                                usb.util.CTRL_RECIPIENT_DEVICE
                            )
        buff = usb.util.create_buffer(1)
        ret = self.ctrl_transfer(
                dev_handle,
                bmRequestType,
                0x08,
                0,
                0,
                buff,
                100)

        assert ret == 1
        return buff[0]

    @methodtrace(_logger)
    def set_interface_altsetting(self, dev_handle, intf, altsetting):
        _check(_lib.usb_set_altinterface(dev_handle, altsetting))

    @methodtrace(_logger)
    def claim_interface(self, dev_handle, intf):
        _check(_lib.usb_claim_interface(dev_handle, intf))

    @methodtrace(_logger)
    def release_interface(self, dev_handle, intf):
        _check(_lib.usb_release_interface(dev_handle, intf))

    @methodtrace(_logger)
    def bulk_write(self, dev_handle, ep, intf, data, timeout):
        return self.__write(_lib.usb_bulk_write,
                            dev_handle,
                            ep,
                            intf,
                            data, timeout)

    @methodtrace(_logger)
    def bulk_read(self, dev_handle, ep, intf, buff, timeout):
        return self.__read(_lib.usb_bulk_read,
                           dev_handle,
                           ep,
                           intf,
                           buff,
                           timeout)

    @methodtrace(_logger)
    def intr_write(self, dev_handle, ep, intf, data, timeout):
        return self.__write(_lib.usb_interrupt_write,
                            dev_handle,
                            ep,
                            intf,
                            data,
                            timeout)

    @methodtrace(_logger)
    def intr_read(self, dev_handle, ep, intf, buff, timeout):
        return self.__read(_lib.usb_interrupt_read,
                           dev_handle,
                           ep,
                           intf,
                           buff,
                           timeout)

    @methodtrace(_logger)
    def iso_write(self, dev_handle, ep, intf, data, timeout):
        if not _has_iso_transfer():
            return usb.backend.IBackend.iso_write(self, dev_handle, ep, intf, data, timeout)
        return self.__iso_transfer(dev_handle, ep, intf, data, timeout)

    @methodtrace(_logger)
    def iso_read(self, dev_handle, ep, intf, buff, timeout):
        if not _has_iso_transfer():
            return usb.backend.IBackend.iso_read(self, dev_handle, ep, intf, buff, timeout)
        return self.__iso_transfer(dev_handle, ep, intf, buff, timeout)

    @methodtrace(_logger)
    def ctrl_transfer(self,
                      dev_handle,
                      bmRequestType,
                      bRequest,
                      wValue,
                      wIndex,
                      data,
                      timeout):
        address, length = data.buffer_info()
        length *= data.itemsize
        return _check(_lib.usb_control_msg(
                            dev_handle,
                            bmRequestType,
                            bRequest,
                            wValue,
                            wIndex,
                            cast(address, c_char_p),
                            length,
                            timeout
                        ))

    @methodtrace(_logger)
    def clear_halt(self, dev_handle, ep):
        _check(_lib.usb_clear_halt(dev_handle, ep))

    @methodtrace(_logger)
    def reset_device(self, dev_handle):
        _check(_lib.usb_reset(dev_handle))

    @methodtrace(_logger)
    def is_kernel_driver_active(self, dev_handle, intf):
        if sys.platform == 'linux':
            # based on the implementation of libusb_kernel_driver_active()
            # (see op_kernel_driver_active() in libusb/os/linux_usbfs.c)
            # and the fact that usb_get_driver_np() is a wrapper for
            # IOCTL_USBFS_GETDRIVER
            try:
                driver_name = self.__get_driver_name(dev_handle, intf)
                # 'usbfs' is not considered a [foreign] kernel driver because
                # it is what we use to access the device from userspace
                return driver_name != b'usbfs'
            except USBError as err:
                # ENODATA means that no kernel driver is attached
                if err.backend_error_code == -errno.ENODATA:
                    return False
                raise
        elif sys.platform == 'darwin':
            # on mac os/darwin we assume all users are running libusb-compat,
            # which, in turn, uses libusb_kernel_driver_active()
            try:
                driver_name = self.__get_driver_name(dev_handle, intf)
                return True
            except USBError as err:
                # ENODATA means that no kernel driver is attached
                if err.backend_error_code == -errno.ENODATA:
                    return False
                raise
        elif sys.platform.startswith('freebsd') or sys.platform.startswith('dragonfly'):
            # this is similar to the Linux implementation, but the generic
            # driver is called 'ugen' and usb_get_driver_np() simply returns an
            # empty string is no driver is attached (see comments on PR #366)
            driver_name = self.__get_driver_name(dev_handle, intf)
            # 'ugen' is not considered a [foreign] kernel driver because
            # it is what we use to access the device from userspace
            return driver_name != b'ugen'
        else:
            raise NotImplementedError(self.is_kernel_driver_active.__name__)

    @methodtrace(_logger)
    def detach_kernel_driver(self, dev_handle, intf):
        if not hasattr(_lib, 'usb_detach_kernel_driver_np'):
            raise NotImplementedError(self.detach_kernel_driver.__name__)
        _check(_lib.usb_detach_kernel_driver_np(dev_handle, intf))

    def __get_driver_name(self, dev_handle, intf):
        if not hasattr(_lib, 'usb_get_driver_np'):
            raise NotImplementedError('usb_get_driver_np')
        buf = usb.util.create_buffer(_USBFS_MAXDRIVERNAME + 1)
        name, length = buf.buffer_info()
        length *= buf.itemsize
        _check(_lib.usb_get_driver_np(
                    dev_handle,
                    intf,
                    cast(name, c_char_p),
                    length))
        return cast(name, c_char_p).value

    def __write(self, fn, dev_handle, ep, intf, data, timeout):
        address, length = data.buffer_info()
        length *= data.itemsize
        return int(_check(fn(
                        dev_handle,
                        ep,
                        cast(address, c_char_p),
                        length,
                        timeout
                    )))

    def __read(self, fn, dev_handle, ep, intf, buff, timeout):
        address, length = buff.buffer_info()
        length *= buff.itemsize
        ret = int(_check(fn(
                    dev_handle,
                    ep,
                    cast(address, c_char_p),
                    length,
                    timeout
                )))
        return ret

    def __iso_transfer(self, dev_handle, ep, intf, data, timeout):
        context = c_void_p()
        buff, length = data.buffer_info()
        length *= data.itemsize

        _check(_lib.usb_isochronous_setup_async(
            dev_handle,
            byref(context),
            ep,
            0))

        transmitted = 0

        try:
            while transmitted < length:
                _check(_lib.usb_submit_async(
                    context,
                    cast(buff + transmitted, c_char_p),
                    length - transmitted))

                ret = _check(_lib.usb_reap_async(context, timeout))
                if not ret:
                    return transmitted

                transmitted += ret
        except:
            if not transmitted:
                raise
        finally:
            _check(_lib.usb_free_async(byref(context)))

        return transmitted

def get_backend(find_library=None):
    global _lib
    try:
        if _lib is None:
            _lib = _load_library(find_library)
            _setup_prototypes(_lib)
            _lib.usb_init()
        return _LibUSB()
    except usb.libloader.LibraryException:
        # exception already logged (if any)
        _logger.error('Error loading libusb 0.1 backend', exc_info=False)
        return None
    except Exception:
        _logger.error('Error loading libusb 0.1 backend', exc_info=True)
        return None
