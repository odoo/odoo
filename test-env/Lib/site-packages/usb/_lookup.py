# Copyright (C) 2009-2014 Walker Inman
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

r"""usb._lookups - Lookup tables for USB
"""

descriptors = {
        0x1 : "Device",
        0x2 : "Configuration",
        0x3 : "String",
        0x4 : "Interface",
        0x5 : "Endpoint",
        0x6 : "Device qualifier",
        0x7 : "Other speed configuration",
        0x8 : "Interface power",
        0x9 : "OTG",
        0xA : "Debug",
        0xB : "Interface association",
        0xC : "Security",
        0xD : "Key",
        0xE : "Encryption type",
        0xF : "Binary device object store (BOS)",
        0x10 : "Device capability",
        0x11 : "Wireless endpoint companion",
        0x30 : "SuperSpeed endpoint companion",
        }

device_classes = {
        0x0 : "Specified at interface",
        0x2 : "Communications Device",
        0x9 : "Hub",
        0xF : "Personal Healthcare Device",
        0xDC : "Diagnostic Device",
        0xE0 : "Wireless Controller",
        0xEF : "Miscellaneous",
        0xFF : "Vendor-specific",
        }

interface_classes = {
        0x0 : "Reserved",
        0x1 : "Audio",
        0x2 : "CDC Communication",
        0x3 : "Human Interface Device",
        0x5 : "Physical",
        0x6 : "Image",
        0x7 : "Printer",
        0x8 : "Mass Storage",
        0x9 : "Hub",
        0xA : "CDC Data",
        0xB : "Smart Card",
        0xD : "Content Security",
        0xE : "Video",
        0xF : "Personal Healthcare",
        0xDC : "Diagnostic Device",
        0xE0 : "Wireless Controller",
        0xEF : "Miscellaneous",
        0xFE : "Application Specific",
        0xFF : "Vendor Specific",
        }

ep_attributes = {
        0x0 : "Control",
        0x1 : "Isochronous",
        0x2 : "Bulk",
        0x3 : "Interrupt",
        }

MAX_POWER_UNITS_USB2p0 = 2             # mA
MAX_POWER_UNITS_USB_SUPERSPEED = 8     # mA
