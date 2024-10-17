# Copyright (C) 2009-2014 Wander Lairson Costa
#
# The following terms apply to all files associated
# with the software unless explicitly disclaimed in individual files.
#
# The authors hereby grant permission to use, copy, modify, distribute,
# and license this software and its documentation for any purpose, provided
# that existing copyright notices are retained in all copies and that this
# notice is included verbatim in any distributions. No written agreement,
# license, or royalty fee is required for any of the authorized uses.
# Modifications to this software may be copyrighted by their authors
# and need not follow the licensing terms described here, provided that
# the new terms are clearly indicated on the first page of each file where
# they apply.
#
# IN NO EVENT SHALL THE AUTHORS OR DISTRIBUTORS BE LIABLE TO ANY PARTY
# FOR DIRECT, INDIRECT, SPECIAL, INCIDENTAL, OR CONSEQUENTIAL DAMAGES
# ARISING OUT OF THE USE OF THIS SOFTWARE, ITS DOCUMENTATION, OR ANY
# DERIVATIVES THEREOF, EVEN IF THE AUTHORS HAVE BEEN ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.
#
# THE AUTHORS AND DISTRIBUTORS SPECIFICALLY DISCLAIM ANY WARRANTIES,
# INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE, AND NON-INFRINGEMENT.  THIS SOFTWARE
# IS PROVIDED ON AN "AS IS" BASIS, AND THE AUTHORS AND DISTRIBUTORS HAVE
# NO OBLIGATION TO PROVIDE MAINTENANCE, SUPPORT, UPDATES, ENHANCEMENTS, OR
# MODIFICATIONS.

r"""usb.core - Core USB features.

This module exports:

Device - a class representing a USB device.
Configuration - a class representing a configuration descriptor.
Interface - a class representing an interface descriptor.
Endpoint - a class representing an endpoint descriptor.
find() - a function to find USB devices.
show_devices() - a function to show the devices present.
"""

__author__ = 'Wander Lairson Costa'

__all__ = [ 'Device', 'Configuration', 'Interface', 'Endpoint', 'find',
            'show_devices' ]

import usb.util as util
import copy
import operator
import usb._interop as _interop
import usb._objfinalizer as _objfinalizer
import usb._lookup as _lu
import logging
import array
import threading
import functools

_logger = logging.getLogger('usb.core')

_DEFAULT_TIMEOUT = 1000

def _set_attr(input, output, fields):
    for f in fields:
       setattr(output, f, getattr(input, f))

def _try_get_string(dev, index, langid = None, default_str_i0 = "",
        default_access_error = "Error Accessing String"):
    """ try to get a string, but return a string no matter what
    """
    if index == 0 :
        string = default_str_i0
    else:
        try:
            if langid is None:
                string = util.get_string(dev, index)
            else:
                string = util.get_string(dev, index, langid)
        except :
            string = default_access_error
    return string

def _try_lookup(table, value, default = ""):
    """ try to get a string from the lookup table, return "" instead of key
    error
    """
    try:
        string = table[ value ]
    except KeyError:
        string = default
    return string

class _DescriptorInfo(str):
    """ this class is used so that when a descriptor is shown on the
    terminal it is propely formatted """
    def __repr__(self):
        return self

def synchronized(f):
    @functools.wraps(f)
    def wrapper(self, *args, **kwargs):
        try:
            self.lock.acquire()
            return f(self, *args, **kwargs)
        finally:
            self.lock.release()
    return wrapper

