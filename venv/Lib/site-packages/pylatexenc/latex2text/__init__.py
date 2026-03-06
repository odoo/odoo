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
A simplistic, heuristic LaTeX code parser allowing to returns a text-only
approximation.  Suitable, e.g. for indexing tex code in a database for full text
searching.

The main class is :py:class:`LatexNodes2Text`.  For a quick start, try::

    from pylatexenc.latex2text import LatexNodes2Text

    latex = "... LaTeX code ..."
    text = LatexNodes2Text().latex_to_text(latex)

You may also use the command-line version of `latex2text`::

    $ echo '\textit{italic} \`acc\^ented text' | latex2text
    italic àccênted text

"""

from __future__ import print_function, unicode_literals #, absolute_import

import os
import re
import logging
import sys
import inspect
import textwrap

if sys.version_info.major >= 3:
    def unicode(string): return string
    basestring = str
    getfullargspec = inspect.getfullargspec
else:
    getfullargspec = inspect.getargspec
    chr = unichr

import pylatexenc
from .. import latexwalker
from .. import macrospec
from .. import _util

logger = logging.getLogger(__name__)



class MacroTextSpec(object):
    """
    A specification of how to obtain a textual representation of a macro.

    .. py:attribute:: macroname

       The name of the macro (no backslash)

    .. py:attribute:: simplify_repl

       The replacement text of the macro invocation.  This is either a string or
       a callable:

         - If `simplify_repl` is a string, this string is used as the text
           representation of this macro node.

           The string may contain a single '%s' replacement placeholder which
           will be replaced by the concatenated textual representation of all
           macro arguments.  Alternatively, the string may contain '%(<n>)s'
           (where `<n>` is an integer) to refer to the n-th argument (starting
           at '%(1)s').  You cannot mix the two %-formatting styles.

         - If `simplify_repl` is a callable, it should accept the corresponding
           :py:class:`pylatexenc.latexwalker.LatexMacroNode` as an argument.

           The callable will be inspected to see what other arguments it
           accepts.  If it accepts an argument named `l2tobj`, the
           :py:class:`LatexNodes2Text` instance is provided to that argument.
           If it accepts an argument named `macroname`, the name of the macro is
           provided to that argument.

    .. py:attribute:: discard

       If set to `True`, then the macro call is discarded, i.e., it is converted
       to an empty string.


    .. versionadded:: 2.0

       The class :py:class:`MacroTextSpec` was introduced in `pylatexenc
       2.0` to succeed to the previously named `MacroDef` class.
    """
    def __init__(self, macroname, simplify_repl=None, discard=None):
        super(MacroTextSpec, self).__init__()
        self.macroname = macroname
        self.discard = True if (discard is None) else discard
        self.simplify_repl = simplify_repl


class EnvironmentTextSpec(object):
    """
    A specification of how to obtain a textual representation of an environment.

    .. py:attribute:: environmentname

       The name of the environment

    .. py:attribute:: simplify_repl

       The replacement text of the environment.  This is either a string or a
       callable:

         - If `simplify_repl` is a string, this string is used as the text
           representation of this environment node.

           The string may contain a single '%s' replacement placeholder, in
           which the (processed) environment body will be substituted.

           Alternatively, the `simplify_repl` string may contain '%(<n>)s'
           (where `<n>` is an integer) to refer to the n-th argument after
           ``\begin{environment}`` (starting at '%(1)s').  The body of the
           environment has to be referred to with `%(body)s`.

           You cannot mix the two %-formatting styles.

         - If `simplify_repl` is a callable, it should accept the corresponding
           :py:class:`pylatexenc.latexwalker.LatexEnvironmentNode` as an
           argument.

           The callable will be inspected to see what other arguments it
           accepts.  If it accepts an argument named `l2tobj`, the
           :py:class:`LatexNodes2Text` instance is provided to that argument.
           If it accepts an argument named `environmentname`, the name of the
           environment is provided to that argument.

    .. py:attribute:: discard

       If set to `True`, then the full environment is discarded, i.e., it is
       converted to an empty string.


    .. versionadded:: 2.0

       The class :py:class:`EnvironmentTextSpec` was introduced in `pylatexenc
       2.0` to succeed to the previously named `EnvDef` class.
    """
    def __init__(self, environmentname, simplify_repl=None, discard=False):
        super(EnvironmentTextSpec, self).__init__()
        self.environmentname = environmentname
        self.simplify_repl = simplify_repl
        self.discard = discard


class SpecialsTextSpec(object):
    """
    A specification of how to obtain a textual representation of latex specials.

    .. py:attribute:: specials_chars

       The sequence of special LaTeX characters

    .. py:attribute:: simplify_repl

       The replacement text for the given latex specials.  This is either a
       string or a callable:

         - If `simplify_repl` is a string, this string is used as the text
           representation of this specials node.

           The string may contain a single '%s' replacement placeholder which
           will be replaced by the concatenated textual representation of all
           macro arguments.

           Alternatively, the string may contain '%(<n>)s' (where `<n>` is an
           integer) to refer to the n-th argument (starting at '%(1)s').  You
           cannot mix the two %-formatting styles.

         - If `simplify_repl` is a callable, it should accept the corresponding
           :py:class:`pylatexenc.latexwalker.LatexSpecialsNode` as an argument.

           The callable will be inspected to see what other arguments it
           accepts.  If it accepts an argument named `l2tobj`, the
           :py:class:`LatexNodes2Text` instance is provided to that argument.
           If it accepts an argument named `specials_chars`, the characters that
           were parsed this "latex specials" node are provided to that argument.

    .. versionadded:: 2.0

       Latex specials were introduced in `pylatexenc 2.0`.
    """
    def __init__(self, specials_chars, simplify_repl=None):
        super(SpecialsTextSpec, self).__init__()
        self.specials_chars = specials_chars
        self.simplify_repl = simplify_repl



def EnvDef(envname, simplify_repl=None, discard=False):
    r"""
    .. deprecated:: 2.0

       Instantiate a :py:class:`EnvironmentTextSpec` instead.

       Since `pylatexenc 2.0`, `EnvDef` is a function which returns a
       :py:class:`~pylatexenc.macrospec.EnvironmentTextSpec` instance.  In this
       way the earlier idiom ``EnvDef(...)`` still works in `pylatexenc 2`.
    """
    e = EnvironmentTextSpec(environmentname=envname, simplify_repl=simplify_repl,
                            discard=discard)
    e.envname = e.environmentname
    return e

def MacroDef(macname, simplify_repl=None, discard=None):
    r"""
    .. deprecated:: 2.0

       Instantiate a :py:class:`MacroTextSpec` instead.

       Since `pylatexenc 2.0`, `MacroDef` is a function which returns a
       :py:class:`~pylatexenc.macrospec.MacroTextSpec` instance.  In this way
       the earlier idiom ``MacroDef(...)`` still works in `pylatexenc 2`.
    """
    m = MacroTextSpec(macroname=macname, simplify_repl=simplify_repl, discard=discard)
    m.macname = m.macroname
    return m



#
# NOTE: while internally documented (but not in the public docs), these fmt_***
# functions should be considered internal API and should not be relied upon for
# the moment in production code.  I intend to change some things in how common
# rendering procedures (for equations, for non-textual content that probably
# requires a placeholder, etc.) by some other means such as by extending the
# latex context database object directly.
#

def fmt_equation_environment(envnode, l2tobj):
    r"""
    Can be used as callback for display equation environments.

    .. versionadded:: 2.0

       This function was introduced in `pylatexenc 2.0`.
    """

    return l2tobj.math_node_to_text(envnode)


def fmt_input_macro(macronode, l2tobj):
    r"""
    This function can be used as callback in :py:class:`MacroTextSpec` for
    ``\input`` or ``\include`` macros.  The `macronode` must be a macro node
    with a single argument.  If :py:meth:`set_tex_input_directory()` was called
    with a nonempty input directory in the :py:class:`LatexNodes2Text` object,
    then this method reads the contents of the file name in the macro argument
    according to the provided settings.  Otherwise, returns an empty string.

    .. versionadded:: 2.0

       This function was introduced in `pylatexenc 2.0`.
    """
    return l2tobj._input_node_simplify_repl(macronode)


def placeholder_node_formatter(placeholdertext, block=True):
    r"""
    This function returns a callable that can be used in
    :py:class:`MacroTextSpec`, :py:class:`EnvironmentTextSpec`, or
    :py:class:`SpecialsTextSpec` for latex nodes that do not have a good textual
    representation, providing as text replacement the simple placeholder text
    ``'< P L A C E H O L D E R   T E X T >'``.

    If `block=True` (the default), the placeholder text is typeset in an
    indented block on its own.  Otherwise, it is typeset inline.

    .. versionadded:: 2.0

       This function was introduced in `pylatexenc 2.0`.
    """
    return  lambda n, l2tobj, pht=placeholdertext: \
        _do_fmt_placeholder_node(pht, l2tobj, block=block)

def _do_fmt_placeholder_node(placeholdertext, l2tobj, block=True):
    # spaces added so that database indexing doesn't index the word "array" or
    # "pmatrix"
    txt = '< ' + " ".join(placeholdertext) + ' >'
    if block:
        return l2tobj._fmt_indented_block(txt, indent='    ')
    return ' ' + txt + ' '

def fmt_placeholder_node(node, l2tobj):
    r"""
    This function can be used as callable in :py:class:`MacroTextSpec`,
    :py:class:`EnvironmentTextSpec`, or :py:class:`SpecialsTextSpec` for latex
    nodes that do not have a good textual representation.  The text replacement
    is the placeholder text
    ``'< N A M E   O F   T H E   M A C R O   O R   E N V I R O N M E N T >'``.

    .. versionadded:: 2.0

       This function was introduced in `pylatexenc 2.0`.
    """

    for att in ('macroname', 'environmentname', 'specials_chars'):
        if hasattr(node, att):
            name = getattr(node, att)
            break
    else:
        name = '<unknown>'

    return _do_fmt_placeholder_node(name, l2tobj)


def fmt_matrix_environment_node(node, l2tobj):
    r"""
    This function can be used as a callable in :py:class:`EnvironmentTextSpec`
    for matrix-like environments like ``\begin{bmatrix}...\end{bmatrix}``.

    The contents is parsed by separating columns with ``&``'s and rows with
    ``\\``'s, and is rendered in the form ``[  a11  a12  ;  a21  a22  ]``.

    .. versionadded:: 2.8

       This function was introduced in `pylatexenc 2.8`.
    """

    class StateType:
        def __init__(self):
            self.matrix_rows = []
            self.buffer_this_column = []
            self.buffer_nodes = []

        def add_content(self, node):
            self.buffer_nodes.append(node)

        def new_column(self):
            if self.buffer_nodes:
                self.buffer_this_column.append(
                    l2tobj.nodelist_to_text(self.buffer_nodes) .strip()
                )
            self.buffer_nodes = []

        def new_row(self):
            self.new_column()
            self.matrix_rows.append( self.buffer_this_column )
            self.buffer_this_column = []
            
    state = StateType()

    # iterate the nodelist and find column and row separators
    for n in node.nodelist:
        if n.isNodeType(latexwalker.LatexSpecialsNode) and n.specials_chars == '&':
            # column separator
            state.new_column()
            continue
        if n.isNodeType(latexwalker.LatexMacroNode) and n.macroname == "\\":
            # row separator
            state.new_row()
            continue
        state.add_content(n)

    state.new_row() # finish the last row

    # now format the contents as array --
    max_char_width = max( ( len(x)  for row in state.matrix_rows  for x in row ) )
    matrix_contents = "; ".join( (
        " ".join( (
            x.rjust(max_char_width, ' ')
            for x in row
        ) )
        for row in state.matrix_rows
    ) )
    return "[ " + matrix_contents + " ]"

#
# see reference: https://unicode.org/charts/PDF/U1D400.pdf
#

_fmt_math_style_offsets = {
    'bold': (0x1D400, 0x1D41A),
    'italic': (0x1D434, 0x1D44E),
    'bold-italic': (0x1D468, 0x1D482),
    'script': (0x1D49C, 0x1D4B6),
    'bold-script': (0x1D4D0, 0x1D4EA),
    'fraktur': (0x1D504, 0x1D51E),
    'doublestruck': (0x1D538, 0x1D552),
    'bold-fraktur': (0x1D56C, 0x1D586),
    'sans': (0x1D5A0, 0x1D5BA),
    'sans-bold': (0x1D5D4, 0x1D5EE),
    'sans-italic': (0x1D608, 0x1D622),
    'sans-bold-italic': (0x1D63C, 0x1D656),
    'monospace': (0x1D670, 0x1D68A),
}
# account for "holes" in code point chart because some symbols have already
# been allocated earlier code points (see reference linked above)
_fmt_math_style_exceptions = {
    'italic': {
        ord('h'): chr(0x210E), # PLANK CONSTANT
    },
    'script': {
        ord('B'): chr(0x212C),
        ord('E'): chr(0x2130),
        ord('F'): chr(0x2131),
        ord('H'): chr(0x210B),
        ord('I'): chr(0x2110),
        ord('L'): chr(0x2112),
        ord('M'): chr(0x2133),
        ord('R'): chr(0x211B),
        ord('e'): chr(0x212F),
        ord('g'): chr(0x210A),
        ord('o'): chr(0x2134),
    },
    'fraktur': {
        ord('C'): chr(0x212D),
        ord('H'): chr(0x210C),
        ord('I'): chr(0x2111),
        ord('R'): chr(0x211C),
        ord('Z'): chr(0x2128),
    },
    'doublestruck': {
        ord('C'): chr(0x2102),
        ord('H'): chr(0x210D),
        ord('N'): chr(0x2115),
        ord('P'): chr(0x2119),
        ord('Q'): chr(0x211A),
        ord('R'): chr(0x211D),
        ord('Z'): chr(0x2124),
    },
}

_oA, _oZ, _oa, _oz = ord('A'), ord('Z'), ord('a'), ord('z')

def _fmt_math_style_char(c, style):
    oc = ord(c)
    z = _fmt_math_style_exceptions.get(style, {}).get(oc, None)
    if z is not None:
        return z

    offset_up, offset_lo = _fmt_math_style_offsets.get(style, (_oA, _oa,))

    if oc >= _oA and oc <= _oZ:
        return chr(offset_up + oc - _oA)
    if oc >= _oa and oc <= _oz:
        return chr(offset_lo + oc - _oa)

    # don't know how to handle this char
    return c

if sys.maxunicode < 0x10FFFF:
    # narrow python build, disable math alphabets.
    _fmt_math_style_char = lambda c, style: c



def fmt_math_text_style(text, style):
    r"""
    Return the text with letters replaced by unicode characters so that the
    style `style` is applied.  (We use the unicode math alphanumeric symbols,
    see `https://unicode.org/charts/PDF/U1D400.pdf`_.)

    The `style` must be one of 'bold', 'italic', 'bold-italic', 'script',
    'bold-script', 'fraktur', 'doublestruck', 'bold-fraktur', 'sans',
    'sans-bold', 'sans-italic', 'sans-bold-italic', or 'monospace'.

    The character `c` is essentially expected to be an ascii letter, and any
    other character will be returned unchanged.  (Possible exceptions might be
    implemented in the future, for instance to implement the double-struck
    one/identity operator ``\mathbbm{1}``.)
    """
    return "".join( (_fmt_math_style_char(c, style=style) for c in text) )






def get_default_latex_context_db():
    r"""
    Return a :py:class:`pylatexenc.macrospec.LatexContextDb` instance
    initialized with a collection of text replacements for known macros and
    environments.

    TODO: clean up and document categories.

    If you want to add your own definitions, you should use the
    :py:meth:`pylatexenc.macrospec.LatexContextDb.add_context_category()`
    method.  If you would like to override some definitions, use that method
    with the argument `prepend=True`.  See docs for
    :py:meth:`pylatexenc.macrospec.LatexContextDb.add_context_category()`.

    If there are too many macro/environment definitions, or if there are some
    irrelevant ones, you can always filter the returned database using
    :py:meth:`pylatexenc.macrospec.LatexContextDb.filter_context()`.

    .. versionadded:: 2.0

       The :py:class:`pylatexenc.macrospec.LatexContextDb` class as well as this
       method, were all introduced in `pylatexenc 2.0`.
    """
    db = macrospec.LatexContextDb()

    from ._defaultspecs import specs

    for cat, catspecs in specs:
        db.add_context_category(cat,
                                macros=catspecs['macros'],
                                environments=catspecs['environments'],
                                specials=catspecs['specials'])

    return db




default_macro_dict = _util.LazyDict(
    generate_dict_fn=lambda: dict([
        (m.macroname, m)
        for m in get_default_latex_context_db().iter_macro_specs()
    ])
)
r"""
.. deprecated:: 2.0

   Use :py:func:`get_default_latex_context_db()` instead, or create your own
   :py:class:`pylatexenc.macrospec.LatexContextDb` object.


