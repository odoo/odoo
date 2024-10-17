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

r"""usb.util - Utility functions.

This module exports:

endpoint_address - return the endpoint absolute address.
endpoint_direction - return the endpoint transfer direction.
endpoint_type - return the endpoint type
ctrl_direction - return the direction of a control transfer
build_request_type - build a bmRequestType field of a control transfer.
find_descriptor - find an inner descriptor.
claim_interface - explicitly claim an interface.
release_interface - explicitly release an interface.
dispose_resources - release internal resources allocated by the object.
get_langids - retrieve the list of supported string languages from the device.
get_string - retrieve a string descriptor from the device.
"""

__author__ = 'Wander Lairson Costa'

import operator
import array
from sys import hexversion
import usb._interop as _interop

# descriptor type
DESC_TYPE_DEVICE = 0x01
DESC_TYPE_CONFIG = 0x02
DESC_TYPE_STRING = 0x03
DESC_TYPE_INTERFACE = 0x04
DESC_TYPE_ENDPOINT = 0x05

# endpoint direction
ENDPOINT_IN = 0x80
ENDPOINT_OUT = 0x00

# endpoint type
ENDPOINT_TYPE_CTRL = 0x00
ENDPOINT_TYPE_ISO = 0x01
ENDPOINT_TYPE_BULK = 0x02
ENDPOINT_TYPE_INTR = 0x03

# control request type
CTRL_TYPE_STANDARD = (0 << 5)
CTRL_TYPE_CLASS = (1 << 5)
CTRL_TYPE_VENDOR = (2 << 5)
CTRL_TYPE_RESERVED = (3 << 5)

# control request recipient
CTRL_RECIPIENT_DEVICE = 0
CTRL_RECIPIENT_INTERFACE = 1
CTRL_RECIPIENT_ENDPOINT = 2
CTRL_RECIPIENT_OTHER = 3

# control request direction
CTRL_OUT = 0x00
CTRL_IN = 0x80

_ENDPOINT_ADDR_MASK = 0x0f
_ENDPOINT_DIR_MASK = 0x80
_ENDPOINT_TRANSFER_TYPE_MASK = 0x03
_CTRL_DIR_MASK = 0x80

# For compatibility between Python 2 and 3
_dummy_s = '\x00'.encode('utf-8')

# speed type
SPEED_LOW = 1
SPEED_FULL = 2
SPEED_HIGH = 3
SPEED_SUPER = 4
SPEED_UNKNOWN = 0

def endpoint_address(address):
    r"""Return the endpoint absolute address.

    The address parameter is the bEndpointAddress field
    of the endpoint descriptor.
    """
    return address & _ENDPOINT_ADDR_MASK

def endpoint_direction(address):
    r"""Return the endpoint direction.

    The address parameter is the bEndpointAddress field
    of the endpoint descriptor.
    The possible return values are ENDPOINT_OUT or ENDPOINT_IN.
    """
    return address & _ENDPOINT_DIR_MASK

def endpoint_type(bmAttributes):
    r"""Return the transfer type of the endpoint.

    The bmAttributes parameter is the bmAttributes field
    of the endpoint descriptor.
    The possible return values are: ENDPOINT_TYPE_CTRL,
    ENDPOINT_TYPE_ISO, ENDPOINT_TYPE_BULK or ENDPOINT_TYPE_INTR.
    """
    return bmAttributes & _ENDPOINT_TRANSFER_TYPE_MASK

def ctrl_direction(bmRequestType):
    r"""Return the direction of a control request.

    The bmRequestType parameter is the value of the
    bmRequestType field of a control transfer.
    The possible return values are CTRL_OUT or CTRL_IN.
    """
    return bmRequestType & _CTRL_DIR_MASK

def build_request_type(direction, type, recipient):
    r"""Build a bmRequestType field for control requests.

    These is a conventional function to build a bmRequestType
    for a control request.

    The direction parameter can be CTRL_OUT or CTRL_IN.
    The type parameter can be CTRL_TYPE_STANDARD, CTRL_TYPE_CLASS,
    CTRL_TYPE_VENDOR or CTRL_TYPE_RESERVED values.
    The recipient can be CTRL_RECIPIENT_DEVICE, CTRL_RECIPIENT_INTERFACE,
    CTRL_RECIPIENT_ENDPOINT or CTRL_RECIPIENT_OTHER.

    Return the bmRequestType value.
    """
    return recipient | type | direction

def create_buffer(length):
    r"""Create a buffer to be passed to a read function.

    A read function may receive an out buffer so the data
    is read inplace and the object can be reused, avoiding
    the overhead of creating a new object at each new read
    call. This function creates a compatible sequence buffer
    of the given length.
    """
    return array.array('B', _dummy_s * length)

