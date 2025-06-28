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

r"""PyUSB - Easy USB access in Python

This package exports the following modules and subpackages:

    core - the main USB implementation
    legacy - the compatibility layer with 0.x version
    backend - the support for backend implementations.
    control - USB standard control requests.
    libloader - helper module for backend library loading.

Since version 1.0, main PyUSB implementation lives in the 'usb.core'
module. New applications are encouraged to use it.
"""

import logging
import os

__author__ = 'Wander Lairson Costa'

# Use Semantic Versioning, http://semver.org/
try:
    from usb._version import version as __version__
except ImportError:
    __version__ = '0.0.0'

def _get_extended_version_info(version):
    import re
    m = re.match(r'(\d+)\.(\d+)\.(\d+)[.-]?(.*)', version)
    major, minor, patch, suffix = m.groups()
    return int(major), int(minor), int(patch), suffix

extended_version_info = _get_extended_version_info(__version__)
version_info = extended_version_info[:3]

__all__ = ['legacy', 'control', 'core', 'backend', 'util', 'libloader']

def _setup_log():
    from usb import _debug
    logger = logging.getLogger('usb')
    debug_level = os.getenv('PYUSB_DEBUG')

    if debug_level is not None:
        _debug.enable_tracing(True)
        filename = os.getenv('PYUSB_LOG_FILENAME')

        LEVELS = {'debug': logging.DEBUG,
                  'info': logging.INFO,
                  'warning': logging.WARNING,
                  'error': logging.ERROR,
                  'critical': logging.CRITICAL}

        level = LEVELS.get(debug_level, logging.CRITICAL + 10)
        logger.setLevel(level = level)

        try:
            handler = logging.FileHandler(filename)
        except:
            handler = logging.StreamHandler()

        fmt = logging.Formatter('%(asctime)s %(levelname)s:%(name)s:%(message)s')
        handler.setFormatter(fmt)
        logger.addHandler(handler)
    else:
        class NullHandler(logging.Handler):
            def emit(self, record):
                pass

        # We set the log level to avoid delegation to the
        # parent log handler (if there is one).
        # Thanks to Chris Clark to pointing this out.
        logger.setLevel(logging.CRITICAL + 10)

        logger.addHandler(NullHandler())


_setup_log()

# We import all 'legacy' module symbols to provide compatibility
# with applications that use 0.x versions.
from usb.legacy import *
