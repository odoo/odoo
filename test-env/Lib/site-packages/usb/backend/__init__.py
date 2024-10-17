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

r"""usb.backend - Backend interface.

This module exports:

IBackend - backend interface.

Backends are Python objects which implement the IBackend interface.
The easiest way to do so is inherinting from IBackend.

PyUSB already provides backends for libusb versions 0.1 and 1.0,
and OpenUSB library. Backends modules included with PyUSB are required to
export the get_backend() function, which returns an instance of a backend
object. You can provide your own customized backend if you
want to. Below you find a skeleton of a backend implementation module:

import usb.backend

class MyBackend(usb.backend.IBackend):
    pass

def get_backend():
    return MyBackend()

You can use your customized backend by passing it as the backend parameter of the
usb.core.find() function. For example:

import custom_backend
import usb.core

myidVendor = 0xfffe
myidProduct = 0x0001

mybackend = custom_backend.get_backend()

dev = usb.core.find(backend = mybackend, idProduct=myidProduct,
                    idVendor=myidVendor)

For custom backends, you are not required to supply the get_backend() function,
since the application code will instantiate the backend.

If you do not provide a backend to the find() function, it will use one of the
defaults backend according to its internal rules. For details, consult the
find() function documentation.
"""

import usb._objfinalizer as _objfinalizer

__author__ = 'Wander Lairson Costa'

__all__ = ['IBackend', 'libusb01', 'libusb10', 'openusb']

def _not_implemented(func):
    raise NotImplementedError(func.__name__)

