# iso9362.py - compatibility module for stdnum.bic
#
# Copyright (C) 2017 Arthur de Jong
#
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA
# 02110-1301 USA

# flake8: noqa

import sys
import warnings


warnings.warn(
    'The stdnum.iso9362 module has been renamed, use stdnum.bic instead.',
    DeprecationWarning, stacklevel=2)


# We ensure that stdnum.bic is exposed in this module's place
import stdnum.bic  # isort:skip
sys.modules[__name__] = stdnum.bic