class _ResourceManager(object):
    def __init__(self, dev, backend):
        self.backend = backend
        self._active_cfg_index = None
        self.dev = dev
        self.handle = None
        self._claimed_intf = _interop._set()
        self._ep_info = {}
        self.lock = threading.RLock()

    @synchronized
    def managed_open(self):
        if self.handle is None:
            self.handle = self.backend.open_device(self.dev)
        return self.handle

    @synchronized
    def managed_close(self):
        if self.handle is not None:
            self.backend.close_device(self.handle)
            self.handle = None

    @synchronized
    def managed_set_configuration(self, device, config):
        if config is None:
            cfg = device[0]
        elif isinstance(config, Configuration):
            cfg = config
        elif config == 0: # unconfigured state
            class MockConfiguration(object):
                def __init__(self):
                    self.index = None
                    self.bConfigurationValue = 0
            cfg = MockConfiguration()
        else:
            cfg = util.find_descriptor(device, bConfigurationValue=config)

        if cfg is None:
            raise ValueError("Invalid configuration " + str(config))

        self.managed_open()
        self.backend.set_configuration(self.handle, cfg.bConfigurationValue)

        # cache the index instead of the object to avoid cyclic references
        # of the device and Configuration (Device tracks the _ResourceManager,
        # which tracks the Configuration, which tracks the Device)
        self._active_cfg_index = cfg.index

        self._ep_info.clear()

    @synchronized
    def managed_claim_interface(self, device, intf):
        self.managed_open()

        if isinstance(intf, Interface):
            i = intf.bInterfaceNumber
        else:
            i = intf

        if i not in self._claimed_intf:
            self.backend.claim_interface(self.handle, i)
            self._claimed_intf.add(i)

    @synchronized
    def managed_release_interface(self, device, intf):
        if intf is None:
            cfg = self.get_active_configuration(device)
            i = cfg[(0,0)].bInterfaceNumber
        elif isinstance(intf, Interface):
            i = intf.bInterfaceNumber
        else:
            i = intf

        if i in self._claimed_intf:
            try:
                self.backend.release_interface(self.handle, i)
            finally:
                self._claimed_intf.remove(i)

    @synchronized
    def managed_set_interface(self, device, intf, alt):
        if isinstance(intf, Interface):
            i = intf
        else:
            cfg = self.get_active_configuration(device)
            if intf is None:
                intf = cfg[(0,0)].bInterfaceNumber
            if alt is not None:
                i = util.find_descriptor(cfg, bInterfaceNumber=intf, bAlternateSetting=alt)
            else:
                i = util.find_descriptor(cfg, bInterfaceNumber=intf)

        self.managed_claim_interface(device, i)

        if alt is None:
            alt = i.bAlternateSetting

        self.backend.set_interface_altsetting(self.handle, i.bInterfaceNumber, alt)

    @synchronized
    def setup_request(self, device, endpoint):
        # we need the endpoint address, but the "endpoint" parameter
        # can be either the a Endpoint object or the endpoint address itself
        if isinstance(endpoint, Endpoint):
            endpoint_address = endpoint.bEndpointAddress
        else:
            endpoint_address = endpoint

        intf, ep = self.get_interface_and_endpoint(device, endpoint_address)
        self.managed_claim_interface(device, intf)
        return (intf, ep)

    # Find the interface and endpoint objects which endpoint address belongs to
    @synchronized
    def get_interface_and_endpoint(self, device, endpoint_address):
        try:
            return self._ep_info[endpoint_address]
        except KeyError:
            for intf in self.get_active_configuration(device):
                ep = util.find_descriptor(intf, bEndpointAddress=endpoint_address)
                if ep is not None:
                    self._ep_info[endpoint_address] = (intf, ep)
                    return intf, ep

            raise ValueError('Invalid endpoint address ' + hex(endpoint_address))

    @synchronized
    def get_active_configuration(self, device):
        if self._active_cfg_index is None:
            self.managed_open()
            cfg = util.find_descriptor(
                    device,
                    bConfigurationValue=self.backend.get_configuration(self.handle)
                )
            if cfg is None:
                raise USBError('Configuration not set')
            self._active_cfg_index = cfg.index
            return cfg
        return device[self._active_cfg_index]

    @synchronized
    def release_all_interfaces(self, device):
        claimed = copy.copy(self._claimed_intf)
        for i in claimed:
            try:
                self.managed_release_interface(device, i)
            except USBError:
                # Ignore errors when releasing the interfaces
                # When the device is disconnected, the call may fail
                pass

    @synchronized
    def dispose(self, device, close_handle = True):
        self.release_all_interfaces(device)
        if close_handle:
            self.managed_close()
        self._ep_info.clear()
        self._active_cfg_index = None


class USBError(IOError):
    r"""Exception class for USB errors.

    Backends must raise this exception when USB related errors occur.  The
    backend specific error code is available through the 'backend_error_code'
    member variable.
    """

    def __init__(self, strerror, error_code = None, errno = None):
        r"""Initialize the object.

        This initializes the USBError object. The strerror and errno are passed
        to the parent object. The error_code parameter is attributed to the
        backend_error_code member variable.
        """

        IOError.__init__(self, errno, strerror)
        self.backend_error_code = error_code

class NoBackendError(ValueError):
    r"Exception class when a valid backend is not found."
    pass

