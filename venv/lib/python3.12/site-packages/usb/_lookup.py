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
