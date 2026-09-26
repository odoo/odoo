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

# All the hacks necessary to assure compatibility across all
# supported versions come here.
# Please, note that there is one version check for each
# hack we need to do, this makes maintenance easier... ^^

import sys
import array

__all__ = ['_reduce', '_set', '_next', '_update_wrapper']

# we support Python >= 2.4
assert sys.hexversion >= 0x020400f0

# On Python 3, reduce became a functools module function
try:
    import functools
    _reduce = functools.reduce
except (ImportError, AttributeError):
    _reduce = reduce

# all, introduced in Python 2.5
try:
    _all = all
except NameError:
    _all = lambda iter_ : _reduce( lambda x, y: x and y, iter_, True )

# we only have the builtin set type since 2.5 version
try:
    _set = set
except NameError:
    import sets
    _set = sets.Set

# On Python >= 2.6, we have the builtin next() function
# On Python 2.5 and before, we have to call the iterator method next()
def _next(iter):
    try:
        return next(iter)
    except NameError:
        return iter.next()

# functools appeared in 2.5
try:
    import functools
    _update_wrapper = functools.update_wrapper
except (ImportError, AttributeError):
    def _update_wrapper(wrapper, wrapped):
        wrapper.__name__ = wrapped.__name__
        wrapper.__module__ = wrapped.__module__
        wrapper.__doc__ = wrapped.__doc__
        wrapper.__dict__ = wrapped.__dict__

# this is used (as of May 2015) twice in core, once in backend/openusb, and in
# some unit test code. It would probably be clearer if written in terms of some
# definite 3.2+ API (bytearrays?) with a fallback provided for 2.4+.
def as_array(data=None):
    if data is None:
        return array.array('B')

    if isinstance(data, array.array):
        return data

    try:
        return array.array('B', data)
    except TypeError:
        # When you pass a unicode string or a character sequence,
        # you get a TypeError if the first parameter does not match
        a = array.array('B')
        a.frombytes(data.encode('utf-8'))
        return a