class IBackend(_objfinalizer.AutoFinalizedObject):
    r"""Backend interface.

    IBackend is the basic interface for backend implementations. By default,
    the methods of the interface raise a NotImplementedError exception. A
    backend implementation should replace the methods to provide the funcionality
    necessary.

    As Python is a dynamic typed language, you are not obligated to inherit from
    IBackend: everything that behaves like an IBackend is an IBackend. But you
    are strongly recommended to do so, inheriting from IBackend provides consistent
    default behavior.
    """

    def enumerate_devices(self):
        r"""This function is required to return an iterable object which
        yields an implementation defined device identification for each
        USB device found in the system.

        The device identification object is used as argument to other methods
        of the interface.
        """
        _not_implemented(self.enumerate_devices)

    def get_device_descriptor(self, dev):
        r"""Return the device descriptor of the given device.

        The object returned is required to have all the Device Descriptor
        fields accessible as member variables. They must be convertible (but
        not required to be equal) to the int type.

        dev is an object yielded by the iterator returned by the enumerate_devices()
        method.
        """
        _not_implemented(self.get_device_descriptor)

    def get_configuration_descriptor(self, dev, config):
        r"""Return a configuration descriptor of the given device.

        The object returned is required to have all the Configuration Descriptor
        fields acessible as member variables. They must be convertible (but
        not required to be equal) to the int type.

        The dev parameter is the device identification object.
        config is the logical index of the configuration (not the bConfigurationValue
        field).  By "logical index" we mean the relative order of the configurations
        returned by the peripheral as a result of GET_DESCRIPTOR request.
        """
        _not_implemented(self.get_configuration_descriptor)

    def get_interface_descriptor(self, dev, intf, alt, config):
        r"""Return an interface descriptor of the given device.

        The object returned is required to have all the Interface Descriptor
        fields accessible as member variables. They must be convertible (but
        not required to be equal) to the int type.

        The dev parameter is the device identification object.
        The intf parameter is the interface logical index (not the bInterfaceNumber field)
        and alt is the alternate setting logical index (not the bAlternateSetting value).
        Not every interface has more than one alternate setting.  In this case, the alt
        parameter should be zero. config is the configuration logical index (not the
        bConfigurationValue field).
        """
        _not_implemented(self.get_interface_descriptor)

    def get_endpoint_descriptor(self, dev, ep, intf, alt, config):
        r"""Return an endpoint descriptor of the given device.

        The object returned is required to have all the Endpoint Descriptor
        fields acessible as member variables. They must be convertible (but
        not required to be equal) to the int type.

        The ep parameter is the endpoint logical index (not the bEndpointAddress
        field) of the endpoint descriptor desired. dev, intf, alt and config are the same
        values already described in the get_interface_descriptor() method.
        """
        _not_implemented(self.get_endpoint_descriptor)

    def open_device(self, dev):
        r"""Open the device for data exchange.

        This method opens the device identified by the dev parameter for communication.
        This method must be called before calling any communication related method, such
        as transfer methods.

        It returns a handle identifying the communication instance. This handle must be
        passed to the communication methods.
        """
        _not_implemented(self.open_device)

    def close_device(self, dev_handle):
        r"""Close the device handle.

        This method closes the device communication channel and releases any
        system resources related to it.
        """
        _not_implemented(self.close_device)

    def set_configuration(self, dev_handle, config_value):
        r"""Set the active device configuration.

        This method should be called to set the active configuration
        of the device. The dev_handle parameter is the value returned
        by the open_device() method and the config_value parameter is the
        bConfigurationValue field of the related configuration descriptor.
        """
        _not_implemented(self.set_configuration)

    def get_configuration(self, dev_handle):
        r"""Get the current active device configuration.

        This method returns the bConfigurationValue of the currently
        active configuration. Depending on the backend and the OS,
        either a cached value may be returned or a control request may
        be issued. The dev_handle parameter is the value returned by
        the open_device method.
        """
        _not_implemented(self.get_configuration)

    def set_interface_altsetting(self, dev_handle, intf, altsetting):
        r"""Set the interface alternate setting.

        This method should only be called when the interface has more than
        one alternate setting. The dev_handle is the value returned by the
        open_device() method. intf and altsetting are respectivelly the
        bInterfaceNumber and bAlternateSetting fields of the related interface.
        """
        _not_implemented(self.set_interface_altsetting)

    def claim_interface(self, dev_handle, intf):
        r"""Claim the given interface.

        Interface claiming is not related to USB spec itself, but it is
        generally an necessary call of the USB libraries. It requests exclusive
        access to the interface on the system. This method must be called
        before using one of the transfer methods.

        dev_handle is the value returned by the open_device() method and
        intf is the bInterfaceNumber field of the desired interface.
        """
        _not_implemented(self.claim_interface)

    def release_interface(self, dev_handle, intf):
        r"""Release the claimed interface.

        dev_handle and intf are the same parameters of the claim_interface
        method.
        """
        _not_implemented(self.release_interface)

    def bulk_write(self, dev_handle, ep, intf, data, timeout):
        r"""Perform a bulk write.

        dev_handle is the value returned by the open_device() method.
        The ep parameter is the bEndpointAddress field whose endpoint
        the data will be sent to. intf is the bInterfaceNumber field
        of the interface containing the endpoint. The data parameter
        is the data to be sent. It must be an instance of the array.array
        class. The timeout parameter specifies a time limit to the operation
        in miliseconds.

        The method returns the number of bytes written.
        """
        _not_implemented(self.bulk_write)

    def bulk_read(self, dev_handle, ep, intf, buff, timeout):
        r"""Perform a bulk read.

        dev_handle is the value returned by the open_device() method.
        The ep parameter is the bEndpointAddress field whose endpoint
        the data will be received from. intf is the bInterfaceNumber field
        of the interface containing the endpoint. The buff parameter
        is the buffer to receive the data read, the length of the buffer
        tells how many bytes should be read. The timeout parameter
        specifies a time limit to the operation in miliseconds.

        The method returns the number of bytes actually read.
        """
        _not_implemented(self.bulk_read)

    def intr_write(self, dev_handle, ep, intf, data, timeout):
        r"""Perform an interrupt write.

        dev_handle is the value returned by the open_device() method.
        The ep parameter is the bEndpointAddress field whose endpoint
        the data will be sent to. intf is the bInterfaceNumber field
        of the interface containing the endpoint. The data parameter
        is the data to be sent. It must be an instance of the array.array
        class. The timeout parameter specifies a time limit to the operation
        in miliseconds.

        The method returns the number of bytes written.
        """
        _not_implemented(self.intr_write)

    def intr_read(self, dev_handle, ep, intf, size, timeout):
        r"""Perform an interrut read.

        dev_handle is the value returned by the open_device() method.
        The ep parameter is the bEndpointAddress field whose endpoint
        the data will be received from. intf is the bInterfaceNumber field
        of the interface containing the endpoint. The buff parameter
        is the buffer to receive the data read, the length of the buffer
        tells how many bytes should be read.  The timeout parameter
        specifies a time limit to the operation in miliseconds.

        The method returns the number of bytes actually read.
        """
        _not_implemented(self.intr_read)

    def iso_write(self, dev_handle, ep, intf, data, timeout):
        r"""Perform an isochronous write.

        dev_handle is the value returned by the open_device() method.
        The ep parameter is the bEndpointAddress field whose endpoint
        the data will be sent to. intf is the bInterfaceNumber field
        of the interface containing the endpoint. The data parameter
        is the data to be sent. It must be an instance of the array.array
        class. The timeout parameter specifies a time limit to the operation
        in miliseconds.

        The method returns the number of bytes written.
        """
        _not_implemented(self.iso_write)

    def iso_read(self, dev_handle, ep, intf, size, timeout):
        r"""Perform an isochronous read.

        dev_handle is the value returned by the open_device() method.
        The ep parameter is the bEndpointAddress field whose endpoint
        the data will be received from. intf is the bInterfaceNumber field
        of the interface containing the endpoint. The buff parameter
        is buffer to receive the data read, the length of the buffer tells
        how many bytes should be read. The timeout parameter specifies
        a time limit to the operation in miliseconds.

        The method returns the number of bytes actually read.
        """
        _not_implemented(self.iso_read)

    def ctrl_transfer(self,
                      dev_handle,
                      bmRequestType,
                      bRequest,
                      wValue,
                      wIndex,
                      data,
                      timeout):
        r"""Perform a control transfer on the endpoint 0.

        The direction of the transfer is inferred from the bmRequestType
        field of the setup packet.

        dev_handle is the value returned by the open_device() method.
        bmRequestType, bRequest, wValue and wIndex are the same fields
        of the setup packet. data is an array object, for OUT requests
        it contains the bytes to transmit in the data stage and for
        IN requests it is the buffer to hold the data read. The number
        of bytes requested to transmit or receive is equal to the length
        of the array times the data.itemsize field. The timeout parameter
        specifies a time limit to the operation in miliseconds.

        Return the number of bytes written (for OUT transfers) or the data
        read (for IN transfers), as an array.array object.
        """
        _not_implemented(self.ctrl_transfer)

    def clear_halt(self, dev_handle, ep):
        r"""Clear the halt/stall condition for the endpoint."""
        _not_implemented(self.clear_halt)

    def reset_device(self, dev_handle):
        r"""Reset the device."""
        _not_implemented(self.reset_device)

    def is_kernel_driver_active(self, dev_handle, intf):
        r"""Determine if a kernel driver is active on an interface.

        If a kernel driver is active, you cannot claim the interface,
        and the backend will be unable to perform I/O.
        """
        _not_implemented(self.is_kernel_driver_active)

    def detach_kernel_driver(self, dev_handle, intf):
        r"""Detach a kernel driver from an interface.

        If successful, you will then be able to claim the interface
        and perform I/O.
        """
        _not_implemented(self.detach_kernel_driver)

    def attach_kernel_driver(self, dev_handle, intf):
        r"""Re-attach an interface's kernel driver, which was previously
        detached using detach_kernel_driver()."""
        _not_implemented(self.attach_kernel_driver)
