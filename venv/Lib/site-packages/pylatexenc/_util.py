# -*- coding: utf-8 -*-
#
# The MIT License (MIT)
# 
# Copyright (c) 2019 Philippe Faist
# 
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
# 
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
# 
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
#


# Internal module. Internal API may move, disappear or otherwise change at any
# time and without notice.


try:
    # Python >= 3.3
    from collections.abc import MutableMapping
except ImportError:
    from collections import MutableMapping

import warnings
import bisect


# ------------------------------------------------------------------------------



def pylatexenc_deprecated_ver(ver, msg, stacklevel=2):
    warnings.warn(
        "Deprecated (pylatexenc {}): {} ".format(ver, msg.strip()),
        DeprecationWarning,
        stacklevel=stacklevel+1
    )


def pylatexenc_deprecated_2(msg, stacklevel=2):
    warnings.warn(
        ( "Deprecated (pylatexenc 2.0): {} "
          "[see https://pylatexenc.readthedocs.io/en/latest/new-in-pylatexenc-2/]" )
        .format(msg.strip()),
        DeprecationWarning,
        stacklevel=stacklevel+1
    )



# ------------------------------------------------------------------------------





class LazyDict(MutableMapping):
    r"""
    A lazy dictionary that loads its data when it is first queried.

    This is used to store the legacy
    :py:data:`pylatexenc.latexwalker.default_macro_dict` as well as
    :py:data:`pylatexenc.latex2text.default_macro_dict` etc.  Such that these
    "dictionaries" are still exposed at the module-level, but the data is loaded
    only if they are actually queried.
    """
    def __init__(self, generate_dict_fn):
        self._full_dict = None
        self._generate_dict_fn = generate_dict_fn

    def _ensure_instance(self):
        if self._full_dict is not None:
            return
        self._full_dict = self._generate_dict_fn()

    def __getitem__(self, key):
        self._ensure_instance()
        return self._full_dict.__getitem__(key)

    def __setitem__(self, key, val):
        self._ensure_instance()
        return self._full_dict.__setitem__(key, val)

    def __delitem__(self, key):
        self._ensure_instance()
        return self._full_dict.__delitem__(key)

    def __iter__(self):
        self._ensure_instance()
        return iter(self._full_dict)

    def __len__(self):
        self._ensure_instance()
        return len(self._full_dict)

    def copy(self):
        self._ensure_instance()
        return self._full_dict.copy()

    def clear(self):
        self._ensure_instance()
        return self._full_dict.clear()





# ------------------------------------------------------------------------------




class LineNumbersCalculator(object):
    r"""
    Utility to calculate line numbers.
    """
    def __init__(self, s):
        super(LineNumbersCalculator, self).__init__()

        def find_all_new_lines(x):
            # first line starts at the beginning of the string
            yield 0
            k = 0
            while k < len(x):
                k = x.find('\n', k)
                if k == -1:
                    return
                k += 1
                # s[k] is the character after the newline, i.e., the 0-th column
                # of the new line
                yield k

        self._pos_new_lines = list(find_all_new_lines(s))

        
    def pos_to_lineno_colno(self, pos, as_dict=False):
        r"""
        Return the line and column number corresponding to the given `pos`.

        Return a tuple `(lineno, colno)` giving line number and column number.
        Line numbers start at 1 and column number start at zero, i.e., the
        beginning of the document (`pos=0`) has line and column number `(1,0)`.
        If `as_dict=True`, then a dictionary with keys 'lineno', 'colno' is
        returned instead of a tuple.
        """

        # find line number in list

        # line_no is the index of the last item in self._pos_new_lines that is <= pos.
        line_no = bisect.bisect_right(self._pos_new_lines, pos)-1
        assert line_no >= 0 and line_no < len(self._pos_new_lines)

        col_no = pos - self._pos_new_lines[line_no]
        # 1+... so that line and column numbers start at 1
        if as_dict:
            return {'lineno': 1 + line_no, 'colno': col_no}
        return (1 + line_no, col_no)