class Endpoint(object):
    r"""Represent an endpoint object.

    This class contains all fields of the Endpoint Descriptor according to the
    USB Specification. You can access them as class properties. For example, to
    access the field bEndpointAddress of the endpoint descriptor, you can do so:

    >>> import usb.core
    >>> dev = usb.core.find()
    >>> for cfg in dev:
    >>>     for i in cfg:
    >>>         for e in i:
    >>>             print e.bEndpointAddress
    """

    def __init__(self, device, endpoint, interface = 0,
                    alternate_setting = 0, configuration = 0):
        r"""Initialize the Endpoint object.

        The device parameter is the device object returned by the find()
        function. endpoint is the endpoint logical index (not the endpoint
        address). The configuration parameter is the logical index of the
        configuration (not the bConfigurationValue field). The interface
        parameter is the interface logical index (not the bInterfaceNumber
        field) and alternate_setting is the alternate setting logical index
        (not the bAlternateSetting value). An interface may have only one
        alternate setting. In this case, the alternate_setting parameter
        should be zero. By "logical index" we mean the relative order of the
        configurations returned by the peripheral as a result of GET_DESCRIPTOR
        request.
        """
        self.device = device
        self.index = endpoint

        backend = device._ctx.backend

        desc = backend.get_endpoint_descriptor(
                    device._ctx.dev,
                    endpoint,
                    interface,
                    alternate_setting,
                    configuration
                )

        _set_attr(
                desc,
                self,
                (
                    'bLength',
                    'bDescriptorType',
                    'bEndpointAddress',
                    'bmAttributes',
                    'wMaxPacketSize',
                    'bInterval',
                    'bRefresh',
                    'bSynchAddress',
                    'extra_descriptors'
                )
            )

    def __repr__(self):
        return "<" + self._str() + ">"

    def __str__(self):
        headstr = "      " + self._str() + " "

        if util.endpoint_direction(self.bEndpointAddress) == util.ENDPOINT_IN:
            direction = "IN"
        else:
            direction = "OUT"

        return "%s%s\n" % (headstr, "=" * (60 - len(headstr))) + \
        "       %-17s:%#7x (7 bytes)\n" % (
                "bLength", self.bLength) + \
        "       %-17s:%#7x %s\n" % (
                "bDescriptorType", self.bDescriptorType,
                _try_lookup(_lu.descriptors, self.bDescriptorType)) + \
        "       %-17s:%#7x %s\n" % (
                "bEndpointAddress", self.bEndpointAddress, direction) + \
        "       %-17s:%#7x %s\n" % (
                "bmAttributes", self.bmAttributes,
                _lu.ep_attributes[(self.bmAttributes & 0x3)]) + \
        "       %-17s:%#7x (%d bytes)\n" % (
                "wMaxPacketSize", self.wMaxPacketSize, self.wMaxPacketSize) + \
        "       %-17s:%#7x" % ("bInterval", self.bInterval)

    def write(self, data, timeout = None):
        r"""Write data to the endpoint.

        The parameter data contains the data to be sent to the endpoint and
        timeout is the time limit of the operation. The transfer type and
        endpoint address are automatically inferred.

        The method returns the number of bytes written.

        For details, see the Device.write() method.
        """
        return self.device.write(self, data, timeout)

    def read(self, size_or_buffer, timeout = None):
        r"""Read data from the endpoint.

        The parameter size_or_buffer is either the number of bytes to
        read or an array object where the data will be put in and timeout is the
        time limit of the operation. The transfer type and endpoint address
        are automatically inferred.

        The method returns either an array object or the number of bytes
        actually read.

        For details, see the Device.read() method.
        """
        return self.device.read(self, size_or_buffer, timeout)

    def clear_halt(self):
        r"""Clear the halt/status condition of the endpoint."""
        self.device.clear_halt(self.bEndpointAddress)

    def _str(self):
        if util.endpoint_direction(self.bEndpointAddress) == util.ENDPOINT_IN:
            direction = "IN"
        else:
            direction = "OUT"

        return (
            "ENDPOINT 0x%X: %s %s" % (self.bEndpointAddress,
            _lu.ep_attributes[(self.bmAttributes & 0x3)],
            direction))

class Interface(object):
    r"""Represent an interface object.

    This class contains all fields of the Interface Descriptor
    according to the USB Specification. You may access them as class
    properties. For example, to access the field bInterfaceNumber
    of the interface descriptor, you can do so:

    >>> import usb.core
    >>> dev = usb.core.find()
    >>> for cfg in dev:
    >>>     for i in cfg:
    >>>         print i.bInterfaceNumber
    """

    def __init__(self, device, interface = 0,
            alternate_setting = 0, configuration = 0):
        r"""Initialize the interface object.

        The device parameter is the device object returned by the find()
        function. The configuration parameter is the logical index of the
        configuration (not the bConfigurationValue field). The interface
        parameter is the interface logical index (not the bInterfaceNumber
        field) and alternate_setting is the alternate setting logical index
        (not the bAlternateSetting value). An interface may have only one
        alternate setting. In this case, the alternate_setting parameter
        should be zero.  By "logical index" we mean the relative order of
        the configurations returned by the peripheral as a result of
        GET_DESCRIPTOR request.
        """
        self.device = device
        self.alternate_index = alternate_setting
        self.index = interface
        self.configuration = configuration

        backend = device._ctx.backend

        desc = backend.get_interface_descriptor(
                    self.device._ctx.dev,
                    interface,
                    alternate_setting,
                    configuration
                )

        _set_attr(
                desc,
                self,
                (
                    'bLength',
                    'bDescriptorType',
                    'bInterfaceNumber',
                    'bAlternateSetting',
                    'bNumEndpoints',
                    'bInterfaceClass',
                    'bInterfaceSubClass',
                    'bInterfaceProtocol',
                    'iInterface',
                    'extra_descriptors'
                )
            )

    def __repr__(self):
        return "<" + self._str() + ">"

    def __str__(self):
        """Show all information for the interface."""

        string = self._get_full_descriptor_str()
        for endpoint in self:
            string += "\n" + str(endpoint)
        return string

    def endpoints(self):
        r"""Return a tuple of the interface endpoints."""
        return tuple(self)

    def set_altsetting(self):
        r"""Set the interface alternate setting."""
        self.device.set_interface_altsetting(
            self.bInterfaceNumber,
            self.bAlternateSetting)

    def __iter__(self):
        r"""Iterate over all endpoints of the interface."""
        for i in range(self.bNumEndpoints):
            yield Endpoint(
                    self.device,
                    i,
                    self.index,
                    self.alternate_index,
                    self.configuration)

    def __getitem__(self, index):
        r"""Return the Endpoint object in the given position."""
        return Endpoint(
                self.device,
                index,
                self.index,
                self.alternate_index,
                self.configuration)

    def _str(self):
        if self.bAlternateSetting:
            alt_setting = ", %d" % self.bAlternateSetting
        else:
            alt_setting = ""

        return "INTERFACE %d%s: %s" % (self.bInterfaceNumber, alt_setting,
            _try_lookup(_lu.interface_classes, self.bInterfaceClass,
                default = "Unknown Class"))

    def _get_full_descriptor_str(self):
        headstr = "    " + self._str() + " "
        return "%s%s\n" % (headstr, "=" * (60 - len(headstr))) + \
        "     %-19s:%#7x (9 bytes)\n" % (
            "bLength", self.bLength) + \
        "     %-19s:%#7x %s\n" % (
            "bDescriptorType", self.bDescriptorType,
            _try_lookup(_lu.descriptors, self.bDescriptorType)) + \
        "     %-19s:%#7x\n" % (
            "bInterfaceNumber", self.bInterfaceNumber) + \
        "     %-19s:%#7x\n" % (
            "bAlternateSetting", self.bAlternateSetting) + \
        "     %-19s:%#7x\n" % (
            "bNumEndpoints", self.bNumEndpoints) + \
        "     %-19s:%#7x %s\n" % (
            "bInterfaceClass", self.bInterfaceClass,
            _try_lookup(_lu.interface_classes, self.bInterfaceClass)) + \
        "     %-19s:%#7x\n" % (
            "bInterfaceSubClass", self.bInterfaceSubClass) + \
        "     %-19s:%#7x\n" % (
            "bInterfaceProtocol", self.bInterfaceProtocol) + \
        "     %-19s:%#7x %s" % (
            "iInterface", self.iInterface,
            _try_get_string(self.device, self.iInterface))


