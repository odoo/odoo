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
version_info = (1, 0, 2)
__version__ = '%d.%d.%d' % version_info

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