Provide an access to the default macro text replacement specs for `latex2text`
in a form that is compatible with `pylatexenc 1.x`\ 's `default_macro_dict`
module-level dictionary.

This is implemented using a custom lazy mutable mapping, which behaves just like
a regular dictionary but that loads the data only once the dictionary is
accessed.  In this way the default latex specs into a python dictionary unless
they are actually queried or modified, and thus users of `pylatexenc 2.0` that
don't rely on the default macro/environment definitions shouldn't notice any
decrease in performance.
"""

default_env_dict = _util.LazyDict(
    generate_dict_fn=lambda: dict([
        (m.environmentname, m)
        for m in get_default_latex_context_db().iter_environment_specs()
    ])
)
r"""
.. deprecated:: 2.0

   Use :py:func:`get_default_latex_context_db()` instead, or create your own
   :py:class:`pylatexenc.macrospec.LatexContextDb` object.


Provide an access to the default environment text replacement specs for
`latex2text` in a form that is compatible with `pylatexenc 1.x`\ 's
`default_macro_dict` module-level dictionary.

This is implemented using a custom lazy mutable mapping, which behaves just like
a regular dictionary but that loads the data only once the dictionary is
accessed.  In this way the default latex specs into a python dictionary unless
they are actually queried or modified, and thus users of `pylatexenc 2.0` that
don't rely on the default macro/environment definitions shouldn't notice any
decrease in performance.
"""


default_text_replacements = ( )
r"""
.. deprecated:: 2.0

   Text replacements are deprecated since `pylatexenc 2.0` with the advent of
   "latex specials".  See :py:meth:`LatexNodes2Text.apply_text_replacements()`
   for a quick solution to keep existing code working if it uses custom text
   replacements.