def find_descriptor(desc, find_all=False, custom_match=None, **args):
    r"""Find an inner descriptor.

    find_descriptor works in the same way as the core.find() function does,
    but it acts on general descriptor objects. For example, suppose you
    have a Device object called dev and want a Configuration of this
    object with its bConfigurationValue equals to 1, the code would
    be like so:

    >>> cfg = util.find_descriptor(dev, bConfigurationValue=1)

    You can use any field of the Descriptor as a match criteria, and you
    can supply a customized match just like core.find() does. The
    find_descriptor function also accepts the find_all parameter to get
    an iterator instead of just one descriptor.
    """
    def desc_iter(**kwargs):
        for d in desc:
            tests = (val == getattr(d, key) for key, val in kwargs.items())
            if _interop._all(tests) and (custom_match is None or custom_match(d)):
                yield d

    if find_all:
        return desc_iter(**args)
    else:
        try:
            return _interop._next(desc_iter(**args))
        except StopIteration:
            return None

def claim_interface(device, interface):
    r"""Explicitly claim an interface.

    PyUSB users normally do not have to worry about interface claiming,
    as the library takes care of it automatically. But there are situations
    where you need deterministic interface claiming. For these uncommon
    cases, you can use claim_interface.

    If the interface is already claimed, either through a previously call
    to claim_interface or internally by the device object, nothing happens.
    """
    device._ctx.managed_claim_interface(device, interface)

def release_interface(device, interface):
    r"""Explicitly release an interface.

    This function is used to release an interface previously claimed,
    either through a call to claim_interface or internally by the
    device object.

    Normally, you do not need to worry about claiming policies, as
    the device object takes care of it automatically.
    """
    device._ctx.managed_release_interface(device, interface)

def dispose_resources(device):
    r"""Release internal resources allocated by the object.

    Sometimes you need to provide deterministic resources
    freeing, for example to allow another application to
    talk to the device. As Python does not provide deterministic
    destruction, this function releases all internal resources
    allocated by the device, like device handle and interface
    policy.

    After calling this function, you can continue using the device
    object normally. If the resources will be necessary again, it
    will be allocated automatically.
    """
    device._ctx.dispose(device)

def get_langids(dev):
    r"""Retrieve the list of supported Language IDs from the device.

    Most client code should not call this function directly, but instead use
    the langids property on the Device object, which will call this function as
    needed and cache the result.

    USB LANGIDs are 16-bit integers familiar to Windows developers, where
    for example instead of en-US you say 0x0409. See the file USB_LANGIDS.pdf
    somewhere on the usb.org site for a list, which does not claim to be
    complete. It requires "system software must allow the enumeration and
    selection of LANGIDs that are not currently on this list." It also requires
    "system software should never request a LANGID not defined in the LANGID
    code array (string index = 0) presented by a device." Client code can
    check this tuple before issuing string requests for a specific language ID.

    dev is the Device object whose supported language IDs will be retrieved.

    The return value is a tuple of integer LANGIDs, possibly empty if the
    device does not support strings at all (which USB 3.1 r1.0 section
    9.6.9 allows). In that case client code should not request strings at all.

    A USBError may be raised from this function for some devices that have no
    string support, instead of returning an empty tuple. The accessor for the
    langids property on Device catches that case and supplies an empty tuple,
    so client code can ignore this detail by using the langids property instead
    of directly calling this function.
    """
    from usb.control import get_descriptor
    buf = get_descriptor(
                dev,
                254,
                DESC_TYPE_STRING,
                0
            )

    # The array is retrieved by asking for string descriptor zero, which is
    # never the index of a real string. The returned descriptor has bLength
    # and bDescriptorType bytes followed by pairs of bytes representing
    # little-endian LANGIDs. That is, buf[0] contains the length of the
    # returned array, buf[2] is the least-significant byte of the first LANGID
    # (if any), buf[3] is the most-significant byte, and in general the LSBs of
    # all the LANGIDs are given by buf[2:buf[0]:2] and MSBs by buf[3:buf[0]:2].
    # If the length of buf came back odd, something is wrong.

    if len(buf) < 4 or buf[0] < 4 or buf[0]&1 != 0:
        return ()

    return tuple(map(lambda x,y: x+(y<<8), buf[2:buf[0]:2], buf[3:buf[0]:2]))

def get_string(dev, index, langid = None):
    r"""Retrieve a string descriptor from the device.

    dev is the Device object which the string will be read from.

    index is the string descriptor index and langid is the Language
    ID of the descriptor. If langid is omitted, the string descriptor
    of the first Language ID will be returned.

    Zero is never the index of a real string. The USB spec allows a device to
    use zero in a string index field to indicate that no string is provided.
    So the caller does not have to treat that case specially, this function
    returns None if passed an index of zero, and generates no traffic
    to the device.

    The return value is the unicode string present in the descriptor, or None
    if the requested index was zero.

    It is a ValueError to request a real string (index not zero), if: the
    device's langid tuple is empty, or with an explicit langid the device does
    not support.
    """
    if 0 == index:
        return None

    from usb.control import get_descriptor
    langids = dev.langids

    if 0 == len(langids):
        raise ValueError("The device has no langid")
    if langid is None:
        langid = langids[0]
    elif langid not in langids:
        raise ValueError("The device does not support the specified langid")

    buf = get_descriptor(
                dev,
                255, # Maximum descriptor size
                DESC_TYPE_STRING,
                index,
                langid
            )
    if hexversion >= 0x03020000:
        return buf[2:buf[0]].tobytes().decode('utf-16-le')
    else:
        return buf[2:buf[0]].tostring().decode('utf-16-le')
