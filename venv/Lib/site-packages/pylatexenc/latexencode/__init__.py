# -*- coding: utf-8 -*-
#
# The MIT License (MIT)
# 
# Copyright (c) 2018 Philippe Faist
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

r"""
The `latexencode` module provides a set of routines that allows you to
convert a unicode string to LaTeX escape sequences.

For basic usage you can use the :py:func:`unicode_to_latex()` function
directly::

  >>> from pylatexenc.latexencode import unicode_to_latex
  >>> print(unicode_to_latex('À votre santé'))
  \`A votre sant\'e
  >>> print(unicode_to_latex('The length of samples #3 & #4 is 3μm'))
  The length of samples \#3 \& \#4 is 3\ensuremath{\mu}m

The conversion is handled by the class :py:class:`UnicodeToLatexEncoder`.  If
you are converting multiple strings, you may create an instance with the flags
you like and invoke its method
:py:meth:`~UnicodeToLatexEncoder.unicode_to_latex()` as many times as necessary::

  >>> from pylatexenc.latexencode import UnicodeToLatexEncoder
  >>> u = UnicodeToLatexEncoder(unknown_char_policy='replace')
  >>> print(u.unicode_to_latex('À votre santé'))
  \`A votre sant\'e
  >>> print(u.unicode_to_latex('The length of samples #3 & #4 is 3μm'))
  The length of samples \#3 \& \#4 is 3\ensuremath{\mu}m
  >>> print(u.unicode_to_latex('À votre santé: 乾杯'))
  No known latex representation for character: U+4E7E - ‘乾’
  No known latex representation for character: U+676F - ‘杯’
  \`A votre sant\'e: {\bfseries ?}{\bfseries ?}

Example using custom conversion rules::

  >>> from pylatexenc.latexencode import UnicodeToLatexEncoder, \
  ...     UnicodeToLatexConversionRule, RULE_REGEX
  >>> u = UnicodeToLatexEncoder(
  ...     conversion_rules=[
  ...         UnicodeToLatexConversionRule(rule_type=RULE_REGEX, rule=[
  ...             (re.compile(r'-->'), r'\\textrightarrow'),
  ...             (re.compile(r'<--'), r'\\textleftarrow'),
  ...         ]),
  ...         'defaults'
  ...     ]
  ... )
  >>> print(u.unicode_to_latex("Cheers --> À votre santé"))
  Cheers {\textrightarrow} \`A votre sant\'e

See :py:class:`UnicodeToLatexEncoder` and
:py:class:`UnicodeToLatexConversionRule`.  Note for regex rules, the replacement
text is expanded like the second argument of `re.sub()` and backslashes need to
be escaped even inside raw strings.

.. versionadded:: 2.0

   The class :py:class:`UnicodeToLatexEncoder` along with its helper functions
   and classes were introduced in `pylatexenc 2.0`.

   The earlier function :py:func:`utf8tolatex()` that was available in
   `pylatexenc 1.x` is still provided unchanged, so code written for `pylatexenc
   1.x` should work without changes.  New code is however strongly encouraged to
   employ the new API.
"""

from __future__ import print_function, absolute_import, unicode_literals

import unicodedata
import logging
import sys
import functools
import itertools

if sys.version_info.major > 2:
    unicode = str # need to support unicode() w/ no arguments
    basestring = str
    # use MappingProxyType for keeping
    from types import MappingProxyType as _MappingProxyType
    # inspect function argument names
    from inspect import getfullargspec
else:
    _MappingProxyType = dict
    # inspect function argument names -- simulate getfullargspec with getargspec (argh...)
    from inspect import getargspec as getfullargspec

logger = logging.getLogger(__name__)



from .. import _util


# ------------------------------------------------


from ._unicode_to_latex_encoder import (
    get_builtin_uni2latex_dict,
    RULE_DICT,
    RULE_REGEX,
    RULE_CALLABLE,
    UnicodeToLatexConversionRule,
    get_builtin_conversion_rules,
    UnicodeToLatexEncoder,
)



