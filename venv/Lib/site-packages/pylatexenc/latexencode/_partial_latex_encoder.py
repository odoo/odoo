# -*- coding: utf-8 -*-
#
# The MIT License (MIT)
# 
# Copyright (c) 2021 Philippe Faist
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

from __future__ import print_function, absolute_import, unicode_literals

#import sys
import logging

logger = logging.getLogger(__name__)


from ._unicode_to_latex_encoder import (
    RULE_CALLABLE,
    UnicodeToLatexConversionRule,
    UnicodeToLatexEncoder
)

# if sys.version_info.major == 2:
#     bytes = str
#     str = unicode



class PartialLatexToLatexEncoder(UnicodeToLatexEncoder):
    r"""
    Encode a string while preserving some (fuzzily detected) LaTeX constructs
    that the input string already has (e.g. accent macros or inline math modes).

    Sometimes you need to fully LaTeX-encode a string that already has some
    LaTeX constructs.  For instance, titles of bibliographic entries might
    include some inline math or accents, but they might also include unicode
    characters that need to be encoded.  Using a
    :py:class:`UnicodeToLatexEncoder` on such strings would result in ugly
    doubly-escaped strings such as ``\textbackslash{}'\{e\}``.  Instead,
    constructs such as ``\'{e}`` should be preserved while other characters
    and/or constructs (say '&' or '%') as well as unicode characters should be
    encoded.

    This class offers a simple partial solution: Characters are encoded as per
    the given `conversion_rules` (or the default conversion rules of
    :py:class:`UnicodeToLatexEncoder` objects), except that the characters in
    `keep_latex_chars` are to be interpreted as LaTeX and are not to be further
    encoded.

    .. versionadded: 2.10
    """
    def __init__(self,
                 # keyword arguments:
                 keep_latex_chars=r'\${}^_', conversion_rules=None,
                 **kwargs):

        base_conversion_rules = conversion_rules
        if base_conversion_rules is None:
            base_conversion_rules = ['defaults']

        super(PartialLatexToLatexEncoder, self).__init__(
            # only a single rule, our own special method that tries to parse
            # partial latex.
            conversion_rules=[UnicodeToLatexConversionRule(
                rule_type=RULE_CALLABLE,
                rule=self._do_partial_latex_encode_step,
                replacement_latex_protection='none'
            )] + base_conversion_rules,
            **kwargs
        )

        self.keep_latex_chars = keep_latex_chars


    def _do_partial_latex_encode_step(self, s, pos):
        r"""
        This method is used as a "callable rule" for the
        :py:class:`UnicodeToLatexEncoder` object.

        The strategy is to see if we have something that looks like a LaTeX char
        we want to keep.  If so, keep it as is; if not, return `None` so that
        further rules can be considered by the base unicode encoder.
        """

        from ..latexwalker import LatexWalker

        if s[pos] in self.keep_latex_chars:
            # Read a token and if it is a macro, keep the full macro!
            lw = LatexWalker(s, tolerant_parsing=False)
            
            tok = lw.get_token(pos, environments=False)

            tok_as_latex = tok.pre_space + s[tok.pos : tok.pos+tok.len]

            # keep the LaTeX token as-is
            return (tok.pos+tok.len - pos, tok_as_latex)

        return None