class Configuration(object):
    r"""Represent a configuration object.

    This class contains all fields of the Configuration Descriptor according to
    the USB Specification. You may access them as class properties.  For
    example, to access the field bConfigurationValue of the configuration
    descriptor, you can do so:

    >>> import usb.core
    >>> dev = usb.core.find()
    >>> for cfg in dev:
    >>>     print cfg.bConfigurationValue
    """

    def __init__(self, device, configuration = 0):
        r"""Initialize the configuration object.

        The device parameter is the device object returned by the find()
        function. The configuration parameter is the logical index of the
        configuration (not the bConfigurationValue field). By "logical index"
        we mean the relative order of the configurations returned by the
        peripheral as a result of GET_DESCRIPTOR request.
        """
        self.device = device
        self.index = configuration

        backend = device._ctx.backend

        desc = backend.get_configuration_descriptor(
                self.device._ctx.dev,
                configuration
            )

        _set_attr(
                desc,
                self,
                (
                    'bLength',
                    'bDescriptorType',
                    'wTotalLength',
                    'bNumInterfaces',
                    'bConfigurationValue',
                    'iConfiguration',
                    'bmAttributes',
                    'bMaxPower',
                    'extra_descriptors'
                )
            )

    def __repr__(self):
        return "<" + self._str() + ">"

    def __str__(self):
        string = self._get_full_descriptor_str()
        for interface in self:
            string += "\n%s" % str(interface)
        return string

    def interfaces(self):
        r"""Return a tuple of the configuration interfaces."""
        return tuple(self)

    def set(self):
        r"""Set this configuration as the active one."""
        self.device.set_configuration(self.bConfigurationValue)

    def __iter__(self):
        r"""Iterate over all interfaces of the configuration."""
        for i in range(self.bNumInterfaces):
            alt = 0
            try:
                while True:
                    yield Interface(self.device, i, alt, self.index)
                    alt += 1
            except (USBError, IndexError):
                pass

    def __getitem__(self, index):
        r"""Return the Interface object in the given position.

        index is a tuple of two values with interface index and
        alternate setting index, respectivally. Example:

        >>> interface = config[(0, 0)]
        """
        return Interface(self.device, index[0], index[1], self.index)


    def _str(self):
        return "CONFIGURATION %d: %d mA" % (
            self.bConfigurationValue,
            _lu.MAX_POWER_UNITS_USB2p0 * self.bMaxPower)

    def _get_full_descriptor_str(self):
        headstr = "  " + self._str() + " "
        if self.bmAttributes & (1<<6):
            powered = "Self"
        else:
            powered = "Bus"

        if self.bmAttributes & (1<<5):
            remote_wakeup = ", Remote Wakeup"
        else:
            remote_wakeup = ""

        return "%s%s\n" % (headstr, "=" * (60 - len(headstr))) + \
        "   %-21s:%#7x (9 bytes)\n" % (
            "bLength", self.bLength) + \
        "   %-21s:%#7x %s\n" % (
            "bDescriptorType", self.bDescriptorType,
            _try_lookup(_lu.descriptors, self.bDescriptorType)) + \
        "   %-21s:%#7x (%d bytes)\n" % (
            "wTotalLength", self.wTotalLength, self.wTotalLength) + \
        "   %-21s:%#7x\n" % (
            "bNumInterfaces", self.bNumInterfaces) + \
        "   %-21s:%#7x\n" % (
            "bConfigurationValue", self.bConfigurationValue) + \
        "   %-21s:%#7x %s\n" % (
            "iConfiguration", self.iConfiguration,
            _try_get_string(self.device, self.iConfiguration)) + \
        "   %-21s:%#7x %s Powered%s\n" % (
            "bmAttributes", self.bmAttributes, powered, remote_wakeup
            # bit 7 is high, bit 4..0 are 0
            ) + \
        "   %-21s:%#7x (%d mA)" % (
            "bMaxPower", self.bMaxPower,
            _lu.MAX_POWER_UNITS_USB2p0 * self.bMaxPower)
            # FIXME : add a check for superspeed vs usb 2.0