# ------------------------------------------------

from ._partial_latex_encoder import (
    PartialLatexToLatexEncoder,
)



# ------------------------------------------------



_u2l_obj_cache = {}


def unicode_to_latex(s, non_ascii_only=False, replacement_latex_protection='braces',
                     unknown_char_policy='keep', unknown_char_warning=True):
    r"""
    Shorthand for constructing a :py:class:`UnicodeToLatexEncoder` instance and
    calling its :py:meth:`~UnicodeToLatexEncoder.unicode_to_latex()` method.

    The :py:class:`UnicodeToLatexEncoder` instances for given option settings
    are cached, making repeated calls to :py:func:`unicode_to_latex()` possible
    without creating a new instance upon each call.

    The parameters `non_ascii_only`, `replacement_latex_protection`,
    `unknown_char_policy`, and `unknown_char_warning` are directly passed on to
    the :py:class:`UnicodeToLatexEncoder` constructor.  See the class doc for
    :py:class:`UnicodeToLatexEncoder` for more information about what they do.

    You may only use arguments to this function that are python hashable (like
    `True`, `False`, or simple strings) to help us keep a cache of previously
    constructed :py:class:`UnicodeToLatexEncoder` instances.  For instance, it
    is not possible to provide a callable to `unknown_char_policy`.  It is also
    not possible to specify custom conversion rules with this helper function.
    If you need any of these features, simply create a
    :py:class:`UnicodeToLatexEncoder` instance directly.
    """

    key = (non_ascii_only, replacement_latex_protection, unknown_char_policy,
           unknown_char_warning)

    if key in _u2l_obj_cache:
        u = _u2l_obj_cache[key]
    else:
        u = UnicodeToLatexEncoder(non_ascii_only=non_ascii_only,
                                  replacement_latex_protection=replacement_latex_protection,
                                  unknown_char_policy=unknown_char_policy,
                                  unknown_char_warning=unknown_char_warning)
        _u2l_obj_cache[key] = u

    return u.unicode_to_latex(s)
    



# ------------------------------------------------------------------------------

# Don't change pylatexenc 1.x function:


def _get_deprecated_utf82latex():
    #
    # Don't issue a deprecation warning, because utf8tolatex() uses the
    # `utf82latex` dict even if it isn't modified by the user.
    #
    #     _util.pylatexenc_deprecated_2(
    #         "The module-level dictionary `pylatexenc.latexencode.utf82latex` is deprecated "
    #         "and might be removed in a future version of `pylatexenc`.",
    #     )

    # return a copy of the dict so that the user can modify the module-level
    # `utf82latex` dict without influencing the behavior of the new
    # `unicode_to_latex()` routines. (E.g., if two python modules use
    # pylatexenc.latexencode, we don't want one python module's use of
    # `utf2tolatex()` to influence the behavior of another module's use of
    # `unicode_to_latex()`.  If both modules use `utf8tolatex()`, we can't avoid
    # this influence.)
    from ._uni2latexmap import uni2latex as _uni2latex
    return _uni2latex.copy()


utf82latex = _util.LazyDict(generate_dict_fn=_get_deprecated_utf82latex)
"""
.. deprecated:: 2.0

   Pylatexenc 1.x exposed the module-level dictionary `utf82latex` that could be
   modified to alter the behavior of `utf8tolatex()`.

   If you would like to obtain a copy of the built-in unicode to text
   dictionary, see :py:func:`get_builtin_uni2latex_dict()`.  If you would like
   to alter the behavior of :py:func:`utf8tolatex()`, you should use
   :py:class:`UnicodeToLatexEncoder` which provides a rich interface for
   specifying rules how to convert chars to LaTeX escapes.

   For backwards compatibility, you can still modify the module-level dictionary
   `utf82latex` (but you can't assign a new object to it) and this will directly
   modify the global built-in dictionary of known latex escapes.  This is not
   recommended however, and the `utf82latex` module-level dictionary might be
   removed in the future.

   .. warning::

      Modifying the `utf82latex` module-level dictionary is not recommended.
      Doing so will alter the behavior of the `utf8tolatex()` function also for
      all other modules that also use `pylatexenc`!
"""