"""


# ------------------------------------------------------------------------------

_strict_latex_spaces_predef = {
    'based-on-source': {
        'between-macro-and-chars': False,
        'between-latex-constructs': False,
        'after-comment': False,
        'in-equations': None,
    },
    'macros': {
        'between-macro-and-chars': True,
        'between-latex-constructs': True,
        'after-comment': False,
        'in-equations': 'based-on-source',
    },
    'except-in-equations': {
        'between-macro-and-chars': True,
        'between-latex-constructs': True,
        'after-comment': True,
        'in-equations': 'based-on-source',
    },
}


def _parse_strict_latex_spaces_dict(strict_latex_spaces):
    d = {
        'between-macro-and-chars': False,
        'between-latex-constructs': False,
        'after-comment': False,
        'in-equations': None,
    }
    if strict_latex_spaces is None:
        return d
    elif strict_latex_spaces is False:
        # "False" == the actual default for non-strict latex spaces == "macros"
        return _strict_latex_spaces_predef['macros']
    elif strict_latex_spaces is True:
        return dict([(k, True) for k in d.keys()])
    elif isinstance(strict_latex_spaces, dict):
        d.update(strict_latex_spaces)
        return d
    elif isinstance(strict_latex_spaces, basestring):
        if strict_latex_spaces == 'on':
            return _parse_strict_latex_spaces_dict(True)
        if strict_latex_spaces == 'off':
            return _parse_strict_latex_spaces_dict(False)
        if strict_latex_spaces not in _strict_latex_spaces_predef:
            raise ValueError("invalid value for strict_latex_spaces preset: {}"
                             .format(strict_latex_spaces))

        if strict_latex_spaces == 'default': # deprecated -- report this
            # compatibility with pylatexenc 1.x, but it is no longer the default!!
            _util.pylatexenc_deprecated_2(
                "The value 'default' for `strict_latex_spaces=` in LatexNodes2Text() "
                "is deprecated. The actual default changed to 'macros', and for "
                "backwards compatibility the obsolete value 'default' still refers to "
                "the earlier default which is now called 'based-on-source'.",
                stacklevel=4
            )
            strict_latex_spaces = 'based-on-source'

        return _strict_latex_spaces_predef[strict_latex_spaces]
    else:
        raise ValueError("Invalid value for strict_latex_spaces: {!r}"
                         .format(strict_latex_spaces))


class LatexNodes2Text(object):
    r"""
    Simplistic Latex-To-Text Converter.

    This class parses a nodes structure generated by the :py:mod:`latexwalker` module,
    and creates a text representation of the structure.

    It is capable of parsing ``\input`` directives safely, see
    :py:meth:`set_tex_input_directory()` and :py:meth:`read_input_file()`.  By default,
    ``\input`` and ``\include`` directives are ignored.

    Arguments to the constructor:

    - `latex_context_db` is a :py:class:`pylatexenc.macrospec.LatexContextDb`
      class storing a collection of rules for converting macros, environments,
      and other latex specials to text.  The `LatexContextDb` should contain
      specifications via :py:class:`MacroTextSpec`,
      :py:class:`EnvironmentTextSpec`, and :py:class:`SpecialsTextSpec` objects.

      The default latex context database can be obtained using
      :py:func:`get_default_latex_context_db()`.

    Additional keyword arguments are flags which may influence the behavior:

    - `math_mode='text'|'with-delimiters'|'verbatim'|'remove'`: Specify how to
      treat chunks of LaTeX code that correspond to math modes.  If 'text' (the
      default), then the math mode contents is incorporated as normal text.  If
      'with-delimiters', the content is incorporated as normal text but it is
      still included in the original math-mode delimiters, such as '$...$'.  If
      'verbatim', then the math mode chunk is kept verbatim, including the
      delimiters.  The value 'remove' means to remove the math mode sections
      entirely and not to produce any replacement text.

    - `keep_comments=True|False`: If set to `True`, then LaTeX comments are kept
      (including the percent-sign); otherwise they are discarded.  (By default
      this is `False`)

    - `fill_text`: If set to `True` or to a positive integer, then the
      whitespace of LaTeX char blocks is re-layed out to fill at the given
      number of characters or 80 by default.  The fill is by far not perfect,
      but the resulting text might be slightly more readable.

    - `strict_latex_spaces=True|False`: If set to `True`, then we follow closely
      LaTeX's handling of whitespace.  For instance, whitespace following a bare
      macro (i.e. without any delimiting characters like '{') is
      consumed/removed.  If set to `False` (the default), then some liberties
      are taken with respect to whitespace [hopefully making the result slightly
      more aesthetic, but this behavior is mostly there for historical reasons].

      You may also use one of the presets
      `strict_latex_spaces='based-on-source'|'macros'|'except-in-equations'`,
      which allow for finer control of how whitespace is handled:

        - The value 'based-on-source' is the option that is furthest from
          latex's behavior with spaces, and takes liberties in incuding spaces
          that are present in the source file in several situations where LaTeX
          would remove them, including after macros.  This is meant to be
          hopefully slightly more aesthetic.  However, this option might
          inadvertently break up words: For instance::

              Sk\l odowska

          would be replaced by::

             Skł odowska

        - The value 'macros' is the same as specifying
          `strict_latex_spaces=False`, and it is the default.  It will make
          macros and other sequences of LaTeX constructions obey LaTeX space
          rules, but will keep indentations after comments and keep more liberal
          whitespace rules in equations for a hopefully more aesthetic result.

        - The 'except-in-equations' preset goes as you would expect, setting
          strict latex spacing only outside of equation contexts.

      Finally, the argument `strict_latex_spaces` may also be set to a
      dictionary with keys 'between-macro-and-chars', 'after-comment',
      'between-latex-constructs', and 'in-equations', with individual values
      either `True` or `False`, dictating whitespace behavior in specific cases
      (`True` indicates strict latex behavior).  The value for 'in-equations'
      may even be another dictionary with the same keys to override values in
      equations.  A value of `False` for 'in-equation' has the same meaning as
      'macros'.

      .. versionchanged:: 2.0

         Since `pylatexenc 2.0`, the default value of `strict_latex_spaces` is
         'macros', and no longer 'based-on-source'.

      .. deprecated:: 2.0

         The value 'default' is also accepted, but it is no longer the default!
         It is an alias for 'based-on-source'

      .. versionchanged:: 2.6

         In `pylatexenc` versions 2.0–2.5, contrary to the documentation, the
         default value of `strict_latex_spaces` was actually still
         'based-on-source'.  This bug was fixed in version 2.6, so that now, the
         default setting is actually 'macros'.

    - `keep_braced_groups=True|False`: If set to `True`, then braces delimiting
      a TeX group ``{Like this}`` will be kept in the output, with the contents
      of the group converted to text as usual.  (By default this is `False`)

    - `keep_braced_groups_minlen=<int>`: If `keep_braced_groups` is set to
      `True`, then we keep braced groups only if their contents length (after
      conversion to text) is longer than the given value.  E.g., if
      `keep_braced_groups_minlen=2`, then ``{\'e}tonnant`` still goes to
      ``étonnant`` but ``{\'etonnant}``
      becomes ``{étonnant}``.

    .. versionadded: 1.4

       Added the `strict_latex_spaces`, `keep_braced_groups`, and
       `keep_braced_groups_minlen` flags

    .. versionadded: 2.0

       Added the `math_mode=` flag to replace the poorly designed
       `keep_inline_math=` flag;

       Added the `fill_text=` flag.

    Additionally, the following arguments are accepted for backwards compatibility:

    - `keep_inline_math=True|False`: Obsolete since `pylatexenc 2`.  If set to
      `True`, then this is the same as `math_mode='verbatim'`, and if set to
      `False`, this is the same as `math_mode='text'`.

      .. deprecated:: 2.0

         The `keep_inline_math=` option is deprecated because it had a weird
         behavior and was poorly implemented, especially given that a similarly
         named option in :py:class:`LatexWalker` had a different effect.  See
         issue :issue:`14`.

    - `text_replacements` this argument is ignored starting from `pylatexenc 2`.

      .. deprecated:: 2.0

         Text replacements are no longer made at the end of the text conversion.
         This feature is replaced by the concept of LaTeX specials---see, e.g.,
         :py:class:`pylatexenc.latexwalker.LatexSpecialsNode`.

         To keep existing code working, add a call to
         :py:meth:`apply_text_replacements()` immediately after
         :py:meth:`nodelist_to_text()` to achieve the same effect as in
         `pylatexenc 1.x`.  See :py:meth:`apply_text_replacements()`.

    - `env_dict`, `macro_dict`: Obsolete since `pylatexenc 2`.  If set, they are
      dictionaries of known environment and macro definitions.  They default to
      :py:data:`default_env_dict` and :py:data:`default_macro_dict`,
      respectively.

      .. deprecated:: 2.0

         You should now use the more powerful option `latex_context_db=`.  You
         cannot specify both `macro_list` (or `env_list`) and
         `latex_context_db`.
    """
    def __init__(self, latex_context=None, **flags):
        super(LatexNodes2Text, self).__init__()

        if latex_context is None:
            if 'macro_dict' in flags or 'env_dict' in flags:
                # LEGACY -- build a latex context using the given macro_dict
                _util.pylatexenc_deprecated_2(
                    "The `macro_dict=...` and `env_dict=...` options in LatexNodes2Text() are "
                    "obsolete since pylatexenc 2.  They will still work, but please consider "
                    "using instead the more versatile option `latex_context=...`."
                )

                macro_dict = flags.pop('macro_dict', [])
                env_dict = flags.pop('env_dict', [])

                latex_context = macrospec.LatexContextDb()
                latex_context.add_context_category('custom',
                                                   macros=macro_dict.values(),
                                                   environments=env_dict.values(),
                                                   specials=[])

            else:
                # default -- use default
                latex_context = get_default_latex_context_db()

        self.latex_context = latex_context

        self.tex_input_directory = None
        self.strict_input = True

        if 'keep_inline_math' in flags:
            if 'math_mode' in flags:
                raise TypeError("Cannot specify both math_mode= and keep_inline_math= "
                                "for LatexNodes2Text()")
            _util.pylatexenc_deprecated_2(
                "The keep_inline_math=... option in LatexNodes2Text() has been replaced by "
                "the math_mode=... option."
            )
            self.math_mode = 'verbatim' if flags.pop('keep_inline_math') else 'text'
        else:
            self.math_mode = flags.pop('math_mode', 'text')

        if self.math_mode not in ('text', 'with-delimiters', 'verbatim', 'remove'):
            raise ValueError("math_mode= option must be one of 'text', 'with-delimiters', "
                             "'verbatim', 'remove'")

        self.keep_comments = flags.pop('keep_comments', False)

        strict_latex_spaces = flags.pop('strict_latex_spaces', False)
        self.strict_latex_spaces = _parse_strict_latex_spaces_dict(strict_latex_spaces)

        self.keep_braced_groups = flags.pop('keep_braced_groups', False)
        self.keep_braced_groups_minlen = flags.pop('keep_braced_groups_minlen', 2)

        self.fill_text = flags.pop('fill_text', None)
        if not self.fill_text: # None, 0, False, or false-ish
            self.fill_text = None
        if self.fill_text is True: # exactly boolean true, not an int
            self.fill_text = 80

        if 'text_replacements' in flags:
            del flags['text_replacements']
            _util.pylatexenc_deprecated_2(
                "The text_replacements= argument is ignored since pylatexenc 2. "
                "To keep existing code working, add a call to "
                "`LatexNodes2Text.apply_text_replacements()`. "
                "New code should use \"latex specials\" instead."
            )

        if flags:
            # any flags left which we haven't recognized
            logger.warning("LatexNodes2Text(): Unknown flag(s) encountered: %r",
                           list(flags.keys()))


    def set_tex_input_directory(self, tex_input_directory, latex_walker_init_args=None,
                                strict_input=True):
        """
        Set where to look for input files when encountering the ``\\input`` or
        ``\\include`` macro.

        Alternatively, you may also override :py:meth:`read_input_file()` to
        implement a custom file lookup mechanism.

        The argument `tex_input_directory` is the directory relative to which to
        search for input files.

        If `strict_input` is set to `True`, then we always check that the
        referenced file lies within the subtree of `tex_input_directory`,
        prohibiting for instance hacks with '..' in filenames or using symbolic
        links to refer to files out of the directory tree.

        The argument `latex_walker_init_args` allows you to specify the parse
        flags passed to the constructor of
        :py:class:`pylatexenc.latexwalker.LatexWalker` when parsing the input
        file.
        """
        self.tex_input_directory = tex_input_directory
        self.latex_walker_init_args = latex_walker_init_args if latex_walker_init_args else {}
        self.strict_input = strict_input



    def read_input_file(self, fn):
        """
        This method may be overridden to implement a custom lookup mechanism when
        encountering ``\\input`` or ``\\include`` directives.

        The default implementation looks for a file of the given name relative
        to the directory set by :py:meth:`set_tex_input_directory()`.  If
        `strict_input=True` was set, we ensure strictly that the file resides in
        a subtree of the reference input directory (after canonicalizing the
        paths and resolving all symlinks).

        If `set_tex_input_directory()` was not called, or if it was called with
        a value of `None`, then no file system access is attempted an an empty
        string is returned.

        You may override this method to obtain the input data in however way you
        see fit.  In that case, a call to `set_tex_input_directory()` may not be
        needed as that function simply sets properties which are used by the
        default implementation of `read_input_file()`.

        This function accepts the referred filename as argument (the argument to
        the ``\\input`` macro), and should return a string with the file
        contents (or generate a warning or raise an error).
        """

        if self.tex_input_directory is None:
            return ''

        fnfull = os.path.realpath(os.path.join(self.tex_input_directory, fn))
        if self.strict_input:
            # make sure that the input file is strictly within dirfull, and
            # didn't escape with '../..' tricks or via symlinks.
            dirfull = os.path.realpath(self.tex_input_directory)
            if not fnfull.startswith(dirfull):
                logger.warning(
                    "Can't access path '%s' leading outside of mandated directory "
                    "[strict input mode]",
                    fn
                )
                return ''

        if not os.path.exists(fnfull) and os.path.exists(fnfull + '.tex'):
            fnfull = fnfull + '.tex'
        if not os.path.exists(fnfull) and os.path.exists(fnfull + '.latex'):
            fnfull = fnfull + '.latex'
        if not os.path.isfile(fnfull):
            logger.warning(u"Error, file doesn't exist: '%s'", fn)
            return ''

        logger.debug("Reading input file %r", fnfull)

        try:
            with open(fnfull) as f:
                return f.read()
        except IOError as e:
            logger.warning(u"Error, can't access '%s': %s", fn, e)
            return ''


    def _input_node_simplify_repl(self, n):
        #
        # recurse into files upon '\input{}'
        #

        if len(n.nodeargs) != 1:
            logger.warning(u"Expected exactly one argument for '\\input' ! Got = %r",
                           n.nodeargs)

        inputtex = self.read_input_file(self.nodelist_to_text([n.nodeargs[0]]).strip())

        if not inputtex:
            return ''

        return self.nodelist_to_text(
            latexwalker.LatexWalker(inputtex, **self.latex_walker_init_args)
            .get_latex_nodes()[0]
        )


    def latex_to_text(self, latex, **parse_flags):
        """
        Parses the given `latex` code and returns its textual representation.

        This is equivalent to constructing a
        :py:class:`pylatexenc.latexwalker.LatexWalker` with the given `latex`
        string, calling its method
        :py:meth:`~pylatexenc.latexwalker.LatexWalker.get_latex_nodes()`, and
        providing the outcome to :py:meth:`nodelist_to_text()`.

        The `parse_flags` are keyword arguments to provide to the
        :py:class:`pylatexenc.latexwalker.LatexWalker` constructor.
        """
        return self.nodelist_to_text(
            latexwalker.LatexWalker(latex, **parse_flags).get_latex_nodes()[0]
        )


    def nodelist_to_text(self, nodelist):
        """
        Extracts text from a node list. `nodelist` is a list of `latexwalker` nodes,
        typically returned by
        :py:meth:`pylatexenc.latexwalker.LatexWalker.get_latex_nodes()`.

        This function basically applies `node_to_text()` to each node and
        concatenates the results into one string.  (This is not quite actually
        the case, since we take some care as to where we add whitespace
        according to the class options.)
        """

        s = ''
        prev_node = None
        for node in nodelist:
            if self._is_bare_macro_node(prev_node) and \
               node.isNodeType(latexwalker.LatexCharsNode):

                if not self.strict_latex_spaces['between-macro-and-chars']:
                    # after a macro with absolutely no arguments, include
                    # post_space in output by default if there are other chars
                    # that follow.  This is for more breathing space (especially
                    # in equations(?)), and for compatibility with earlier
                    # versions of pylatexenc (<= 1.3).  This is NOT LaTeX'
                    # default behavior (see issue #11), so only do this if the
                    # corresponding `strict_latex_spaces=` flag is set.
                    s += prev_node.macro_post_space

            last_nl_pos = s.rfind('\n')
            if last_nl_pos != -1:
                textcol = len(s)-last_nl_pos-1
            else:
                textcol = len(s)

            s += self.node_to_text(node, textcol=textcol)

            prev_node = node

        return s

    def node_to_text(self, node, prev_node_hint=None, textcol=0):
        """
        Return the textual representation of the given `node`.

        If `prev_node_hint` is specified, then the current node is formatted
        suitably as following the node given in `prev_node_hint`.  This might
        affect how much space we keep/discard, etc.
        """
        if node is None:
            return ""

        # ### It doesn't look like we use prev_node_hint at all.  Eliminate at
        # ### some point?

        if node.isNodeType(latexwalker.LatexCharsNode):
            return self.chars_node_to_text(node, textcol=textcol)

        if node.isNodeType(latexwalker.LatexCommentNode):
            return self.comment_node_to_text(node)

        if node.isNodeType(latexwalker.LatexGroupNode):
            return self.group_node_to_text(node)

        if node.isNodeType(latexwalker.LatexMacroNode):
            return self.macro_node_to_text(node)

        if node.isNodeType(latexwalker.LatexEnvironmentNode):
            return self.environment_node_to_text(node)

        if node.isNodeType(latexwalker.LatexSpecialsNode):
            return self.specials_node_to_text(node)

        if node.isNodeType(latexwalker.LatexMathNode):
            return self.math_node_to_text(node)

        logger.warning("LatexNodes2Text.node_to_text(): Unknown node: %r", node)

        # discard anything else.
        return ""

    def chars_node_to_text(self, node, textcol=0):
        r"""
        Return the textual representation of the given `node` representing a block
        of simple latex text with no special characters or macros.  The `node`
        is :py:class:`~pylatexenc.latexwalker.LatexCharsNode`.
        """
        # Unless in strict latex spaces mode, ignore nodes consisting only
        # of empty chars, as this tends to produce too much space...  These
        # have been inserted by LatexWalker() in some occasions to keep
        # track of all relevant pre_space of tokens, such as between two
        # braced groups ("{one} {two}") or other such situations.
        content = node.chars
        if self.fill_text: # None or column width
            content = self.do_fill_text(content, textcol=textcol)
        if not self.strict_latex_spaces['between-latex-constructs'] \
           and len(content.strip()) == 0:
            return ""
        return content

    def comment_node_to_text(self, node):
        r"""
        Return the textual representation of the given `node` representing a latex
        comment.  The `node` is
        :py:class:`~pylatexenc.latexwalker.LatexCommentNode`.
        """
        if self.keep_comments:
            if self.strict_latex_spaces['after-comment']:
                nl = '\n'
                if node.comment_post_space == '':
                    # this happens if two newlines follow a comment---the
                    # comment_post_space is empty, and the \n\n is reported as a
                    # char node to notify that there is a new paragraph.
                    nl = ''
                return '%' + node.comment + nl
            else:
                # default spaces, i.e., keep what spaces were already there
                # after the comment
                return '%' + node.comment + node.comment_post_space
        else:
            if self.strict_latex_spaces['after-comment']:
                return ""
            else:
                # default spaces, i.e., keep what spaces were already there
                # after the comment.  This can be useful to preserve
                # e.g. indentation of the next line
                return node.comment_post_space


    def group_node_to_text(self, node):
        r"""
        Return the textual representation of the given `node` representing a latex
        group.  The `node` is
        :py:class:`~pylatexenc.latexwalker.LatexGroupNode`.
        """
        contents = self._groupnodecontents_to_text(node)
        if self.keep_braced_groups and len(contents) >= self.keep_braced_groups_minlen:
            return node.delimiters[0] + contents + node.delimiters[1]
        return contents

    def macro_node_to_text(self, node):
        r"""
        Return the textual representation of the given `node` representing a latex
        macro invocation.  The `node` is
        :py:class:`~pylatexenc.latexwalker.LatexMacroNode`.
        """
        # get macro behavior definition.
        macroname = node.macroname
        mac = self.latex_context.get_macro_spec(macroname)
        if mac is None:
            # default for unknown macros
            mac = MacroTextSpec('', discard=True)

        def get_macro_str_repl(node, macroname, mac):
            if mac.simplify_repl:
                return self.apply_simplify_repl(node, mac.simplify_repl,
                                                what=r"macro '\%s'"%(macroname))
            if mac.discard:
                return ""
            a = []
            if node.nodeargd and node.nodeargd.argnlist:
                a = node.nodeargd.argnlist
            return "".join([self._groupnodecontents_to_text(n) for n in a])

        macrostr = get_macro_str_repl(node, macroname, mac)
        return macrostr

    def environment_node_to_text(self, node):
        r"""
        Return the textual representation of the given `node` representing a full
        latex environment.  The `node` is
        :py:class:`~pylatexenc.latexwalker.LatexEnvironmentNode`.
        """
        # get environment behavior definition.
        environmentname = node.environmentname
        envdef = self.latex_context.get_environment_spec(environmentname)
        if envdef is None:
            # default for unknown environments
            envdef = EnvironmentTextSpec('', discard=False)

        if envdef.simplify_repl:
            return self.apply_simplify_repl(node, envdef.simplify_repl,
                                            what="environment '%s'"%(environmentname))
        if envdef.discard:
            return ""

        return self.nodelist_to_text(node.nodelist)

    def specials_node_to_text(self, node):
        r"""
        Return the textual representation of the given `node` representing special a
        latex character (or characters).  The `node` is
        :py:class:`~pylatexenc.latexwalker.LatexSpecialsNode`.
        """
        # get the specials text spec
        specials_chars = node.specials_chars
        sspec = self.latex_context.get_specials_spec(specials_chars)
        if sspec is None:
            # no corresponding spec, leave the special chars unchanged:
            return specials_chars

        def get_specials_str_repl(node, specials_chars, spec):
            if spec.simplify_repl:
                return self.apply_simplify_repl(node, spec.simplify_repl,
                                                what="specials '%s'"%(specials_chars))
            if spec.discard:
                return ""
            if node.nodeargd and node.nodeargd.argnlist:
                a = node.nodeargd.argnlist
            return "".join([self._groupnodecontents_to_text(n) for n in a])

        s = get_specials_str_repl(node, specials_chars, sspec)
        return s

    def math_node_to_text(self, node):
        r"""
        Return the textual representation of the given `node` representing a block
        of math mode latex.  The `node` is either a
        :py:class:`~pylatexenc.latexwalker.LatexMathNode` or a
        :py:class:`~pylatexenc.latexwalker.LatexEnvironmentNode`.

        This method is responsible for honoring the `math_mode=...` option
        provided to the constructor.
        """

        if self.math_mode == 'verbatim':
            if node.isNodeType(latexwalker.LatexEnvironmentNode) \
               or node.displaytype == 'display':
                return self._fmt_indented_block(node.latex_verbatim(), indent='')
            else:
                return node.latex_verbatim()

        elif self.math_mode == 'remove':
            return ''

        elif self.math_mode == 'with-delimiters':
            with _PushEquationContext(self):
                content = self.nodelist_to_text(node.nodelist).strip()
            if node.isNodeType(latexwalker.LatexMathNode):
                delims = node.delimiters
            else: # environment node
                delims = (r'\begin{%s}'%(node.environmentname),
                          r'\end{%s}'%(node.environmentname),)
            if node.isNodeType(latexwalker.LatexEnvironmentNode) \
               or node.displaytype == 'display':
                return delims[0] + self._fmt_indented_block(content, indent='') + delims[1]
            else:
                return delims[0] + content + delims[1]

        elif self.math_mode == 'text':
            with _PushEquationContext(self):
                content = self.nodelist_to_text(node.nodelist).strip()
            if node.isNodeType(latexwalker.LatexEnvironmentNode) \
               or node.displaytype == 'display':
                return self._fmt_indented_block(content)
            else:
                return content

        else:
            raise RuntimeError("unknown math_mode={} !".format(self.math_mode))


    def do_fill_text(self, text, textcol=0):
        # keep trailing whitespace to have whitespace between macros in text as
        # in "see \ref{...} and blah blah"
        head_ws = re.search(r'^\s*', text).group()
        head_par = '\n\n' if ('\n\n' in head_ws) else ''
        #head_nl = '\n' if (not head_par and '\n' in head_ws) else ''
        trail_ws = re.search(r'\s*$', text).group()
        trail_par = '\n\n' if ('\n\n' in trail_ws) else ''
        #trail_nl = '\n' if (not trail_par and '\n' in trail_ws) else ''
        text = text.strip()

        def fill_chunk(x, textcol):
            #head_ws = ' ' if textcol>0 and x[0:1].isspace() else ''
            #trail_ws = ' ' if x[-1:].isspace() else ''
            head_ws, trail_ws = '', ''
            x = x.strip()
            if textcol >= self.fill_text-4:
                return '\n' + textwrap.fill(x, self.fill_text) + trail_ws
            else:
                return head_ws + \
                    textwrap.fill(x, self.fill_text, initial_indent='X'*textcol)[textcol:] + \
                    trail_ws

        rawchunks = re.compile(r'\n{2,}').split(text)

        chunks = [
            thechunk
            for (j, thechunk) in (
                    ( j, fill_chunk(x, textcol if j==0 else 0) )
                    for j, x in enumerate(rawchunks)
            )
            if thechunk.strip()
        ]

        return head_par + (' ' if textcol>0 and head_ws and not head_par else '') + \
            "\n\n".join(chunks) + \
            (' ' if trail_ws and not trail_par else '') + trail_par

    def apply_simplify_repl(self, node, simplify_repl, what):
        r"""
        Utility to get the replacement text associated with a `node` for which we
        have a `simplify_repl` object (given by e.g. a MacroTextSpec or
        similar).

        The argument `what` is used in error messages.
        """
        if callable(simplify_repl):
            kwargs = {}
            fn_args = getfullargspec(simplify_repl)[0]
            if 'l2tobj' in fn_args:
                # callable accepts an argument named 'l2tobj', provide pointer to self
                kwargs['l2tobj'] = self
            if node.isNodeType(latexwalker.LatexEnvironmentNode) and \
               'environmentname' in fn_args:
                kwargs['environmentname'] = node.environmentname
            if node.isNodeType(latexwalker.LatexMacroNode) and \
               'macroname' in fn_args:
                kwargs['macroname'] = node.macroname
            if node.isNodeType(latexwalker.LatexSpecialsNode) and \
               'specials_chars' in fn_args:
                kwargs['specials_chars'] = node.specials_chars

            r = simplify_repl(node, **kwargs)
            if r:
                return r
            return '' # don't return None

        if '%' in simplify_repl and len(simplify_repl) != 1:
            # if simplify_repl contains a '%' sign then we will look for %-based
            # formatting placeholder(s), except if simplify_repl is the string
            # '%' itself (checked above with "len(simplify_repl)!=1") in which
            # case it is a literal replacement percent symbol.

            nodeargs = []
            if node.nodeargd and node.nodeargd.argnlist:
                nodeargs = node.nodeargd.argnlist

            has_percent_s = re.search('(^|[^%])(%%)*%s', simplify_repl)

            if node.isNodeType(latexwalker.LatexEnvironmentNode):
                if has_percent_s:
                    x = (self.nodelist_to_text(node.nodelist), )
                else:
                    x = dict(
                        (str(1+j),val) for j, val in enumerate(
                            self._groupnodecontents_to_text(nn) for nn in nodeargs
                        )
                    )
                    x.update(body=self.nodelist_to_text(node.nodelist))
            elif has_percent_s:
                x = tuple([self._groupnodecontents_to_text(nn)
                           for nn in nodeargs])
            else:
                x = dict(
                    (str(1+j),val) for j, val in enumerate(
                        self._groupnodecontents_to_text(nn) for nn in nodeargs
                    )
                )

            try:
                return simplify_repl % x
            except (TypeError, ValueError):
                logger.warning(
                    "WARNING: Error in configuration: {} failed its substitution!"
                    .format(what)
                )
                return simplify_repl # too bad, keep the percent signs as they are...
        return simplify_repl

    def _fmt_indented_block(self, contents, indent=' '*4):
        block = ("\n"+indent + contents.replace("\n", "\n"+indent) + "\n")
        if self.fill_text:
            # additional newlines because neighboring text gets trimmed
            block = '\n'+block+'\n'
        return block


    def _is_bare_macro_node(self, node):
        return (node is not None and
                node.isNodeType(latexwalker.LatexMacroNode) and
                node.nodeoptarg is None and
                len(node.nodeargs) == 0)

    def _groupnodecontents_to_text(self, groupnode):
        if groupnode is None:
            return ''
        if not groupnode.isNodeType(latexwalker.LatexGroupNode):
            return self.node_to_text(groupnode)
        return self.nodelist_to_text(groupnode.nodelist)

    def node_arg_to_text(self, node, k):
        r"""
        Return the textual representation of the `k`\ -th argument of the given
        `node`.  This might be useful for substitution lambdas in macro and
        environment specs.
        """
        if node.nodeargd and node.nodeargd.argnlist:
            return self._groupnodecontents_to_text(node.nodeargd.argnlist[k])
        return ''

    def apply_text_replacements(self, s, text_replacements):
        r"""
        Convenience function for code that used `text_replacements=` in `pylatexenc
        1.x`.

        If you used custom `text_replacements=` in `pylatexenc 1.x` then you
        will have to change::

          # pylatexenc 1.x with text_replacements
          text_replacements = ...
          l2t = LatexNodes2Text(..., text_replacements=text_replacements)
          text = l2t.nodelist_to_text(...)

        to::

          # pylatexenc 2 text_replacements compatibility code
          text_replacements = ...
          l2t = LatexNodes2Text(...)
          temp = l2t.nodelist_to_text(...)
          text = l2t.apply_text_replacements(temp, text_replacements)

        as a quick fix.  It is recommended however to treat text replacements
        instead as "latex specials".  (Otherwise the brutal text replacements
        might act on text generated from macros and environments and give
        unwanted results.)  See :py:class:`pylatexenc.macrospec.SpecialsSpec`
        and :py:class:`SpecialsTextSpec`.

        .. deprecated:: 2.0

           The `apply_text_replacements()` method was introduced in `pylatexenc
           2.0` as a deprecated method.  You can use it as a quick fix to make
           existing code run as it did in `pylatexenc 1.x`.  Its use is however
           not recommended for new code.  You should use "latex specials"
           instead for characters that have special LaTeX meaning.
        """

        # perform suitable replacements
        for pattern, replacement in text_replacements:
            if hasattr(pattern, 'sub'):
                s = pattern.sub(replacement, s)
            else:
                s = s.replace(pattern, replacement)

        return s





class _PushEquationContext(latexwalker._PushPropOverride):
    def __init__(self, l2t):

        new_strict_latex_spaces = None
        if l2t.strict_latex_spaces['in-equations'] is not None:
            new_strict_latex_spaces = _parse_strict_latex_spaces_dict(
                l2t.strict_latex_spaces['in-equations']
            )

        super(_PushEquationContext, self).__init__(l2t, 'strict_latex_spaces',
                                                   new_strict_latex_spaces)








# ------------------------------------------------------------------------------



def latex2text(content, tolerant_parsing=False, keep_inline_math=False,
               keep_comments=False):
    """
    Heuristic conversion of LaTeX content `content` to unicode text.

    .. deprecated:: 1.0
       Please use :py:class:`LatexNodes2Text` instead.
    """

    _util.pylatexenc_deprecated_ver(
        "1.0",
        "The module-level function `pylatexenc.latex2text.latex2text()` is deprecated "
        "in favor of the `pylatexenc.latex2text.LatexNodes2Text` class."
    )

    (nodelist, tpos, tlen) = latexwalker.get_latex_nodes(
        content,
        keep_inline_math=keep_inline_math,
        tolerant_parsing=tolerant_parsing)

    return latexnodes2text(nodelist,
                           keep_inline_math=keep_inline_math,
                           keep_comments=keep_comments)


def latexnodes2text(nodelist, keep_inline_math=False, keep_comments=False):
    """
    Extracts text from a node list. `nodelist` is a list of nodes as returned by
    :py:func:`pylatexenc.latexwalker.get_latex_nodes()`.

    .. deprecated:: 1.0
       Please use :py:class:`LatexNodes2Text` instead.
    """

    _util.pylatexenc_deprecated_ver(
        "1.0",
        "The module-level function `pylatexenc.latex2text.latexnodes2text()` is "
        "deprecated in favor of the `pylatexenc.latex2text.LatexNodes2Text` class."
    )

    return LatexNodes2Text(
        keep_inline_math=keep_inline_math,
        keep_comments=keep_comments
    ).nodelist_to_text(nodelist)
