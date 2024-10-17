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

r"""usb.control - USB standard control requests

This module exports:

get_status - get recipeint status
clear_feature - clear a recipient feature
set_feature - set a recipient feature
get_descriptor - get a device descriptor
set_descriptor - set a device descriptor
get_configuration - get a device configuration
set_configuration - set a device configuration
get_interface - get a device interface
set_interface - set a device interface
"""

__author__ = 'Wander Lairson Costa'

__all__ = ['get_status',
           'clear_feature',
           'set_feature',
           'get_descriptor',
           'set_descriptor',
           'get_configuration',
           'set_configuration',
           'get_interface',
           'set_interface',
           'ENDPOINT_HALT',
           'FUNCTION_SUSPEND',
           'DEVICE_REMOTE_WAKEUP',
           'U1_ENABLE',
           'U2_ENABLE',
           'LTM_ENABLE']

import usb.util as util
import usb.core as core

def _parse_recipient(recipient, direction):
    if recipient is None:
        r = util.CTRL_RECIPIENT_DEVICE
        wIndex = 0
    elif isinstance(recipient, core.Interface):
        r = util.CTRL_RECIPIENT_INTERFACE
        wIndex = recipient.bInterfaceNumber
    elif isinstance(recipient, core.Endpoint):
        r = util.CTRL_RECIPIENT_ENDPOINT
        wIndex = recipient.bEndpointAddress
    else:
        raise ValueError('Invalid recipient.')
    bmRequestType = util.build_request_type(
                            direction,
                            util.CTRL_TYPE_STANDARD,
                            r
                        )
    return (bmRequestType, wIndex)

# standard feature selectors from USB 2.0/3.0
ENDPOINT_HALT = 0
FUNCTION_SUSPEND = 0
DEVICE_REMOTE_WAKEUP = 1
U1_ENABLE = 48
U2_ENABLE = 49
LTM_ENABLE = 50

def get_status(dev, recipient = None):
    r"""Return the status for the specified recipient.

    dev is the Device object to which the request will be
    sent to.

    The recipient can be None (on which the status will be queried
    from the device), an Interface or Endpoint descriptors.

    The status value is returned as an integer with the lower
    word being the two bytes status value.
    """
    bmRequestType, wIndex = _parse_recipient(recipient, util.CTRL_IN)
    ret = dev.ctrl_transfer(bmRequestType = bmRequestType,
                            bRequest = 0x00,
                            wIndex = wIndex,
                            data_or_wLength = 2)
    return ret[0] | (ret[1] << 8)

def clear_feature(dev, feature, recipient = None):
    r"""Clear/disable a specific feature.

    dev is the Device object to which the request will be
    sent to.

    feature is the feature you want to disable.

    The recipient can be None (on which the status will be queried
    from the device), an Interface or Endpoint descriptors.
    """
    if feature == ENDPOINT_HALT:
        dev.clear_halt(recipient)
    else:
        bmRequestType, wIndex = _parse_recipient(recipient, util.CTRL_OUT)
        dev.ctrl_transfer(bmRequestType = bmRequestType,
                          bRequest = 0x01,
                          wIndex = wIndex,
                          wValue = feature)

def set_feature(dev, feature, recipient = None):
    r"""Set/enable a specific feature.

    dev is the Device object to which the request will be
    sent to.

    feature is the feature you want to enable.

    The recipient can be None (on which the status will be queried
    from the device), an Interface or Endpoint descriptors.
    """
    bmRequestType, wIndex = _parse_recipient(recipient, util.CTRL_OUT)
    dev.ctrl_transfer(bmRequestType = bmRequestType,
                      bRequest = 0x03,
                      wIndex = wIndex,
                      wValue = feature)

def get_descriptor(dev, desc_size, desc_type, desc_index, wIndex = 0):
    r"""Return the specified descriptor.

    dev is the Device object to which the request will be
    sent to.

    desc_size is the descriptor size.

    desc_type and desc_index are the descriptor type and index,
    respectively. wIndex index is used for string descriptors
    and represents the Language ID. For other types of descriptors,
    it is zero.
    """
    wValue = desc_index | (desc_type << 8)

    bmRequestType = util.build_request_type(
                        util.CTRL_IN,
                        util.CTRL_TYPE_STANDARD,
                        util.CTRL_RECIPIENT_DEVICE)

    return dev.ctrl_transfer(
            bmRequestType = bmRequestType,
            bRequest = 0x06,
            wValue = wValue,
            wIndex = wIndex,
            data_or_wLength = desc_size)

def set_descriptor(dev, desc, desc_type, desc_index, wIndex = None):
    r"""Update an existing descriptor or add a new one.

    dev is the Device object to which the request will be
    sent to.

    The desc parameter is the descriptor to be sent to the device.
    desc_type and desc_index are the descriptor type and index,
    respectively. wIndex index is used for string descriptors
    and represents the Language ID. For other types of descriptors,
    it is zero.
    """
    wValue = desc_index | (desc_type << 8)

    bmRequestType = util.build_request_type(
                        util.CTRL_OUT,
                        util.CTRL_TYPE_STANDARD,
                        util.CTRL_RECIPIENT_DEVICE)

    dev.ctrl_transfer(
        bmRequestType = bmRequestType,
        bRequest = 0x07,
        wValue = wValue,
        wIndex = wIndex,
        data_or_wLength = desc)

def get_configuration(dev):
    r"""Get the current active configuration of the device.

    dev is the Device object to which the request will be
    sent to.

    This function differs from the Device.get_active_configuration
    method because the later may use cached data, while this
    function always does a device request.
    """
    bmRequestType = util.build_request_type(
                            util.CTRL_IN,
                            util.CTRL_TYPE_STANDARD,
                            util.CTRL_RECIPIENT_DEVICE)

    return dev.ctrl_transfer(
                bmRequestType,
                bRequest = 0x08,
                data_or_wLength = 1)[0]

def set_configuration(dev, bConfigurationNumber):
    r"""Set the current device configuration.

    dev is the Device object to which the request will be
    sent to.
    """
    dev.set_configuration(bConfigurationNumber)

def get_interface(dev, bInterfaceNumber):
    r"""Get the current alternate setting of the interface.

    dev is the Device object to which the request will be
    sent to.
    """
    bmRequestType = util.build_request_type(
                            util.CTRL_IN,
                            util.CTRL_TYPE_STANDARD,
                            util.CTRL_RECIPIENT_INTERFACE)

    return dev.ctrl_transfer(
                bmRequestType = bmRequestType,
                bRequest = 0x0a,
                wIndex = bInterfaceNumber,
                data_or_wLength = 1)[0]

def set_interface(dev, bInterfaceNumber, bAlternateSetting):
    r"""Set the alternate setting of the interface.

    dev is the Device object to which the request will be
    sent to.
    """
    dev.set_interface_altsetting(bInterfaceNumber, bAlternateSetting)