def utf8tolatex(s, non_ascii_only=False, brackets=True, substitute_bad_chars=False,
                fail_bad_chars=False):
    """
    .. note::

       Since `pylatexenc 2.0`, it is recommended to use the the
       :py:func:`unicode_to_latex()` function or the
       :py:class:`UnicodeToLatexEncoder` class instead of the earlier function
       `utf8tolatex()`.

       The new routines provide much more flexibility and versatility.  For
       instance, you can specify custom escape sequences for certain characters.
       Some cheap benchmarks seem to indicate that the new routines are not
       significantly slower than the `utf8tolatex()` function.  Also, the name
       `utf8tolatex()` was poorly chosen, since the argument is in fact not
       'utf-8'-encoded but rather a Python unicode string object.

       The function `utf8tolatex()` is still provided unchanged from `pylatexenc
       1.x`.  We do not plan to remove this function in the near future so it is
       not (yet) considered as deprecated and we will continue to provide it in
       near future versions of `pylatexenc`.  Bug reports, improvements, and new
       features will however be directed to :py:func:`UnicodeToLatexEncoder()`.

    Encode a UTF-8 string to a LaTeX snippet.

    If `non_ascii_only` is set to `True`, then usual (ascii) characters such as ``#``,
    ``{``, ``}`` etc. will not be escaped.  If set to `False` (the default), they are
    escaped to their respective LaTeX escape sequences.

    If `brackets` is set to `True` (the default), then LaTeX macros are enclosed in
    brackets.  For example, ``sant\N{LATIN SMALL LETTER E WITH ACUTE}`` is replaced by
    ``sant{\\'e}`` if `brackets=True` and by ``sant\\'e`` if `brackets=False`.

    .. warning::
        Using `brackets=False` might give you an invalid LaTeX string, so avoid
        it! (for instance, ``ma\N{LATIN SMALL LETTER I WITH CIRCUMFLEX}tre`` will be
        replaced incorrectly by ``ma\\^\\itre`` resulting in an unknown macro ``\\itre``).

    If `substitute_bad_chars=True`, then any non-ascii character for which no LaTeX escape
    sequence is known is replaced by a question mark in boldface. Otherwise (by default),
    the character is left as it is.

    If `fail_bad_chars=True`, then a `ValueError` is raised if we cannot find a
    character substitution for any non-ascii character.

    .. versionchanged:: 1.3

        Added `fail_bad_chars` switch
    """

    s = unicode(s) # make sure s is unicode
    s = unicodedata.normalize('NFC', s)

    if not s:
        return ""

    result = u""
    for ch in s:
        #logger.longdebug("Encoding char %r", ch)
        if (non_ascii_only and ord(ch) < 127):
            result += ch
        else:
            # use the `utf82latex` dict -- not `_uni2latex` which should NOT be
            # modified externally even for backwards-compatible code
            lch = utf82latex.get(ord(ch), None)
            if (lch is not None):
                # add brackets if needed, i.e. if we have a substituting macro.
                # note: in condition, beware, that lch might be of zero length.
                result += (  '{'+lch+'}' if brackets and lch[0:1] == '\\' else
                             lch  )
            elif ((ord(ch) >= 32 and ord(ch) <= 127) or
                  (ch in "\n\r\t")):
                # ordinary printable ascii char, just add it
                result += ch
            else:
                # non-ascii char
                msg = u"Character cannot be encoded into LaTeX: U+%04X - `%s'" % (ord(ch), ch)
                if fail_bad_chars:
                    raise ValueError(msg)

                logger.warning(msg)
                if substitute_bad_chars:
                    result += r'{\bfseries ?}'
                else:
                    # keep unescaped char
                    result += ch

    return result