class Device(_objfinalizer.AutoFinalizedObject):
    r"""Device object.

    This class contains all fields of the Device Descriptor according to the
    USB Specification. You may access them as class properties.  For example,
    to access the field bDescriptorType of the device descriptor, you can
    do so:

    >>> import usb.core
    >>> dev = usb.core.find()
    >>> dev.bDescriptorType

    Additionally, the class provides methods to communicate with the hardware.
    Typically, an application will first call the set_configuration() method to
    put the device in a known configured state, optionally call the
    set_interface_altsetting() to select the alternate setting (if there is
    more than one) of the interface used, and call the write() and read()
    methods to send and receive data, respectively.

    When working in a new hardware, the first try could be like this:

    >>> import usb.core
    >>> dev = usb.core.find(idVendor=myVendorId, idProduct=myProductId)
    >>> dev.set_configuration()
    >>> dev.write(1, 'test')

    This sample finds the device of interest (myVendorId and myProductId should
    be replaced by the corresponding values of your device), then configures
    the device (by default, the configuration value is 1, which is a typical
    value for most devices) and then writes some data to the endpoint 0x01.

    Timeout values for the write, read and ctrl_transfer methods are specified
    in miliseconds. If the parameter is omitted, Device.default_timeout value
    will be used instead. This property can be set by the user at anytime.
    """

    def __repr__(self):
        return "<" + self._str() + ">"

    def __str__(self):
        string = self._get_full_descriptor_str()
        try:
            for configuration in self:
                string += "\n%s" % str(configuration)
        except USBError:
            try:
                configuration = self.get_active_configuration()
                string += "\n%s" % (configuration.info)
            except USBError:
                string += " USBError Accessing Configurations"
        return string

    def configurations(self):
        r"""Return a tuple of the device configurations."""
        return tuple(self)

    def __init__(self, dev, backend):
        r"""Initialize the Device object.

        Library users should normally get a Device instance through
        the find function. The dev parameter is the identification
        of a device to the backend and its meaning is opaque outside
        of it. The backend parameter is a instance of a backend
        object.
        """
        self._ctx = _ResourceManager(dev, backend)
        self.__default_timeout = _DEFAULT_TIMEOUT
        self._serial_number, self._product, self._manufacturer = None, None, None
        self._langids = None

        desc = backend.get_device_descriptor(dev)

        _set_attr(
                desc,
                self,
                (
                    'bLength',
                    'bDescriptorType',
                    'bcdUSB',
                    'bDeviceClass',
                    'bDeviceSubClass',
                    'bDeviceProtocol',
                    'bMaxPacketSize0',
                    'idVendor',
                    'idProduct',
                    'bcdDevice',
                    'iManufacturer',
                    'iProduct',
                    'iSerialNumber',
                    'bNumConfigurations',
                    'address',
                    'bus',
                    'port_number',
                    'port_numbers',
                    'speed',
                )
            )

        if desc.bus is not None:
            self.bus = int(desc.bus)
        else:
            self.bus = None

        if desc.address is not None:
            self.address = int(desc.address)
        else:
            self.address = None

        if desc.port_number is not None:
            self.port_number = int(desc.port_number)
        else:
            self.port_number = None

        if desc.speed is not None:
            self.speed = int(desc.speed)
        else:
            self.speed = None

    @property
    def langids(self):
        """ Return the USB device's supported language ID codes.

        These are 16-bit codes familiar to Windows developers, where for
        example instead of en-US you say 0x0409. USB_LANGIDS.pdf on the usb.org
        developer site for more info. String requests using a LANGID not
        in this array should not be sent to the device.

        This property will cause some USB traffic the first time it is accessed
        and cache the resulting value for future use.
        """
        if self._langids is None:
            try:
                self._langids = util.get_langids(self)
            except USBError:
                self._langids = ()
        return self._langids

    @property
    def serial_number(self):
        """ Return the USB device's serial number string descriptor.

        This property will cause some USB traffic the first time it is accessed
        and cache the resulting value for future use.
        """
        if self._serial_number is None:
            self._serial_number = util.get_string(self, self.iSerialNumber)
        return self._serial_number

    @property
    def product(self):
        """ Return the USB device's product string descriptor.

        This property will cause some USB traffic the first time it is accessed
        and cache the resulting value for future use.
        """
        if self._product is None:
            self._product = util.get_string(self, self.iProduct)
        return self._product

    @property
    def manufacturer(self):
        """ Return the USB device's manufacturer string descriptor.

        This property will cause some USB traffic the first time it is accessed
        and cache the resulting value for future use.
        """
        if self._manufacturer is None:
            self._manufacturer = util.get_string(self, self.iManufacturer)
        return self._manufacturer

    @property
    def backend(self):
        """Return the backend being used by the device."""
        return self._ctx.backend

    def set_configuration(self, configuration = None):
        r"""Set the active configuration.

        The configuration parameter is the bConfigurationValue field of the
        configuration you want to set as active. If you call this method
        without parameter, it will use the first configuration found.  As a
        device hardly ever has more than one configuration, calling the method
        without arguments is enough to get the device ready.
        """
        self._ctx.managed_set_configuration(self, configuration)

    def get_active_configuration(self):
        r"""Return a Configuration object representing the current
        configuration set.
        """
        return self._ctx.get_active_configuration(self)

    def set_interface_altsetting(self, interface = None, alternate_setting = None):
        r"""Set the alternate setting for an interface.

        When you want to use an interface and it has more than one alternate
        setting, you should call this method to select the appropriate
        alternate setting. If you call the method without one or the two
        parameters, it will be selected the first one found in the Device in
        the same way of the set_configuration method.

        Commonly, an interface has only one alternate setting and this call is
        not necessary. For most devices, either it has more than one
        alternate setting or not, it is not harmful to make a call to this
        method with no arguments, as devices will silently ignore the request
        when there is only one alternate setting, though the USB Spec allows
        devices with no additional alternate setting return an error to the
        Host in response to a SET_INTERFACE request.

        If you are in doubt, you may want to call it with no arguments wrapped
        by a try/except clause:

        >>> try:
        >>>     dev.set_interface_altsetting()
        >>> except usb.core.USBError:
        >>>     pass
        """
        self._ctx.managed_set_interface(self, interface, alternate_setting)

    def clear_halt(self, ep):
        r""" Clear the halt/stall condition for the endpoint ep."""
        if isinstance(ep, Endpoint):
            ep = ep.bEndpointAddress
        self._ctx.managed_open()
        self._ctx.backend.clear_halt(self._ctx.handle, ep)

    def reset(self):
        r"""Reset the device."""
        self._ctx.managed_open()
        self._ctx.dispose(self, False)
        self._ctx.backend.reset_device(self._ctx.handle)
        self._ctx.dispose(self, True)

    def write(self, endpoint, data, timeout = None):
        r"""Write data to the endpoint.

        This method is used to send data to the device. The endpoint parameter
        corresponds to the bEndpointAddress member whose endpoint you want to
        communicate with.

        The data parameter should be a sequence like type convertible to
        the array type (see array module).

        The timeout is specified in miliseconds.

        The method returns the number of bytes written.
        """
        backend = self._ctx.backend

        fn_map = {
                    util.ENDPOINT_TYPE_BULK:backend.bulk_write,
                    util.ENDPOINT_TYPE_INTR:backend.intr_write,
                    util.ENDPOINT_TYPE_ISO:backend.iso_write
                }

        intf, ep = self._ctx.setup_request(self, endpoint)
        fn = fn_map[util.endpoint_type(ep.bmAttributes)]

        return fn(
                self._ctx.handle,
                ep.bEndpointAddress,
                intf.bInterfaceNumber,
                _interop.as_array(data),
                self.__get_timeout(timeout)
            )

    def read(self, endpoint, size_or_buffer, timeout = None):
        r"""Read data from the endpoint.

        This method is used to receive data from the device. The endpoint
        parameter corresponds to the bEndpointAddress member whose endpoint
        you want to communicate with. The size_or_buffer parameter either
        tells how many bytes you want to read or supplies the buffer to
        receive the data (it *must* be an object of the type array).

        The timeout is specified in miliseconds.

        If the size_or_buffer parameter is the number of bytes to read, the
        method returns an array object with the data read. If the
        size_or_buffer parameter is an array object, it returns the number
        of bytes actually read.
        """
        backend = self._ctx.backend

        fn_map = {
                    util.ENDPOINT_TYPE_BULK:backend.bulk_read,
                    util.ENDPOINT_TYPE_INTR:backend.intr_read,
                    util.ENDPOINT_TYPE_ISO:backend.iso_read
                }

        intf, ep = self._ctx.setup_request(self, endpoint)
        fn = fn_map[util.endpoint_type(ep.bmAttributes)]

        if isinstance(size_or_buffer, array.array):
            buff = size_or_buffer
        else: # here we consider it is a integer
            buff = util.create_buffer(size_or_buffer)

        ret = fn(
                self._ctx.handle,
                ep.bEndpointAddress,
                intf.bInterfaceNumber,
                buff,
                self.__get_timeout(timeout))

        if isinstance(size_or_buffer, array.array):
            return ret
        elif ret != len(buff) * buff.itemsize:
            return buff[:ret]
        else:
            return buff

    def ctrl_transfer(self, bmRequestType, bRequest, wValue=0, wIndex=0,
            data_or_wLength = None, timeout = None):
        r"""Do a control transfer on the endpoint 0.

        This method is used to issue a control transfer over the endpoint 0
        (endpoint 0 is required to always be a control endpoint).

        The parameters bmRequestType, bRequest, wValue and wIndex are the same
        of the USB Standard Control Request format.

        Control requests may or may not have a data payload to write/read.
        In cases which it has, the direction bit of the bmRequestType
        field is used to infer the desired request direction. For
        host to device requests (OUT), data_or_wLength parameter is
        the data payload to send, and it must be a sequence type convertible
        to an array object. In this case, the return value is the number
        of bytes written in the data payload. For device to host requests
        (IN), data_or_wLength is either the wLength parameter of the control
        request specifying the number of bytes to read in data payload, and
        the return value is an array object with data read, or an array
        object which the data will be read to, and the return value is the
        number of bytes read.
        """
        try:
            buff = util.create_buffer(data_or_wLength)
        except TypeError:
            buff = _interop.as_array(data_or_wLength)

        self._ctx.managed_open()

        # Thanks to Johannes Stezenbach to point me out that we need to
        # claim the recipient interface
        recipient = bmRequestType & 3
        rqtype = bmRequestType & (3 << 5)
        if recipient == util.CTRL_RECIPIENT_INTERFACE \
                and rqtype != util.CTRL_TYPE_VENDOR:
            interface_number = wIndex & 0xff
            self._ctx.managed_claim_interface(self, interface_number)

        ret = self._ctx.backend.ctrl_transfer(
                                    self._ctx.handle,
                                    bmRequestType,
                                    bRequest,
                                    wValue,
                                    wIndex,
                                    buff,
                                    self.__get_timeout(timeout))

        if isinstance(data_or_wLength, array.array) \
                or util.ctrl_direction(bmRequestType) == util.CTRL_OUT:
            return ret
        elif ret != len(buff) * buff.itemsize:
            return buff[:ret]
        else:
            return buff

    def is_kernel_driver_active(self, interface):
        r"""Determine if there is kernel driver associated with the interface.

        If a kernel driver is active, the object will be unable to perform
        I/O.

        The interface parameter is the device interface number to check.
        """
        self._ctx.managed_open()
        return self._ctx.backend.is_kernel_driver_active(
                self._ctx.handle,
                interface)

    def detach_kernel_driver(self, interface):
        r"""Detach a kernel driver.

        If successful, you will then be able to perform I/O.

        The interface parameter is the device interface number to detach the
        driver from.
        """
        self._ctx.managed_open()
        self._ctx.backend.detach_kernel_driver(
            self._ctx.handle,
            interface)

    def attach_kernel_driver(self, interface):
        r"""Re-attach an interface's kernel driver, which was previously
        detached using detach_kernel_driver().

        The interface parameter is the device interface number to attach the
        driver to.
        """
        self._ctx.managed_open()
        self._ctx.backend.attach_kernel_driver(
            self._ctx.handle,
            interface)

    def __iter__(self):
        r"""Iterate over all configurations of the device."""
        for i in range(self.bNumConfigurations):
            yield Configuration(self, i)

    def __getitem__(self, index):
        r"""Return the Configuration object in the given position."""
        return Configuration(self, index)

    def _finalize_object(self):
        self._ctx.dispose(self)

    def __get_timeout(self, timeout):
        if timeout is not None:
            return timeout
        return self.__default_timeout

    def __set_def_tmo(self, tmo):
        if tmo < 0:
            raise ValueError('Timeout cannot be a negative value')
        self.__default_timeout = tmo

    def __get_def_tmo(self):
        return self.__default_timeout

    def _str(self):
        return "DEVICE ID %04x:%04x on Bus %03d Address %03d" % (
            self.idVendor, self.idProduct, self.bus, self.address)

    def _get_full_descriptor_str(self):
        headstr = self._str() + " "

        if self.bcdUSB & 0xf:
            low_bcd_usb = str(self.bcdUSB & 0xf)
        else:
            low_bcd_usb = ""

        if self.bcdDevice & 0xf:
            low_bcd_device = str(self.bcdDevice & 0xf)
        else:
            low_bcd_device = ""

        return "%s%s\n" %  (headstr, "=" * (60 - len(headstr))) + \
        " %-23s:%#7x (18 bytes)\n" % (
            "bLength", self.bLength) + \
        " %-23s:%#7x %s\n" % (
            "bDescriptorType", self.bDescriptorType,
            _try_lookup(_lu.descriptors, self.bDescriptorType)) + \
        " %-23s:%#7x USB %d.%d%s\n" % (
            "bcdUSB", self.bcdUSB, (self.bcdUSB & 0xff00)>>8,
            (self.bcdUSB & 0xf0) >> 4, low_bcd_usb) + \
        " %-23s:%#7x %s\n" % (
            "bDeviceClass", self.bDeviceClass,
            _try_lookup(_lu.device_classes, self.bDeviceClass)) + \
        " %-23s:%#7x\n" % (
            "bDeviceSubClass", self.bDeviceSubClass) + \
        " %-23s:%#7x\n" % (
            "bDeviceProtocol", self.bDeviceProtocol) + \
        " %-23s:%#7x (%d bytes)\n" % (
            "bMaxPacketSize0", self.bMaxPacketSize0, self.bMaxPacketSize0) + \
        " %-23s: %#06x\n" % (
            "idVendor", self.idVendor) + \
        " %-23s: %#06x\n" % (
            "idProduct", self.idProduct) + \
        " %-23s:%#7x Device %d.%d%s\n" % (
            "bcdDevice", self.bcdDevice, (self.bcdDevice & 0xff00)>>8,
            (self.bcdDevice & 0xf0) >> 4, low_bcd_device) + \
        " %-23s:%#7x %s\n" % (
            "iManufacturer", self.iManufacturer,
            _try_get_string(self, self.iManufacturer)) + \
        " %-23s:%#7x %s\n" % (
            "iProduct", self.iProduct,
            _try_get_string(self, self.iProduct)) + \
        " %-23s:%#7x %s\n" % (
            "iSerialNumber", self.iSerialNumber,
            _try_get_string(self, self.iSerialNumber)) + \
        " %-23s:%#7x" % (
            "bNumConfigurations", self.bNumConfigurations)

    default_timeout = property(
                        __get_def_tmo,
                        __set_def_tmo,
                        doc = 'Default timeout for transfer I/O functions'
                    )


def find(find_all=False, backend = None, custom_match = None, **args):
    r"""Find an USB device and return it.

    find() is the function used to discover USB devices.  You can pass as
    arguments any combination of the USB Device Descriptor fields to match a
    device. For example:

    find(idVendor=0x3f4, idProduct=0x2009)

    will return the Device object for the device with idVendor field equals
    to 0x3f4 and idProduct equals to 0x2009.

    If there is more than one device which matchs the criteria, the first one
    found will be returned. If a matching device cannot be found the function
    returns None. If you want to get all devices, you can set the parameter
    find_all to True, then find will return an iterator with all matched devices.
    If no matching device is found, it will return an empty iterator. Example:

    for printer in find(find_all=True, bDeviceClass=7):
        print (printer)

    This call will get all the USB printers connected to the system.  (actually
    may be not, because some devices put their class information in the
    Interface Descriptor).

    You can also use a customized match criteria:

    dev = find(custom_match = lambda d: d.idProduct=0x3f4 and d.idvendor=0x2009)

    A more accurate printer finder using a customized match would be like
    so:

    def is_printer(dev):
        import usb.util
        if dev.bDeviceClass == 7:
            return True
        for cfg in dev:
            if usb.util.find_descriptor(cfg, bInterfaceClass=7) is not None:
                return True

    for printer in find(find_all=True, custom_match = is_printer):
        print (printer)

    Now even if the device class code is in the interface descriptor the
    printer will be found.

    You can combine a customized match with device descriptor fields. In this
    case, the fields must match and the custom_match must return True. In the
    our previous example, if we would like to get all printers belonging to the
    manufacturer 0x3f4, the code would be like so:

    printers = list(find(find_all=True, idVendor=0x3f4, custom_match=is_printer))

    If you want to use find as a 'list all devices' function, just call
    it with find_all = True:

    devices = list(find(find_all=True))

    Finally, you can pass a custom backend to the find function:

    find(backend = MyBackend())

    PyUSB has builtin backends for libusb 0.1, libusb 1.0 and OpenUSB.  If you
    do not supply a backend explicitly, find() function will select one of the
    predefineds backends according to system availability.

    Backends are explained in the usb.backend module.
    """
    def device_iter(**kwargs):
        for dev in backend.enumerate_devices():
            d = Device(dev, backend)
            tests = (val == getattr(d, key) for key, val in kwargs.items())
            if _interop._all(tests) and (custom_match is None or custom_match(d)):
                yield d

    if backend is None:
        import usb.backend.libusb1 as libusb1
        import usb.backend.libusb0 as libusb0
        import usb.backend.openusb as openusb

        for m in (libusb1, openusb, libusb0):
            backend = m.get_backend()
            if backend is not None:
                _logger.info('find(): using backend "%s"', m.__name__)
                break
        else:
            raise NoBackendError('No backend available')

    if find_all:
        return device_iter(**args)
    else:
        try:
            return _interop._next(device_iter(**args))
        except StopIteration:
            return None

def show_devices(verbose=False, **kwargs):
    """Show information about connected devices.

    The verbose flag sets to verbose or not.
    **kwargs are passed directly to the find() function.
    """
    kwargs["find_all"] = True
    devices = find(**kwargs)
    strings = ""
    for device in devices:
        if not verbose:
            strings +=  "%s, %s\n" % (device._str(), _try_lookup(
                _lu.device_classes, device.bDeviceClass))
        else:
            strings += "%s\n\n" % str(device)

    return _DescriptorInfo(strings)
