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


from __future__ import print_function, unicode_literals #, absolute_import

# Internal module. May change without notice.

import unicodedata
import datetime
import sys

if sys.version_info.major >= 3:
    def unicode(string): return string
    basestring = str
else:
    pass



from ..latex2text import (
    MacroTextSpec, EnvironmentTextSpec, SpecialsTextSpec,
    fmt_equation_environment, #fmt_placeholder_node,
    placeholder_node_formatter,
    fmt_matrix_environment_node, fmt_input_macro, fmt_math_text_style
)


def _format_uebung(n, l2tobj):
    s = '\n' + l2tobj.nodelist_to_text([n.nodeargs[0]]) + '\n'
    optarg = n.nodeargs[1]
    if optarg is not None:
        s += '[{}]\n'.format(l2tobj.nodelist_to_text([optarg]))
    return s

def _format_maketitle(title, author, date):
    s = title + '\n'
    s += '    ' + author + '\n'
    s += '    ' + date + '\n'
    s += '='*max(len(title), 4+len(author), 4+len(date)) + '\n\n'
    return s

def _latex_today():
    return '{dt:%B} {dt.day}, {dt.year}'.format(dt=datetime.datetime.now())


def _mathxx_formatter(style):
    def formatter(node, l2tobj, style=style):
        arg_text = l2tobj.node_arg_to_text(node, 0)
        return fmt_math_text_style(arg_text, style)

    return formatter



# construct the specs structure, more than the just the following definition


# ==============================================================================



_latex_specs_placeholders = {
    'environments': [
#  --- as of pylatexenc 2.8, these are now approximated ---
#        EnvironmentTextSpec('array', simplify_repl=fmt_placeholder_node),
#        EnvironmentTextSpec('pmatrix', simplify_repl=fmt_placeholder_node),
#        EnvironmentTextSpec('bmatrix', simplify_repl=fmt_placeholder_node),
#        EnvironmentTextSpec('smallmatrix', simplify_repl=fmt_placeholder_node),
#        EnvironmentTextSpec('psmallmatrix', simplify_repl=fmt_placeholder_node),
#        EnvironmentTextSpec('bsmallmatrix', simplify_repl=fmt_placeholder_node),
    ],
    'specials': [
    ],
    'macros': [
    ] + [ MacroTextSpec(x, simplify_repl=y) for x, y in (

        ('includegraphics', placeholder_node_formatter('graphics')),

        ('ref', '<ref>'),
        ('autoref', '<ref>'),
        ('cref', '<ref>'),
        ('Cref', '<Ref>'),
        ('eqref', '(<ref>)'),

        ('cite', '<cit.>'),
        ('citet', '<cit.>'),
        ('citep', '<cit.>'),
    )],
}

_latex_specs_approximations = {
    'environments': [
        EnvironmentTextSpec('center', simplify_repl='\n%s\n'),
        EnvironmentTextSpec('flushleft', simplify_repl='\n%s\n'),
        EnvironmentTextSpec('flushright', simplify_repl='\n%s\n'),

        EnvironmentTextSpec('exenumerate', discard=False),
        EnvironmentTextSpec('enumerate', discard=False),
        EnvironmentTextSpec('list', discard=False),
        EnvironmentTextSpec('itemize', discard=False),
        EnvironmentTextSpec('subequations', discard=False),
        EnvironmentTextSpec('figure', discard=False),
        EnvironmentTextSpec('table', discard=False),

        EnvironmentTextSpec('array', simplify_repl=fmt_matrix_environment_node),
        EnvironmentTextSpec('pmatrix', simplify_repl=fmt_matrix_environment_node),
        EnvironmentTextSpec('bmatrix', simplify_repl=fmt_matrix_environment_node),
        EnvironmentTextSpec('smallmatrix', simplify_repl=fmt_matrix_environment_node),
        EnvironmentTextSpec('psmallmatrix', simplify_repl=fmt_matrix_environment_node),
        EnvironmentTextSpec('bsmallmatrix', simplify_repl=fmt_matrix_environment_node),

        #
        # math environments used to be categorized as 'placeholders' in
        # pylatexenc <= 2.9, but I think it's more accurate to have them in
        # 'approximations'.
        #
        EnvironmentTextSpec('equation', simplify_repl=fmt_equation_environment),
        # note {equation*} is actually defined by amsmath
        EnvironmentTextSpec('equation*', simplify_repl=fmt_equation_environment),
        EnvironmentTextSpec('eqnarray', simplify_repl=fmt_equation_environment),
        EnvironmentTextSpec('eqnarray*', simplify_repl=fmt_equation_environment),
        #
        EnvironmentTextSpec('align', simplify_repl=fmt_equation_environment),
        EnvironmentTextSpec('multline', simplify_repl=fmt_equation_environment),
        EnvironmentTextSpec('gather', simplify_repl=fmt_equation_environment),
        EnvironmentTextSpec('align*', simplify_repl=fmt_equation_environment),
        EnvironmentTextSpec('multline*', simplify_repl=fmt_equation_environment),
        EnvironmentTextSpec('gather*', simplify_repl=fmt_equation_environment),
        #
        # breqn math
        EnvironmentTextSpec('dmath', simplify_repl=fmt_equation_environment),
        EnvironmentTextSpec('dmath*', simplify_repl=fmt_equation_environment),
    ],
    'specials': [
        SpecialsTextSpec('&', '   '), # ignore tabular alignments, just add a little space
    ],
    'macros': [
        # NOTE: macro will only be assigned arguments if they are explicitly
        #       defined as accepting arguments in the `LatexWalker` (see
        #       `macrospec` module).

        MacroTextSpec('emph', discard=False),
        MacroTextSpec('textrm', discard=False),
        MacroTextSpec('textit', discard=False),
        MacroTextSpec('textbf', discard=False),
        MacroTextSpec('textsc', discard=False),
        MacroTextSpec('textsl', discard=False),
        MacroTextSpec('text', discard=False),

    ] + [ MacroTextSpec(x, simplify_repl=y) for x, y in (

        ('title', lambda n, l2tobj: \
         setattr(l2tobj, '_doc_title', l2tobj.nodelist_to_text(n.nodeargd.argnlist[0:1]))),
        ('author', lambda n, l2tobj: \
         setattr(l2tobj, '_doc_author', l2tobj.nodelist_to_text(n.nodeargd.argnlist[0:1]))),
        ('date', lambda n, l2tobj: \
         setattr(l2tobj, '_doc_date', l2tobj.nodelist_to_text(n.nodeargd.argnlist[0:1]))),
        ('maketitle', lambda n, l2tobj: \
         _format_maketitle(getattr(l2tobj, '_doc_title', r'[NO \title GIVEN]'),
                           getattr(l2tobj, '_doc_author', r'[NO \author GIVEN]'),
                           getattr(l2tobj, '_doc_date', _latex_today()))),

        ('url', '<%s>'),
        ('item',
         lambda r, l2tobj: '\n  '+(
             l2tobj.nodelist_to_text([r.nodeoptarg]) if r.nodeoptarg else '* '
         )
        ) ,
        ('footnote', '[%(2)s]'), # \footnote[optional mark]{footnote text}
        ('href', lambda n, l2tobj:  \
         '{} <{}>'.format(l2tobj.nodelist_to_text([n.nodeargd.argnlist[1]]), 
                          l2tobj.nodelist_to_text([n.nodeargd.argnlist[0]]))),

        ('part',
         lambda n, l2tobj: u'\n\nPART: {}\n'.format(
             l2tobj.node_arg_to_text(n, 2).upper())),
        ('chapter',
         lambda n, l2tobj: u'\n\nCHAPTER: {}\n'.format(
             l2tobj.node_arg_to_text(n, 2).upper())),
        ('section',
         lambda n, l2tobj: u'\n\n\N{SECTION SIGN} {}\n'.format(
             l2tobj.node_arg_to_text(n, 2).upper())),
        ('subsection',
         lambda n, l2tobj: u'\n\n \N{SECTION SIGN}.\N{SECTION SIGN} {}\n'.format(
             l2tobj.node_arg_to_text(n, 2))),
        ('subsubsection',
         lambda n, l2tobj: \
             u'\n\n  \N{SECTION SIGN}.\N{SECTION SIGN}.\N{SECTION SIGN} {}\n'.format(
                 l2tobj.node_arg_to_text(n, 2))),
        ('paragraph',
         lambda n, l2tobj: u'\n\n  {}\n'.format(l2tobj.node_arg_to_text(n, 2))),
        ('subparagraph',
         lambda n, l2tobj: u'\n\n    {}\n'.format(
             l2tobj.node_arg_to_text(n, 2))),

        ('textcolor', '%(3)s'),
        ('colorbox', '%(3)s'),
        ('fcolorbox', '%(5)s'),

        ('hspace', ''),
        ('vspace', '\n'),

        # \\ is treated as an "approximation" because a good text renderer would
        # have to actually note that this is a end-of-line marker which is not
        # to be confused with other newlines in the paragraph (which can be
        # reflowed)
        ("\\", '\n'),

        ('frac', '%s/%s'),
        ('nicefrac', '%s/%s'),
        ('textfrac', '%s/%s'),

        ('overline', '%s'),
        ('underline', '%s'),
        ('widehat', '%s'),
        ('widetilde', '%s'),
        ('wideparen', '%s'),
        ('overleftarrow', '%s'),
        ('overrightarrow', '%s'),
        ('overleftrightarrow', '%s'),
        ('underleftarrow', '%s'),
        ('underrightarrow', '%s'),
        ('underleftrightarrow', '%s'),
        ('overbrace', '%s'),
        ('underbrace', '%s'),
        ('overgroup', '%s'),
        ('undergroup', '%s'),
        ('overbracket', '%s'),
        ('underbracket', '%s'),
        ('overlinesegment', '%s'),
        ('underlinesegment', '%s'),
        ('overleftharpoon', '%s'),
        ('overrightharpoon', '%s'),

    )],
}

_latex_specs_base = {
    
    'environments': [
    ],
    'specials': [
    ],

    'macros': [
        MacroTextSpec('mathrm', discard=False),
        MacroTextSpec('mathbf', simplify_repl=_mathxx_formatter('bold')),
        MacroTextSpec('mathit', simplify_repl=_mathxx_formatter('italic')),
        MacroTextSpec('mathsf', simplify_repl=_mathxx_formatter('sans')),
        MacroTextSpec('mathbb', simplify_repl=_mathxx_formatter('doublestruck')),
        MacroTextSpec('mathtt', simplify_repl=_mathxx_formatter('monospace')),
        MacroTextSpec('mathcal', simplify_repl=_mathxx_formatter('script')),
        MacroTextSpec('mathscr', simplify_repl=_mathxx_formatter('script')),
        MacroTextSpec('mathfrak', simplify_repl=_mathxx_formatter('fraktur')),

        MacroTextSpec('input', simplify_repl=fmt_input_macro),
        MacroTextSpec('include', simplify_repl=fmt_input_macro),

    ] + [ MacroTextSpec(x, simplify_repl=y) for x, y in (

        ('today', _latex_today()),

        # use second argument:
        ('texorpdfstring', lambda node, l2tobj: l2tobj.nodelist_to_text(node.nodeargs[1:2])),

        ('oe', u'\u0153'),
        ('OE', u'\u0152'),
        ('ae', u'\u00e6'),
        ('AE', u'\u00c6'),
        ('aa', u'\u00e5'), # a norvegien/nordique
        ('AA', u'\u00c5'), # A norvegien/nordique
        ('o', u'\u00f8'), # o norvegien/nordique
        ('O', u'\u00d8'), # O norvegien/nordique
        ('ss', u'\u00df'), # s-z allemand
        ('L', u"\N{LATIN CAPITAL LETTER L WITH STROKE}"),
        ('l', u"\N{LATIN SMALL LETTER L WITH STROKE}"),
        ('i', u"\N{LATIN SMALL LETTER DOTLESS I}"),
        ('j', u"\N{LATIN SMALL LETTER DOTLESS J}"),

        ("~", "~" ),
        ("&", "&" ),
        ("$", "$" ),
        ("{", "{" ),
        ("}", "}" ),
        ("%", lambda arg: "%" ), # careful: % is formatting substitution symbol...
        ("#", "#" ),
        ("_", "_" ),

        ("textquoteleft", u"\N{LEFT SINGLE QUOTATION MARK}"),
        ("textquoteright", u"\N{RIGHT SINGLE QUOTATION MARK}"),
        ("textquotedblright", u"\N{RIGHT DOUBLE QUOTATION MARK}"),
        ("textquotedblleft", u"\N{LEFT DOUBLE QUOTATION MARK}"),
        ("textendash", u"\N{EN DASH}"),
        ("textemdash", u"\N{EM DASH}"),

        ('textpm', u"\N{PLUS-MINUS SIGN}"),
        ('textmp', u"\N{MINUS-OR-PLUS SIGN}"),

        ("texteuro", u"\N{EURO SIGN}"),

        ("backslash", "\\"),
        ("textbackslash", "\\"),

        # math stuff

        ("hbar", u"\N{LATIN SMALL LETTER H WITH STROKE}"),
        ("ell", u"\N{SCRIPT SMALL L}"),

        ('forall', u"\N{FOR ALL}"),
        ('complement', u"\N{COMPLEMENT}"),
        ('partial', u"\N{PARTIAL DIFFERENTIAL}"),
        ('exists', u"\N{THERE EXISTS}"),
        ('nexists', u"\N{THERE DOES NOT EXIST}"),
        ('varnothing', u"\N{EMPTY SET}"),
        ('emptyset', u"\N{EMPTY SET}"),
        ('aleph', u"\N{ALEF SYMBOL}"),
        # increment?
        ('nabla', u"\N{NABLA}"),
        #
        ('in', u"\N{ELEMENT OF}"),
        ('notin', u"\N{NOT AN ELEMENT OF}"),
        ('ni', u"\N{CONTAINS AS MEMBER}"),
        ('prod', u'\N{N-ARY PRODUCT}'),
        ('coprod', u'\N{N-ARY COPRODUCT}'),
        ('sum', u'\N{N-ARY SUMMATION}'),
        ('setminus', u'\N{SET MINUS}'),
        ('smallsetminus', u'\N{SET MINUS}'),
        ('ast', u'\N{ASTERISK OPERATOR}'),
        ('circ', u'\N{RING OPERATOR}'),
        ('bullet', u'\N{BULLET OPERATOR}'),
        ('sqrt', u'\N{SQUARE ROOT}(%(2)s)'),
        ('propto', u'\N{PROPORTIONAL TO}'),
        ('infty', u'\N{INFINITY}'),
        ('parallel', u'\N{PARALLEL TO}'),
        ('nparallel', u'\N{NOT PARALLEL TO}'),
        ('wedge', u"\N{LOGICAL AND}"),
        ('vee', u"\N{LOGICAL OR}"),
        ('cap', u'\N{INTERSECTION}'),
        ('cup', u'\N{UNION}'),
        ('int', u'\N{INTEGRAL}'),
        ('iint', u'\N{DOUBLE INTEGRAL}'),
        ('iiint', u'\N{TRIPLE INTEGRAL}'),
        ('oint', u'\N{CONTOUR INTEGRAL}'),

        ('sim', u'\N{TILDE OPERATOR}'),
        ('backsim', u'\N{REVERSED TILDE}'),
        ('simeq', u'\N{ASYMPTOTICALLY EQUAL TO}'),
        ('approx', u'\N{ALMOST EQUAL TO}'),
        ('neq', u'\N{NOT EQUAL TO}'),
        ('equiv', u'\N{IDENTICAL TO}'),
        ('le', u'\N{LESS-THAN OR EQUAL TO}'),
        ('ge', u'\N{GREATER-THAN OR EQUAL TO}'),
        ('leq', u'\N{LESS-THAN OR EQUAL TO}'),
        ('geq', u'\N{GREATER-THAN OR EQUAL TO}'),
        ('leqslant', u'\N{LESS-THAN OR SLANTED EQUAL TO}'),
        ('geqslant', u'\N{GREATER-THAN OR SLANTED EQUAL TO}'),
        ('leqq', u'\N{LESS-THAN OVER EQUAL TO}'),
        ('geqq', u'\N{GREATER-THAN OVER EQUAL TO}'),
        ('lneqq', u'\N{LESS-THAN BUT NOT EQUAL TO}'),
        ('gneqq', u'\N{GREATER-THAN BUT NOT EQUAL TO}'),
        ('ll', u'\N{MUCH LESS-THAN}'),
        ('gg', u'\N{MUCH GREATER-THAN}'),
        ('nless', u'\N{NOT LESS-THAN}'),
        ('ngtr', u'\N{NOT GREATER-THAN}'),
        ('nleq', u'\N{NEITHER LESS-THAN NOR EQUAL TO}'),
        ('ngeq', u'\N{NEITHER GREATER-THAN NOR EQUAL TO}'),
        ('lesssim', u'\N{LESS-THAN OR EQUIVALENT TO}'),
        ('gtrsim', u'\N{GREATER-THAN OR EQUIVALENT TO}'),
        ('lessgtr', u'\N{LESS-THAN OR GREATER-THAN}'),
        ('gtrless', u'\N{GREATER-THAN OR LESS-THAN}'),
        ('prec', u'\N{PRECEDES}'),
        ('succ', u'\N{SUCCEEDS}'),
        ('preceq', u'\N{PRECEDES OR EQUAL TO}'),
        ('succeq', u'\N{SUCCEEDS OR EQUAL TO}'),
        ('precsim', u'\N{PRECEDES OR EQUIVALENT TO}'),
        ('succsim', u'\N{SUCCEEDS OR EQUIVALENT TO}'),
        ('nprec', u'\N{DOES NOT PRECEDE}'),
        ('nsucc', u'\N{DOES NOT SUCCEED}'),
        ('subset', u'\N{SUBSET OF}'),
        ('supset', u'\N{SUPERSET OF}'),
        ('subseteq', u'\N{SUBSET OF OR EQUAL TO}'),
        ('supseteq', u'\N{SUPERSET OF OR EQUAL TO}'),
        ('nsubseteq', u'\N{NEITHER A SUBSET OF NOR EQUAL TO}'),
        ('nsupseteq', u'\N{NEITHER A SUPERSET OF NOR EQUAL TO}'),
        ('subsetneq', u'\N{SUBSET OF WITH NOT EQUAL TO}'),
        ('supsetneq', u'\N{SUPERSET OF WITH NOT EQUAL TO}'),

        ('cdot', u'\N{MIDDLE DOT}'),
        ('times', u'\N{MULTIPLICATION SIGN}'),
        ('otimes', u'\N{CIRCLED TIMES}'),
        ('oplus', u'\N{CIRCLED PLUS}'),
        ('bigotimes', u'\N{CIRCLED TIMES}'),
        ('bigoplus', u'\N{CIRCLED PLUS}'),

        ('cos', 'cos'),
        ('sin', 'sin'),
        ('tan', 'tan'),
        ('arccos', 'arccos'),
        ('arcsin', 'arcsin'),
        ('arctan', 'arctan'),
        ('cosh', 'cosh'),
        ('sinh', 'sinh'),
        ('tanh', 'tanh'),
        ('arccosh', 'arccosh'),
        ('arcsinh', 'arcsinh'),
        ('arctanh', 'arctanh'),
        
        ('ln', 'ln'),
        ('log', 'log'),
        ('exp', 'exp'),

        ('max', 'max'),
        ('min', 'min'),
        ('sup', 'sup'),
        ('inf', 'inf'),
        ('lim', 'lim'),
        ('limsup', 'lim sup'),
        ('liminf', 'lim inf'),

        ('prime', "'"),
        ('dag', u"\N{DAGGER}"),
        ('dagger', u"\N{DAGGER}"),
        ('pm', u"\N{PLUS-MINUS SIGN}"),
        ('mp', u"\N{MINUS-OR-PLUS SIGN}"),

        (',', u" "),
        (';', u" "),
        (':', u" "),
        (' ', u" "),
        ('!', u""), # sorry, no negative space in ascii
        ('quad', u"  "),
        ('qquad', u"    "),

        ('ldots', u"\N{HORIZONTAL ELLIPSIS}"),
        ('cdots', u"\N{MIDLINE HORIZONTAL ELLIPSIS}"),
        ('ddots', u"\N{DOWN RIGHT DIAGONAL ELLIPSIS}"),
        ('iddots', u"\N{UP RIGHT DIAGONAL ELLIPSIS}"),
        ('vdots', u"\N{VERTICAL ELLIPSIS}"),

        ('dots', u"\N{HORIZONTAL ELLIPSIS}"),
        ('dotsc', u"\N{HORIZONTAL ELLIPSIS}"),
        ('dotsb', u"\N{HORIZONTAL ELLIPSIS}"),
        ('dotsm', u"\N{HORIZONTAL ELLIPSIS}"),
        ('dotsi', u"\N{HORIZONTAL ELLIPSIS}"),
        ('dotso', u"\N{HORIZONTAL ELLIPSIS}"),

        ('langle', u'\N{MATHEMATICAL LEFT ANGLE BRACKET}'),
        ('rangle', u'\N{MATHEMATICAL RIGHT ANGLE BRACKET}'),
        ('lvert', u'|'),
        ('rvert', u'|'),
        ('vert', u'|'),
        ('lVert', u'\N{DOUBLE VERTICAL LINE}'),
        ('rVert', u'\N{DOUBLE VERTICAL LINE}'),
        ('Vert', u'\N{DOUBLE VERTICAL LINE}'),
        ('mid', u'|'),
        ('nmid', u'\N{DOES NOT DIVIDE}'),

        ('ket', u'|%s\N{MATHEMATICAL RIGHT ANGLE BRACKET}'),
        ('bra', u'\N{MATHEMATICAL LEFT ANGLE BRACKET}%s|'),
        ('braket',
         u'\N{MATHEMATICAL LEFT ANGLE BRACKET}%s|%s\N{MATHEMATICAL RIGHT ANGLE BRACKET}'),
        ('ketbra',
         u'|%s\N{MATHEMATICAL RIGHT ANGLE BRACKET}\N{MATHEMATICAL LEFT ANGLE BRACKET}%s|'),
        ('uparrow', u'\N{UPWARDS ARROW}'),
        ('downarrow', u'\N{DOWNWARDS ARROW}'),
        ('rightarrow', u'\N{RIGHTWARDS ARROW}'),
        ('to', u'\N{RIGHTWARDS ARROW}'),
        ('leftarrow', u'\N{LEFTWARDS ARROW}'),
        ('longrightarrow', u'\N{LONG RIGHTWARDS ARROW}'),
        ('longleftarrow', u'\N{LONG LEFTWARDS ARROW}'),
    )]
}


# ==============================================================================

advanced_symbols_macros = [
    # Rules from latexencode defaults 'defaults'
    MacroTextSpec('textasciicircum', u'\N{CIRCUMFLEX ACCENT}'), # ‘^’
    MacroTextSpec('textasciitilde', u'\N{TILDE}'), # ‘~’
    MacroTextSpec('textexclamdown', u'\N{INVERTED EXCLAMATION MARK}'), # ‘¡’
    MacroTextSpec('textcent', u'\N{CENT SIGN}'), # ‘¢’
    MacroTextSpec('textsterling', u'\N{POUND SIGN}'), # ‘£’
    MacroTextSpec('textcurrency', u'\N{CURRENCY SIGN}'), # ‘¤’
    MacroTextSpec('textyen', u'\N{YEN SIGN}'), # ‘¥’
    MacroTextSpec('textbrokenbar', u'\N{BROKEN BAR}'), # ‘¦’
    MacroTextSpec('textsection', u'\N{SECTION SIGN}'), # ‘§’
    MacroTextSpec('textasciidieresis', u'\N{DIAERESIS}'), # ‘¨’
    MacroTextSpec('textcopyright', u'\N{COPYRIGHT SIGN}'), # ‘©’
    MacroTextSpec('textordfeminine', u'\N{FEMININE ORDINAL INDICATOR}'), # ‘ª’
    MacroTextSpec('guillemotleft', u'\N{LEFT-POINTING DOUBLE ANGLE QUOTATION MARK}'), # ‘«’
    MacroTextSpec('textlnot', u'\N{NOT SIGN}'), # ‘¬’
    MacroTextSpec('-', u'\N{SOFT HYPHEN}'), # ‘­’
    MacroTextSpec('textregistered', u'\N{REGISTERED SIGN}'), # ‘®’
    MacroTextSpec('textasciimacron', u'\N{MACRON}'), # ‘¯’
    MacroTextSpec('textdegree', u'\N{DEGREE SIGN}'), # ‘°’
    MacroTextSpec('texttwosuperior', u'\N{SUPERSCRIPT TWO}'), # ‘²’
    MacroTextSpec('textthreesuperior', u'\N{SUPERSCRIPT THREE}'), # ‘³’
    MacroTextSpec('textasciiacute', u'\N{ACUTE ACCENT}'), # ‘´’
    MacroTextSpec('textmu', u'\N{MICRO SIGN}'), # ‘µ’
    MacroTextSpec('textparagraph', u'\N{PILCROW SIGN}'), # ‘¶’
    MacroTextSpec('textperiodcentered', u'\N{MIDDLE DOT}'), # ‘·’
    MacroTextSpec('textonesuperior', u'\N{SUPERSCRIPT ONE}'), # ‘¹’
    MacroTextSpec('textordmasculine', u'\N{MASCULINE ORDINAL INDICATOR}'), # ‘º’
    MacroTextSpec('guillemotright', u'\N{RIGHT-POINTING DOUBLE ANGLE QUOTATION MARK}'), # ‘»’
    MacroTextSpec('textonequarter', u'\N{VULGAR FRACTION ONE QUARTER}'), # ‘¼’
    MacroTextSpec('textonehalf', u'\N{VULGAR FRACTION ONE HALF}'), # ‘½’
    MacroTextSpec('textthreequarters', u'\N{VULGAR FRACTION THREE QUARTERS}'), # ‘¾’
    MacroTextSpec('textquestiondown', u'\N{INVERTED QUESTION MARK}'), # ‘¿’
    MacroTextSpec('DH', u'\N{LATIN CAPITAL LETTER ETH}'), # ‘Ð’
    MacroTextSpec('texttimes', u'\N{MULTIPLICATION SIGN}'), # ‘×’
    MacroTextSpec('TH', u'\N{LATIN CAPITAL LETTER THORN}'), # ‘Þ’
    MacroTextSpec('dh', u'\N{LATIN SMALL LETTER ETH}'), # ‘ð’
    MacroTextSpec('textdiv', u'\N{DIVISION SIGN}'), # ‘÷’
    MacroTextSpec('th', u'\N{LATIN SMALL LETTER THORN}'), # ‘þ’
    MacroTextSpec('DJ', u'\N{LATIN CAPITAL LETTER D WITH STROKE}'), # ‘Đ’
    MacroTextSpec('dj', u'\N{LATIN SMALL LETTER D WITH STROKE}'), # ‘đ’
    MacroTextSpec('IJ', u'\N{LATIN CAPITAL LIGATURE IJ}'), # ‘Ĳ’
    MacroTextSpec('ij', u'\N{LATIN SMALL LIGATURE IJ}'), # ‘ĳ’
    MacroTextSpec('NG', u'\N{LATIN CAPITAL LETTER ENG}'), # ‘Ŋ’
    MacroTextSpec('ng', u'\N{LATIN SMALL LETTER ENG}'), # ‘ŋ’
    MacroTextSpec('textflorin', u'\N{LATIN SMALL LETTER F WITH HOOK}'), # ‘ƒ’
    MacroTextSpec('texthvlig', u'\N{LATIN SMALL LETTER HV}'), # ‘ƕ’
    MacroTextSpec('textnrleg', u'\N{LATIN SMALL LETTER N WITH LONG RIGHT LEG}'), # ‘ƞ’
    MacroTextSpec('textschwa', u'\N{LATIN SMALL LETTER SCHWA}'), # ‘ə’
    MacroTextSpec('textphi', u'\N{LATIN SMALL LETTER PHI}'), # ‘ɸ’
    MacroTextSpec('textglotstop', u'\N{LATIN LETTER GLOTTAL STOP}'), # ‘ʔ’
    MacroTextSpec('textturnk', u'\N{LATIN SMALL LETTER TURNED K}'), # ‘ʞ’
    MacroTextSpec('textasciicircum', u'\N{MODIFIER LETTER CIRCUMFLEX ACCENT}'), # ‘ˆ’
    MacroTextSpec('textasciicaron', u'\N{CARON}'), # ‘ˇ’
    MacroTextSpec('textasciibreve', u'\N{BREVE}'), # ‘˘’
    MacroTextSpec('textperiodcentered', u'\N{DOT ABOVE}'), # ‘˙’
    MacroTextSpec('textasciitilde', u'\N{SMALL TILDE}'), # ‘˜’
    MacroTextSpec('textacutedbl', u'\N{DOUBLE ACUTE ACCENT}'), # ‘˝’
    MacroTextSpec('varkappa', u'\N{GREEK KAPPA SYMBOL}'), # ‘ϰ’
    MacroTextSpec('backepsilon', u'\N{GREEK REVERSED LUNATE EPSILON SYMBOL}'), # ‘϶’
    MacroTextSpec('CYRYO', u'\N{CYRILLIC CAPITAL LETTER IO}'), # ‘Ё’
    MacroTextSpec('CYRDJE', u'\N{CYRILLIC CAPITAL LETTER DJE}'), # ‘Ђ’
    MacroTextSpec('CYRIE', u'\N{CYRILLIC CAPITAL LETTER UKRAINIAN IE}'), # ‘Є’
    MacroTextSpec('CYRDZE', u'\N{CYRILLIC CAPITAL LETTER DZE}'), # ‘Ѕ’
    MacroTextSpec('CYRII', u'\N{CYRILLIC CAPITAL LETTER BYELORUSSIAN-UKRAINIAN I}'), # ‘І’
    MacroTextSpec('CYRYI', u'\N{CYRILLIC CAPITAL LETTER YI}'), # ‘Ї’
    MacroTextSpec('CYRJE', u'\N{CYRILLIC CAPITAL LETTER JE}'), # ‘Ј’
    MacroTextSpec('CYRLJE', u'\N{CYRILLIC CAPITAL LETTER LJE}'), # ‘Љ’
    MacroTextSpec('CYRNJE', u'\N{CYRILLIC CAPITAL LETTER NJE}'), # ‘Њ’
    MacroTextSpec('CYRTSHE', u'\N{CYRILLIC CAPITAL LETTER TSHE}'), # ‘Ћ’
    MacroTextSpec('CYRUSHRT', u'\N{CYRILLIC CAPITAL LETTER SHORT U}'), # ‘Ў’
    MacroTextSpec('CYRDZHE', u'\N{CYRILLIC CAPITAL LETTER DZHE}'), # ‘Џ’
    MacroTextSpec('CYRA', u'\N{CYRILLIC CAPITAL LETTER A}'), # ‘А’
    MacroTextSpec('CYRB', u'\N{CYRILLIC CAPITAL LETTER BE}'), # ‘Б’
    MacroTextSpec('CYRV', u'\N{CYRILLIC CAPITAL LETTER VE}'), # ‘В’
    MacroTextSpec('CYRG', u'\N{CYRILLIC CAPITAL LETTER GHE}'), # ‘Г’
    MacroTextSpec('CYRD', u'\N{CYRILLIC CAPITAL LETTER DE}'), # ‘Д’
    MacroTextSpec('CYRE', u'\N{CYRILLIC CAPITAL LETTER IE}'), # ‘Е’
    MacroTextSpec('CYRZH', u'\N{CYRILLIC CAPITAL LETTER ZHE}'), # ‘Ж’
    MacroTextSpec('CYRZ', u'\N{CYRILLIC CAPITAL LETTER ZE}'), # ‘З’
    MacroTextSpec('CYRI', u'\N{CYRILLIC CAPITAL LETTER I}'), # ‘И’
    MacroTextSpec('CYRISHRT', u'\N{CYRILLIC CAPITAL LETTER SHORT I}'), # ‘Й’
    MacroTextSpec('CYRK', u'\N{CYRILLIC CAPITAL LETTER KA}'), # ‘К’
    MacroTextSpec('CYRL', u'\N{CYRILLIC CAPITAL LETTER EL}'), # ‘Л’
    MacroTextSpec('CYRM', u'\N{CYRILLIC CAPITAL LETTER EM}'), # ‘М’
    MacroTextSpec('CYRN', u'\N{CYRILLIC CAPITAL LETTER EN}'), # ‘Н’
    MacroTextSpec('CYRO', u'\N{CYRILLIC CAPITAL LETTER O}'), # ‘О’
    MacroTextSpec('CYRP', u'\N{CYRILLIC CAPITAL LETTER PE}'), # ‘П’
    MacroTextSpec('CYRR', u'\N{CYRILLIC CAPITAL LETTER ER}'), # ‘Р’
    MacroTextSpec('CYRS', u'\N{CYRILLIC CAPITAL LETTER ES}'), # ‘С’
    MacroTextSpec('CYRT', u'\N{CYRILLIC CAPITAL LETTER TE}'), # ‘Т’
    MacroTextSpec('CYRU', u'\N{CYRILLIC CAPITAL LETTER U}'), # ‘У’
    MacroTextSpec('CYRF', u'\N{CYRILLIC CAPITAL LETTER EF}'), # ‘Ф’
    MacroTextSpec('CYRH', u'\N{CYRILLIC CAPITAL LETTER HA}'), # ‘Х’
    MacroTextSpec('CYRC', u'\N{CYRILLIC CAPITAL LETTER TSE}'), # ‘Ц’
    MacroTextSpec('CYRCH', u'\N{CYRILLIC CAPITAL LETTER CHE}'), # ‘Ч’
    MacroTextSpec('CYRSH', u'\N{CYRILLIC CAPITAL LETTER SHA}'), # ‘Ш’
    MacroTextSpec('CYRSHCH', u'\N{CYRILLIC CAPITAL LETTER SHCHA}'), # ‘Щ’
    MacroTextSpec('CYRHRDSN', u'\N{CYRILLIC CAPITAL LETTER HARD SIGN}'), # ‘Ъ’
    MacroTextSpec('CYRERY', u'\N{CYRILLIC CAPITAL LETTER YERU}'), # ‘Ы’
    MacroTextSpec('CYRSFTSN', u'\N{CYRILLIC CAPITAL LETTER SOFT SIGN}'), # ‘Ь’
    MacroTextSpec('CYREREV', u'\N{CYRILLIC CAPITAL LETTER E}'), # ‘Э’
    MacroTextSpec('CYRYU', u'\N{CYRILLIC CAPITAL LETTER YU}'), # ‘Ю’
    MacroTextSpec('CYRYA', u'\N{CYRILLIC CAPITAL LETTER YA}'), # ‘Я’
    MacroTextSpec('cyra', u'\N{CYRILLIC SMALL LETTER A}'), # ‘а’
    MacroTextSpec('cyrb', u'\N{CYRILLIC SMALL LETTER BE}'), # ‘б’
    MacroTextSpec('cyrv', u'\N{CYRILLIC SMALL LETTER VE}'), # ‘в’
    MacroTextSpec('cyrg', u'\N{CYRILLIC SMALL LETTER GHE}'), # ‘г’
    MacroTextSpec('cyrd', u'\N{CYRILLIC SMALL LETTER DE}'), # ‘д’
    MacroTextSpec('cyre', u'\N{CYRILLIC SMALL LETTER IE}'), # ‘е’
    MacroTextSpec('cyrzh', u'\N{CYRILLIC SMALL LETTER ZHE}'), # ‘ж’
    MacroTextSpec('cyrz', u'\N{CYRILLIC SMALL LETTER ZE}'), # ‘з’
    MacroTextSpec('cyri', u'\N{CYRILLIC SMALL LETTER I}'), # ‘и’
    MacroTextSpec('cyrishrt', u'\N{CYRILLIC SMALL LETTER SHORT I}'), # ‘й’
    MacroTextSpec('cyrk', u'\N{CYRILLIC SMALL LETTER KA}'), # ‘к’
    MacroTextSpec('cyrl', u'\N{CYRILLIC SMALL LETTER EL}'), # ‘л’
    MacroTextSpec('cyrm', u'\N{CYRILLIC SMALL LETTER EM}'), # ‘м’
    MacroTextSpec('cyrn', u'\N{CYRILLIC SMALL LETTER EN}'), # ‘н’
    MacroTextSpec('cyro', u'\N{CYRILLIC SMALL LETTER O}'), # ‘о’
    MacroTextSpec('cyrp', u'\N{CYRILLIC SMALL LETTER PE}'), # ‘п’
    MacroTextSpec('cyrr', u'\N{CYRILLIC SMALL LETTER ER}'), # ‘р’
    MacroTextSpec('cyrs', u'\N{CYRILLIC SMALL LETTER ES}'), # ‘с’
    MacroTextSpec('cyrt', u'\N{CYRILLIC SMALL LETTER TE}'), # ‘т’
    MacroTextSpec('cyru', u'\N{CYRILLIC SMALL LETTER U}'), # ‘у’
    MacroTextSpec('cyrf', u'\N{CYRILLIC SMALL LETTER EF}'), # ‘ф’
    MacroTextSpec('cyrh', u'\N{CYRILLIC SMALL LETTER HA}'), # ‘х’
    MacroTextSpec('cyrc', u'\N{CYRILLIC SMALL LETTER TSE}'), # ‘ц’
    MacroTextSpec('cyrch', u'\N{CYRILLIC SMALL LETTER CHE}'), # ‘ч’
    MacroTextSpec('cyrsh', u'\N{CYRILLIC SMALL LETTER SHA}'), # ‘ш’
    MacroTextSpec('cyrshch', u'\N{CYRILLIC SMALL LETTER SHCHA}'), # ‘щ’
    MacroTextSpec('cyrhrdsn', u'\N{CYRILLIC SMALL LETTER HARD SIGN}'), # ‘ъ’
    MacroTextSpec('cyrery', u'\N{CYRILLIC SMALL LETTER YERU}'), # ‘ы’
    MacroTextSpec('cyrsftsn', u'\N{CYRILLIC SMALL LETTER SOFT SIGN}'), # ‘ь’
    MacroTextSpec('cyrerev', u'\N{CYRILLIC SMALL LETTER E}'), # ‘э’
    MacroTextSpec('cyryu', u'\N{CYRILLIC SMALL LETTER YU}'), # ‘ю’
    MacroTextSpec('cyrya', u'\N{CYRILLIC SMALL LETTER YA}'), # ‘я’
    MacroTextSpec('cyryo', u'\N{CYRILLIC SMALL LETTER IO}'), # ‘ё’
    MacroTextSpec('cyrdje', u'\N{CYRILLIC SMALL LETTER DJE}'), # ‘ђ’
    MacroTextSpec('cyrie', u'\N{CYRILLIC SMALL LETTER UKRAINIAN IE}'), # ‘є’
    MacroTextSpec('cyrdze', u'\N{CYRILLIC SMALL LETTER DZE}'), # ‘ѕ’
    MacroTextSpec('cyrii', u'\N{CYRILLIC SMALL LETTER BYELORUSSIAN-UKRAINIAN I}'), # ‘і’
    MacroTextSpec('cyryi', u'\N{CYRILLIC SMALL LETTER YI}'), # ‘ї’
    MacroTextSpec('cyrje', u'\N{CYRILLIC SMALL LETTER JE}'), # ‘ј’
    MacroTextSpec('cyrlje', u'\N{CYRILLIC SMALL LETTER LJE}'), # ‘љ’
    MacroTextSpec('cyrnje', u'\N{CYRILLIC SMALL LETTER NJE}'), # ‘њ’
    MacroTextSpec('cyrtshe', u'\N{CYRILLIC SMALL LETTER TSHE}'), # ‘ћ’
    MacroTextSpec('cyrushrt', u'\N{CYRILLIC SMALL LETTER SHORT U}'), # ‘ў’
    MacroTextSpec('cyrdzhe', u'\N{CYRILLIC SMALL LETTER DZHE}'), # ‘џ’
    MacroTextSpec('CYRYAT', u'\N{CYRILLIC CAPITAL LETTER YAT}'), # ‘Ѣ’
    MacroTextSpec('cyryat', u'\N{CYRILLIC SMALL LETTER YAT}'), # ‘ѣ’
    MacroTextSpec('CYRBYUS', u'\N{CYRILLIC CAPITAL LETTER BIG YUS}'), # ‘Ѫ’
    MacroTextSpec('cyrbyus', u'\N{CYRILLIC SMALL LETTER BIG YUS}'), # ‘ѫ’
    MacroTextSpec('CYRFITA', u'\N{CYRILLIC CAPITAL LETTER FITA}'), # ‘Ѳ’
    MacroTextSpec('cyrfita', u'\N{CYRILLIC SMALL LETTER FITA}'), # ‘ѳ’
    MacroTextSpec('CYRIZH', u'\N{CYRILLIC CAPITAL LETTER IZHITSA}'), # ‘Ѵ’
    MacroTextSpec('cyrizh', u'\N{CYRILLIC SMALL LETTER IZHITSA}'), # ‘ѵ’
    MacroTextSpec('CYRSEMISFTSN', u'\N{CYRILLIC CAPITAL LETTER SEMISOFT SIGN}'), # ‘Ҍ’
    MacroTextSpec('cyrsemisftsn', u'\N{CYRILLIC SMALL LETTER SEMISOFT SIGN}'), # ‘ҍ’
    MacroTextSpec('CYRRTICK', u'\N{CYRILLIC CAPITAL LETTER ER WITH TICK}'), # ‘Ҏ’
    MacroTextSpec('cyrrtick', u'\N{CYRILLIC SMALL LETTER ER WITH TICK}'), # ‘ҏ’
    MacroTextSpec('CYRGUP', u'\N{CYRILLIC CAPITAL LETTER GHE WITH UPTURN}'), # ‘Ґ’
    MacroTextSpec('cyrgup', u'\N{CYRILLIC SMALL LETTER GHE WITH UPTURN}'), # ‘ґ’
    MacroTextSpec('CYRGHCRS', u'\N{CYRILLIC CAPITAL LETTER GHE WITH STROKE}'), # ‘Ғ’
    MacroTextSpec('cyrghcrs', u'\N{CYRILLIC SMALL LETTER GHE WITH STROKE}'), # ‘ғ’
    MacroTextSpec('CYRGHK', u'\N{CYRILLIC CAPITAL LETTER GHE WITH MIDDLE HOOK}'), # ‘Ҕ’
    MacroTextSpec('cyrghk', u'\N{CYRILLIC SMALL LETTER GHE WITH MIDDLE HOOK}'), # ‘ҕ’
    MacroTextSpec('CYRZHDSC', u'\N{CYRILLIC CAPITAL LETTER ZHE WITH DESCENDER}'), # ‘Җ’
    MacroTextSpec('cyrzhdsc', u'\N{CYRILLIC SMALL LETTER ZHE WITH DESCENDER}'), # ‘җ’
    MacroTextSpec('CYRZDSC', u'\N{CYRILLIC CAPITAL LETTER ZE WITH DESCENDER}'), # ‘Ҙ’
    MacroTextSpec('cyrzdsc', u'\N{CYRILLIC SMALL LETTER ZE WITH DESCENDER}'), # ‘ҙ’
    MacroTextSpec('CYRKDSC', u'\N{CYRILLIC CAPITAL LETTER KA WITH DESCENDER}'), # ‘Қ’
    MacroTextSpec('cyrkdsc', u'\N{CYRILLIC SMALL LETTER KA WITH DESCENDER}'), # ‘қ’
    MacroTextSpec('CYRKVCRS', u'\N{CYRILLIC CAPITAL LETTER KA WITH VERTICAL STROKE}'), # ‘Ҝ’
    MacroTextSpec('cyrkvcrs', u'\N{CYRILLIC SMALL LETTER KA WITH VERTICAL STROKE}'), # ‘ҝ’
    MacroTextSpec('CYRKHCRS', u'\N{CYRILLIC CAPITAL LETTER KA WITH STROKE}'), # ‘Ҟ’
    MacroTextSpec('cyrkhcrs', u'\N{CYRILLIC SMALL LETTER KA WITH STROKE}'), # ‘ҟ’
    MacroTextSpec('CYRKBEAK', u'\N{CYRILLIC CAPITAL LETTER BASHKIR KA}'), # ‘Ҡ’
    MacroTextSpec('cyrkbeak', u'\N{CYRILLIC SMALL LETTER BASHKIR KA}'), # ‘ҡ’
    MacroTextSpec('CYRNDSC', u'\N{CYRILLIC CAPITAL LETTER EN WITH DESCENDER}'), # ‘Ң’
    MacroTextSpec('cyrndsc', u'\N{CYRILLIC SMALL LETTER EN WITH DESCENDER}'), # ‘ң’
    MacroTextSpec('CYRNG', u'\N{CYRILLIC CAPITAL LIGATURE EN GHE}'), # ‘Ҥ’
    MacroTextSpec('cyrng', u'\N{CYRILLIC SMALL LIGATURE EN GHE}'), # ‘ҥ’
    MacroTextSpec('CYRPHK', u'\N{CYRILLIC CAPITAL LETTER PE WITH MIDDLE HOOK}'), # ‘Ҧ’
    MacroTextSpec('cyrphk', u'\N{CYRILLIC SMALL LETTER PE WITH MIDDLE HOOK}'), # ‘ҧ’
    MacroTextSpec('CYRABHHA', u'\N{CYRILLIC CAPITAL LETTER ABKHASIAN HA}'), # ‘Ҩ’
    MacroTextSpec('cyrabhha', u'\N{CYRILLIC SMALL LETTER ABKHASIAN HA}'), # ‘ҩ’
    MacroTextSpec('CYRSDSC', u'\N{CYRILLIC CAPITAL LETTER ES WITH DESCENDER}'), # ‘Ҫ’
    MacroTextSpec('cyrsdsc', u'\N{CYRILLIC SMALL LETTER ES WITH DESCENDER}'), # ‘ҫ’
    MacroTextSpec('CYRTDSC', u'\N{CYRILLIC CAPITAL LETTER TE WITH DESCENDER}'), # ‘Ҭ’
    MacroTextSpec('cyrtdsc', u'\N{CYRILLIC SMALL LETTER TE WITH DESCENDER}'), # ‘ҭ’
    MacroTextSpec('CYRY', u'\N{CYRILLIC CAPITAL LETTER STRAIGHT U}'), # ‘Ү’
    MacroTextSpec('cyry', u'\N{CYRILLIC SMALL LETTER STRAIGHT U}'), # ‘ү’
    MacroTextSpec('CYRYHCRS', u'\N{CYRILLIC CAPITAL LETTER STRAIGHT U WITH STROKE}'), # ‘Ұ’
    MacroTextSpec('cyryhcrs', u'\N{CYRILLIC SMALL LETTER STRAIGHT U WITH STROKE}'), # ‘ұ’
    MacroTextSpec('CYRHDSC', u'\N{CYRILLIC CAPITAL LETTER HA WITH DESCENDER}'), # ‘Ҳ’
    MacroTextSpec('cyrhdsc', u'\N{CYRILLIC SMALL LETTER HA WITH DESCENDER}'), # ‘ҳ’
    MacroTextSpec('CYRTETSE', u'\N{CYRILLIC CAPITAL LIGATURE TE TSE}'), # ‘Ҵ’
    MacroTextSpec('cyrtetse', u'\N{CYRILLIC SMALL LIGATURE TE TSE}'), # ‘ҵ’
    MacroTextSpec('CYRCHRDSC', u'\N{CYRILLIC CAPITAL LETTER CHE WITH DESCENDER}'), # ‘Ҷ’
    MacroTextSpec('cyrchrdsc', u'\N{CYRILLIC SMALL LETTER CHE WITH DESCENDER}'), # ‘ҷ’
    MacroTextSpec('CYRCHVCRS', u'\N{CYRILLIC CAPITAL LETTER CHE WITH VERTICAL STROKE}'), # ‘Ҹ’
    MacroTextSpec('cyrchvcrs', u'\N{CYRILLIC SMALL LETTER CHE WITH VERTICAL STROKE}'), # ‘ҹ’
    MacroTextSpec('CYRSHHA', u'\N{CYRILLIC CAPITAL LETTER SHHA}'), # ‘Һ’
    MacroTextSpec('cyrshha', u'\N{CYRILLIC SMALL LETTER SHHA}'), # ‘һ’
    MacroTextSpec('CYRABHCH', u'\N{CYRILLIC CAPITAL LETTER ABKHASIAN CHE}'), # ‘Ҽ’
    MacroTextSpec('cyrabhch', u'\N{CYRILLIC SMALL LETTER ABKHASIAN CHE}'), # ‘ҽ’
    MacroTextSpec('CYRABHCHDSC', u'\N{CYRILLIC CAPITAL LETTER ABKHASIAN CHE WITH DESCENDER}'), # ‘Ҿ’
    MacroTextSpec('cyrabhchdsc', u'\N{CYRILLIC SMALL LETTER ABKHASIAN CHE WITH DESCENDER}'), # ‘ҿ’
    MacroTextSpec('CYRpalochka', u'\N{CYRILLIC LETTER PALOCHKA}'), # ‘Ӏ’
    MacroTextSpec('CYRKHK', u'\N{CYRILLIC CAPITAL LETTER KA WITH HOOK}'), # ‘Ӄ’
    MacroTextSpec('cyrkhk', u'\N{CYRILLIC SMALL LETTER KA WITH HOOK}'), # ‘ӄ’
    MacroTextSpec('CYRLDSC', u'\N{CYRILLIC CAPITAL LETTER EL WITH TAIL}'), # ‘Ӆ’
    MacroTextSpec('cyrldsc', u'\N{CYRILLIC SMALL LETTER EL WITH TAIL}'), # ‘ӆ’
    MacroTextSpec('CYRNHK', u'\N{CYRILLIC CAPITAL LETTER EN WITH HOOK}'), # ‘Ӈ’
    MacroTextSpec('cyrnhk', u'\N{CYRILLIC SMALL LETTER EN WITH HOOK}'), # ‘ӈ’
    MacroTextSpec('CYRCHLDSC', u'\N{CYRILLIC CAPITAL LETTER KHAKASSIAN CHE}'), # ‘Ӌ’
    MacroTextSpec('cyrchldsc', u'\N{CYRILLIC SMALL LETTER KHAKASSIAN CHE}'), # ‘ӌ’
    MacroTextSpec('CYRMDSC', u'\N{CYRILLIC CAPITAL LETTER EM WITH TAIL}'), # ‘Ӎ’
    MacroTextSpec('cyrmdsc', u'\N{CYRILLIC SMALL LETTER EM WITH TAIL}'), # ‘ӎ’
    MacroTextSpec('CYRAE', u'\N{CYRILLIC CAPITAL LIGATURE A IE}'), # ‘Ӕ’
    MacroTextSpec('cyrae', u'\N{CYRILLIC SMALL LIGATURE A IE}'), # ‘ӕ’
    MacroTextSpec('CYRSCHWA', u'\N{CYRILLIC CAPITAL LETTER SCHWA}'), # ‘Ә’
    MacroTextSpec('cyrschwa', u'\N{CYRILLIC SMALL LETTER SCHWA}'), # ‘ә’
    MacroTextSpec('CYRABHDZE', u'\N{CYRILLIC CAPITAL LETTER ABKHASIAN DZE}'), # ‘Ӡ’
    MacroTextSpec('cyrabhdze', u'\N{CYRILLIC SMALL LETTER ABKHASIAN DZE}'), # ‘ӡ’
    MacroTextSpec('CYROTLD', u'\N{CYRILLIC CAPITAL LETTER BARRED O}'), # ‘Ө’
    MacroTextSpec('cyrotld', u'\N{CYRILLIC SMALL LETTER BARRED O}'), # ‘ө’
    MacroTextSpec('CYRGDSC', u'\N{CYRILLIC CAPITAL LETTER GHE WITH DESCENDER}'), # ‘Ӷ’
    MacroTextSpec('cyrgdsc', u'\N{CYRILLIC SMALL LETTER GHE WITH DESCENDER}'), # ‘ӷ’
    MacroTextSpec('CYRGDSCHCRS', u'\N{CYRILLIC CAPITAL LETTER GHE WITH STROKE AND HOOK}'), # ‘Ӻ’
    MacroTextSpec('cyrgdschcrs', u'\N{CYRILLIC SMALL LETTER GHE WITH STROKE AND HOOK}'), # ‘ӻ’
    MacroTextSpec('CYRHHK', u'\N{CYRILLIC CAPITAL LETTER HA WITH HOOK}'), # ‘Ӽ’
    MacroTextSpec('cyrhhk', u'\N{CYRILLIC SMALL LETTER HA WITH HOOK}'), # ‘ӽ’
    MacroTextSpec('CYRHHCRS', u'\N{CYRILLIC CAPITAL LETTER HA WITH STROKE}'), # ‘Ӿ’
    MacroTextSpec('cyrhhcrs', u'\N{CYRILLIC SMALL LETTER HA WITH STROKE}'), # ‘ӿ’
    MacroTextSpec('textbaht', u'\N{THAI CURRENCY SYMBOL BAHT}'), # ‘฿’
    MacroTextSpec('enskip', u'\N{EN QUAD}'), # ‘ ’
    MacroTextSpec('enskip', u'\N{EN SPACE}'), # ‘ ’
    MacroTextSpec('textcompwordmark', u'\N{ZERO WIDTH NON-JOINER}'), # ‘‌’
    MacroTextSpec('quotesinglbase', u'\N{SINGLE LOW-9 QUOTATION MARK}'), # ‘‚’
    MacroTextSpec('quotedblbase', u'\N{DOUBLE LOW-9 QUOTATION MARK}'), # ‘„’
    MacroTextSpec('textdagger', u'\N{DAGGER}'), # ‘†’
    MacroTextSpec('textdaggerdbl', u'\N{DOUBLE DAGGER}'), # ‘‡’
    MacroTextSpec('textbullet', u'\N{BULLET}'), # ‘•’
    MacroTextSpec('textellipsis', u'\N{HORIZONTAL ELLIPSIS}'), # ‘…’
    MacroTextSpec('textperthousand', u'\N{PER MILLE SIGN}'), # ‘‰’
    MacroTextSpec('textpertenthousand', u'\N{PER TEN THOUSAND SIGN}'), # ‘‱’
    MacroTextSpec('backprime', u'\N{REVERSED PRIME}'), # ‘‵’
    MacroTextSpec('guilsinglleft', u'\N{SINGLE LEFT-POINTING ANGLE QUOTATION MARK}'), # ‘‹’
    MacroTextSpec('guilsinglright', u'\N{SINGLE RIGHT-POINTING ANGLE QUOTATION MARK}'), # ‘›’
    MacroTextSpec('textreferencemark', u'\N{REFERENCE MARK}'), # ‘※’
    MacroTextSpec('textinterrobang', u'\N{INTERROBANG}'), # ‘‽’
    MacroTextSpec('textfractionsolidus', u'\N{FRACTION SLASH}'), # ‘⁄’
    MacroTextSpec('textasteriskcentered', u'\N{LOW ASTERISK}'), # ‘⁎’
    MacroTextSpec('textdiscount', u'\N{COMMERCIAL MINUS SIGN}'), # ‘⁒’
    MacroTextSpec('nolinebreak', u'\N{WORD JOINER}'), # ‘⁠’
    MacroTextSpec('textcolonmonetary', u'\N{COLON SIGN}'), # ‘₡’
    MacroTextSpec('textlira', u'\N{LIRA SIGN}'), # ‘₤’
    MacroTextSpec('textnaira', u'\N{NAIRA SIGN}'), # ‘₦’
    MacroTextSpec('textwon', u'\N{WON SIGN}'), # ‘₩’
    MacroTextSpec('textdong', u'\N{DONG SIGN}'), # ‘₫’
    MacroTextSpec('textpeso', u'\N{PESO SIGN}'), # ‘₱’
    MacroTextSpec('textcelsius', u'\N{DEGREE CELSIUS}'), # ‘℃’
    MacroTextSpec('textnumero', u'\N{NUMERO SIGN}'), # ‘№’
    MacroTextSpec('textcircledP', u'\N{SOUND RECORDING COPYRIGHT}'), # ‘℗’
    MacroTextSpec('wp', u'\N{SCRIPT CAPITAL P}'), # ‘℘’
    MacroTextSpec('textrecipe', u'\N{PRESCRIPTION TAKE}'), # ‘℞’
    MacroTextSpec('textservicemark', u'\N{SERVICE MARK}'), # ‘℠’
    MacroTextSpec('texttrademark', u'\N{TRADE MARK SIGN}'), # ‘™’
    MacroTextSpec('textohm', u'\N{OHM SIGN}'), # ‘Ω’
    MacroTextSpec('textmho', u'\N{INVERTED OHM SIGN}'), # ‘℧’
    MacroTextSpec('textestimated', u'\N{ESTIMATED SYMBOL}'), # ‘℮’
    MacroTextSpec('beth', u'\N{BET SYMBOL}'), # ‘ℶ’
    MacroTextSpec('gimel', u'\N{GIMEL SYMBOL}'), # ‘ℷ’
    MacroTextSpec('daleth', u'\N{DALET SYMBOL}'), # ‘ℸ’
    MacroTextSpec('textleftarrow', u'\N{LEFTWARDS ARROW}'), # ‘←’
    MacroTextSpec('textuparrow', u'\N{UPWARDS ARROW}'), # ‘↑’
    MacroTextSpec('textrightarrow', u'\N{RIGHTWARDS ARROW}'), # ‘→’
    MacroTextSpec('textdownarrow', u'\N{DOWNWARDS ARROW}'), # ‘↓’
    MacroTextSpec('leftrightarrow', u'\N{LEFT RIGHT ARROW}'), # ‘↔’
    MacroTextSpec('updownarrow', u'\N{UP DOWN ARROW}'), # ‘↕’
    MacroTextSpec('nwarrow', u'\N{NORTH WEST ARROW}'), # ‘↖’
    MacroTextSpec('nearrow', u'\N{NORTH EAST ARROW}'), # ‘↗’
    MacroTextSpec('searrow', u'\N{SOUTH EAST ARROW}'), # ‘↘’
    MacroTextSpec('swarrow', u'\N{SOUTH WEST ARROW}'), # ‘↙’
    MacroTextSpec('nleftarrow', u'\N{LEFTWARDS ARROW WITH STROKE}'), # ‘↚’
    MacroTextSpec('nrightarrow', u'\N{RIGHTWARDS ARROW WITH STROKE}'), # ‘↛’
    MacroTextSpec('arrowwaveleft', u'\N{LEFTWARDS WAVE ARROW}'), # ‘↜’
    MacroTextSpec('arrowwaveright', u'\N{RIGHTWARDS WAVE ARROW}'), # ‘↝’
    MacroTextSpec('twoheadleftarrow', u'\N{LEFTWARDS TWO HEADED ARROW}'), # ‘↞’
    MacroTextSpec('twoheadrightarrow', u'\N{RIGHTWARDS TWO HEADED ARROW}'), # ‘↠’
    MacroTextSpec('leftarrowtail', u'\N{LEFTWARDS ARROW WITH TAIL}'), # ‘↢’
    MacroTextSpec('rightarrowtail', u'\N{RIGHTWARDS ARROW WITH TAIL}'), # ‘↣’
    MacroTextSpec('mapsto', u'\N{RIGHTWARDS ARROW FROM BAR}'), # ‘↦’
    MacroTextSpec('hookleftarrow', u'\N{LEFTWARDS ARROW WITH HOOK}'), # ‘↩’
    MacroTextSpec('hookrightarrow', u'\N{RIGHTWARDS ARROW WITH HOOK}'), # ‘↪’
    MacroTextSpec('looparrowleft', u'\N{LEFTWARDS ARROW WITH LOOP}'), # ‘↫’
    MacroTextSpec('looparrowright', u'\N{RIGHTWARDS ARROW WITH LOOP}'), # ‘↬’
    MacroTextSpec('leftrightsquigarrow', u'\N{LEFT RIGHT WAVE ARROW}'), # ‘↭’
    MacroTextSpec('nleftrightarrow', u'\N{LEFT RIGHT ARROW WITH STROKE}'), # ‘↮’
    MacroTextSpec('Lsh', u'\N{UPWARDS ARROW WITH TIP LEFTWARDS}'), # ‘↰’
    MacroTextSpec('Rsh', u'\N{UPWARDS ARROW WITH TIP RIGHTWARDS}'), # ‘↱’
    MacroTextSpec('curvearrowleft', u'\N{ANTICLOCKWISE TOP SEMICIRCLE ARROW}'), # ‘↶’
    MacroTextSpec('curvearrowright', u'\N{CLOCKWISE TOP SEMICIRCLE ARROW}'), # ‘↷’
    MacroTextSpec('circlearrowleft', u'\N{ANTICLOCKWISE OPEN CIRCLE ARROW}'), # ‘↺’
    MacroTextSpec('circlearrowright', u'\N{CLOCKWISE OPEN CIRCLE ARROW}'), # ‘↻’
    MacroTextSpec('leftharpoonup', u'\N{LEFTWARDS HARPOON WITH BARB UPWARDS}'), # ‘↼’
    MacroTextSpec('leftharpoondown', u'\N{LEFTWARDS HARPOON WITH BARB DOWNWARDS}'), # ‘↽’
    MacroTextSpec('upharpoonright', u'\N{UPWARDS HARPOON WITH BARB RIGHTWARDS}'), # ‘↾’
    MacroTextSpec('upharpoonleft', u'\N{UPWARDS HARPOON WITH BARB LEFTWARDS}'), # ‘↿’
    MacroTextSpec('rightharpoonup', u'\N{RIGHTWARDS HARPOON WITH BARB UPWARDS}'), # ‘⇀’
    MacroTextSpec('rightharpoondown', u'\N{RIGHTWARDS HARPOON WITH BARB DOWNWARDS}'), # ‘⇁’
    MacroTextSpec('downharpoonright', u'\N{DOWNWARDS HARPOON WITH BARB RIGHTWARDS}'), # ‘⇂’
    MacroTextSpec('downharpoonleft', u'\N{DOWNWARDS HARPOON WITH BARB LEFTWARDS}'), # ‘⇃’
    MacroTextSpec('rightleftarrows', u'\N{RIGHTWARDS ARROW OVER LEFTWARDS ARROW}'), # ‘⇄’
    MacroTextSpec('dblarrowupdown', u'\N{UPWARDS ARROW LEFTWARDS OF DOWNWARDS ARROW}'), # ‘⇅’
    MacroTextSpec('leftrightarrows', u'\N{LEFTWARDS ARROW OVER RIGHTWARDS ARROW}'), # ‘⇆’
    MacroTextSpec('leftleftarrows', u'\N{LEFTWARDS PAIRED ARROWS}'), # ‘⇇’
    MacroTextSpec('upuparrows', u'\N{UPWARDS PAIRED ARROWS}'), # ‘⇈’
    MacroTextSpec('rightrightarrows', u'\N{RIGHTWARDS PAIRED ARROWS}'), # ‘⇉’
    MacroTextSpec('downdownarrows', u'\N{DOWNWARDS PAIRED ARROWS}'), # ‘⇊’
    MacroTextSpec('leftrightharpoons', u'\N{LEFTWARDS HARPOON OVER RIGHTWARDS HARPOON}'), # ‘⇋’
    MacroTextSpec('rightleftharpoons', u'\N{RIGHTWARDS HARPOON OVER LEFTWARDS HARPOON}'), # ‘⇌’
    MacroTextSpec('nLeftarrow', u'\N{LEFTWARDS DOUBLE ARROW WITH STROKE}'), # ‘⇍’
    MacroTextSpec('nLeftrightarrow', u'\N{LEFT RIGHT DOUBLE ARROW WITH STROKE}'), # ‘⇎’
    MacroTextSpec('nRightarrow', u'\N{RIGHTWARDS DOUBLE ARROW WITH STROKE}'), # ‘⇏’
    MacroTextSpec('Leftarrow', u'\N{LEFTWARDS DOUBLE ARROW}'), # ‘⇐’
    MacroTextSpec('Uparrow', u'\N{UPWARDS DOUBLE ARROW}'), # ‘⇑’
    MacroTextSpec('Rightarrow', u'\N{RIGHTWARDS DOUBLE ARROW}'), # ‘⇒’
    MacroTextSpec('Downarrow', u'\N{DOWNWARDS DOUBLE ARROW}'), # ‘⇓’
    MacroTextSpec('Leftrightarrow', u'\N{LEFT RIGHT DOUBLE ARROW}'), # ‘⇔’
    MacroTextSpec('Updownarrow', u'\N{UP DOWN DOUBLE ARROW}'), # ‘⇕’
    MacroTextSpec('Lleftarrow', u'\N{LEFTWARDS TRIPLE ARROW}'), # ‘⇚’
    MacroTextSpec('Rrightarrow', u'\N{RIGHTWARDS TRIPLE ARROW}'), # ‘⇛’
    MacroTextSpec('rightsquigarrow', u'\N{RIGHTWARDS SQUIGGLE ARROW}'), # ‘⇝’
    MacroTextSpec('DownArrowUpArrow', u'\N{DOWNWARDS ARROW LEFTWARDS OF UPWARDS ARROW}'), # ‘⇵’
    MacroTextSpec('blacksquare', u'\N{END OF PROOF}'), # ‘∎’
    MacroTextSpec('dotplus', u'\N{DOT PLUS}'), # ‘∔’
    MacroTextSpec('rightangle', u'\N{RIGHT ANGLE}'), # ‘∟’
    MacroTextSpec('angle', u'\N{ANGLE}'), # ‘∠’
    MacroTextSpec('measuredangle', u'\N{MEASURED ANGLE}'), # ‘∡’
    MacroTextSpec('sphericalangle', u'\N{SPHERICAL ANGLE}'), # ‘∢’
    MacroTextSpec('surfintegral', u'\N{SURFACE INTEGRAL}'), # ‘∯’
    MacroTextSpec('volintegral', u'\N{VOLUME INTEGRAL}'), # ‘∰’
    MacroTextSpec('clwintegral', u'\N{CLOCKWISE INTEGRAL}'), # ‘∱’
    MacroTextSpec('therefore', u'\N{THEREFORE}'), # ‘∴’
    MacroTextSpec('because', u'\N{BECAUSE}'), # ‘∵’
    MacroTextSpec('homothetic', u'\N{HOMOTHETIC}'), # ‘∻’
    MacroTextSpec('lazysinv', u'\N{INVERTED LAZY S}'), # ‘∾’
    MacroTextSpec('wr', u'\N{WREATH PRODUCT}'), # ‘≀’
    MacroTextSpec('cong', u'\N{APPROXIMATELY EQUAL TO}'), # ‘≅’
    MacroTextSpec('approxnotequal', u'\N{APPROXIMATELY BUT NOT ACTUALLY EQUAL TO}'), # ‘≆’
    MacroTextSpec('approxeq', u'\N{ALMOST EQUAL OR EQUAL TO}'), # ‘≊’
    MacroTextSpec('tildetrpl', u'\N{TRIPLE TILDE}'), # ‘≋’
    MacroTextSpec('allequal', u'\N{ALL EQUAL TO}'), # ‘≌’
    MacroTextSpec('asymp', u'\N{EQUIVALENT TO}'), # ‘≍’
    MacroTextSpec('Bumpeq', u'\N{GEOMETRICALLY EQUIVALENT TO}'), # ‘≎’
    MacroTextSpec('bumpeq', u'\N{DIFFERENCE BETWEEN}'), # ‘≏’
    MacroTextSpec('doteq', u'\N{APPROACHES THE LIMIT}'), # ‘≐’
    MacroTextSpec('doteqdot', u'\N{GEOMETRICALLY EQUAL TO}'), # ‘≑’
    MacroTextSpec('fallingdotseq', u'\N{APPROXIMATELY EQUAL TO OR THE IMAGE OF}'), # ‘≒’
    MacroTextSpec('risingdotseq', u'\N{IMAGE OF OR APPROXIMATELY EQUAL TO}'), # ‘≓’
    MacroTextSpec('eqcirc', u'\N{RING IN EQUAL TO}'), # ‘≖’
    MacroTextSpec('circeq', u'\N{RING EQUAL TO}'), # ‘≗’
    MacroTextSpec('estimates', u'\N{ESTIMATES}'), # ‘≙’
    MacroTextSpec('starequal', u'\N{STAR EQUALS}'), # ‘≛’
    MacroTextSpec('triangleq', u'\N{DELTA EQUAL TO}'), # ‘≜’
    MacroTextSpec('between', u'\N{BETWEEN}'), # ‘≬’
    MacroTextSpec('notlessgreater', u'\N{NEITHER LESS-THAN NOR GREATER-THAN}'), # ‘≸’
    MacroTextSpec('notgreaterless', u'\N{NEITHER GREATER-THAN NOR LESS-THAN}'), # ‘≹’
    MacroTextSpec('uplus', u'\N{MULTISET UNION}'), # ‘⊎’
    MacroTextSpec('sqsubset', u'\N{SQUARE IMAGE OF}'), # ‘⊏’
    MacroTextSpec('sqsupset', u'\N{SQUARE ORIGINAL OF}'), # ‘⊐’
    MacroTextSpec('sqsubseteq', u'\N{SQUARE IMAGE OF OR EQUAL TO}'), # ‘⊑’
    MacroTextSpec('sqsupseteq', u'\N{SQUARE ORIGINAL OF OR EQUAL TO}'), # ‘⊒’
    MacroTextSpec('sqcap', u'\N{SQUARE CAP}'), # ‘⊓’
    MacroTextSpec('sqcup', u'\N{SQUARE CUP}'), # ‘⊔’
    MacroTextSpec('ominus', u'\N{CIRCLED MINUS}'), # ‘⊖’
    MacroTextSpec('oslash', u'\N{CIRCLED DIVISION SLASH}'), # ‘⊘’
    MacroTextSpec('odot', u'\N{CIRCLED DOT OPERATOR}'), # ‘⊙’
    MacroTextSpec('circledcirc', u'\N{CIRCLED RING OPERATOR}'), # ‘⊚’
    MacroTextSpec('circledast', u'\N{CIRCLED ASTERISK OPERATOR}'), # ‘⊛’
    MacroTextSpec('circleddash', u'\N{CIRCLED DASH}'), # ‘⊝’
    MacroTextSpec('boxplus', u'\N{SQUARED PLUS}'), # ‘⊞’
    MacroTextSpec('boxminus', u'\N{SQUARED MINUS}'), # ‘⊟’
    MacroTextSpec('boxtimes', u'\N{SQUARED TIMES}'), # ‘⊠’
    MacroTextSpec('boxdot', u'\N{SQUARED DOT OPERATOR}'), # ‘⊡’
    MacroTextSpec('vdash', u'\N{RIGHT TACK}'), # ‘⊢’
    MacroTextSpec('dashv', u'\N{LEFT TACK}'), # ‘⊣’
    MacroTextSpec('top', u'\N{DOWN TACK}'), # ‘⊤’
    MacroTextSpec('perp', u'\N{UP TACK}'), # ‘⊥’
    MacroTextSpec('truestate', u'\N{MODELS}'), # ‘⊧’
    MacroTextSpec('forcesextra', u'\N{TRUE}'), # ‘⊨’
    MacroTextSpec('Vdash', u'\N{FORCES}'), # ‘⊩’
    MacroTextSpec('Vvdash', u'\N{TRIPLE VERTICAL BAR RIGHT TURNSTILE}'), # ‘⊪’
    MacroTextSpec('VDash', u'\N{DOUBLE VERTICAL BAR DOUBLE RIGHT TURNSTILE}'), # ‘⊫’
    MacroTextSpec('nvdash', u'\N{DOES NOT PROVE}'), # ‘⊬’
    MacroTextSpec('nvDash', u'\N{NOT TRUE}'), # ‘⊭’
    MacroTextSpec('nVdash', u'\N{DOES NOT FORCE}'), # ‘⊮’
    MacroTextSpec('nVDash', u'\N{NEGATED DOUBLE VERTICAL BAR DOUBLE RIGHT TURNSTILE}'), # ‘⊯’
    MacroTextSpec('vartriangleleft', u'\N{NORMAL SUBGROUP OF}'), # ‘⊲’
    MacroTextSpec('vartriangleright', u'\N{CONTAINS AS NORMAL SUBGROUP}'), # ‘⊳’
    MacroTextSpec('trianglelefteq', u'\N{NORMAL SUBGROUP OF OR EQUAL TO}'), # ‘⊴’
    MacroTextSpec('trianglerighteq', u'\N{CONTAINS AS NORMAL SUBGROUP OR EQUAL TO}'), # ‘⊵’
    MacroTextSpec('original', u'\N{ORIGINAL OF}'), # ‘⊶’
    MacroTextSpec('image', u'\N{IMAGE OF}'), # ‘⊷’
    MacroTextSpec('multimap', u'\N{MULTIMAP}'), # ‘⊸’
    MacroTextSpec('hermitconjmatrix', u'\N{HERMITIAN CONJUGATE MATRIX}'), # ‘⊹’
    MacroTextSpec('intercal', u'\N{INTERCALATE}'), # ‘⊺’
    MacroTextSpec('veebar', u'\N{XOR}'), # ‘⊻’
    MacroTextSpec('rightanglearc', u'\N{RIGHT ANGLE WITH ARC}'), # ‘⊾’
    MacroTextSpec('bigwedge', u'\N{N-ARY LOGICAL AND}'), # ‘⋀’
    MacroTextSpec('bigvee', u'\N{N-ARY LOGICAL OR}'), # ‘⋁’
    MacroTextSpec('bigcap', u'\N{N-ARY INTERSECTION}'), # ‘⋂’
    MacroTextSpec('bigcup', u'\N{N-ARY UNION}'), # ‘⋃’
    MacroTextSpec('diamond', u'\N{DIAMOND OPERATOR}'), # ‘⋄’
    MacroTextSpec('star', u'\N{STAR OPERATOR}'), # ‘⋆’
    MacroTextSpec('divideontimes', u'\N{DIVISION TIMES}'), # ‘⋇’
    MacroTextSpec('bowtie', u'\N{BOWTIE}'), # ‘⋈’
    MacroTextSpec('ltimes', u'\N{LEFT NORMAL FACTOR SEMIDIRECT PRODUCT}'), # ‘⋉’
    MacroTextSpec('rtimes', u'\N{RIGHT NORMAL FACTOR SEMIDIRECT PRODUCT}'), # ‘⋊’
    MacroTextSpec('leftthreetimes', u'\N{LEFT SEMIDIRECT PRODUCT}'), # ‘⋋’
    MacroTextSpec('rightthreetimes', u'\N{RIGHT SEMIDIRECT PRODUCT}'), # ‘⋌’
    MacroTextSpec('backsimeq', u'\N{REVERSED TILDE EQUALS}'), # ‘⋍’
    MacroTextSpec('curlyvee', u'\N{CURLY LOGICAL OR}'), # ‘⋎’
    MacroTextSpec('curlywedge', u'\N{CURLY LOGICAL AND}'), # ‘⋏’
    MacroTextSpec('Subset', u'\N{DOUBLE SUBSET}'), # ‘⋐’
    MacroTextSpec('Supset', u'\N{DOUBLE SUPERSET}'), # ‘⋑’
    MacroTextSpec('Cap', u'\N{DOUBLE INTERSECTION}'), # ‘⋒’
    MacroTextSpec('Cup', u'\N{DOUBLE UNION}'), # ‘⋓’
    MacroTextSpec('pitchfork', u'\N{PITCHFORK}'), # ‘⋔’
    MacroTextSpec('lessdot', u'\N{LESS-THAN WITH DOT}'), # ‘⋖’
    MacroTextSpec('gtrdot', u'\N{GREATER-THAN WITH DOT}'), # ‘⋗’
    MacroTextSpec('verymuchless', u'\N{VERY MUCH LESS-THAN}'), # ‘⋘’
    MacroTextSpec('verymuchgreater', u'\N{VERY MUCH GREATER-THAN}'), # ‘⋙’
    MacroTextSpec('lesseqgtr', u'\N{LESS-THAN EQUAL TO OR GREATER-THAN}'), # ‘⋚’
    MacroTextSpec('gtreqless', u'\N{GREATER-THAN EQUAL TO OR LESS-THAN}'), # ‘⋛’
    MacroTextSpec('curlyeqprec', u'\N{EQUAL TO OR PRECEDES}'), # ‘⋞’
    MacroTextSpec('curlyeqsucc', u'\N{EQUAL TO OR SUCCEEDS}'), # ‘⋟’
    MacroTextSpec('lnsim', u'\N{LESS-THAN BUT NOT EQUIVALENT TO}'), # ‘⋦’
    MacroTextSpec('gnsim', u'\N{GREATER-THAN BUT NOT EQUIVALENT TO}'), # ‘⋧’
    MacroTextSpec('precedesnotsimilar', u'\N{PRECEDES BUT NOT EQUIVALENT TO}'), # ‘⋨’
    MacroTextSpec('succnsim', u'\N{SUCCEEDS BUT NOT EQUIVALENT TO}'), # ‘⋩’
    MacroTextSpec('ntriangleleft', u'\N{NOT NORMAL SUBGROUP OF}'), # ‘⋪’
    MacroTextSpec('ntriangleright', u'\N{DOES NOT CONTAIN AS NORMAL SUBGROUP}'), # ‘⋫’
    MacroTextSpec('ntrianglelefteq', u'\N{NOT NORMAL SUBGROUP OF OR EQUAL TO}'), # ‘⋬’
    MacroTextSpec('ntrianglerighteq', u'\N{DOES NOT CONTAIN AS NORMAL SUBGROUP OR EQUAL}'), # ‘⋭’
    MacroTextSpec('vdots', u'\N{VERTICAL ELLIPSIS}'), # ‘⋮’
    MacroTextSpec('udots', u'\N{UP RIGHT DIAGONAL ELLIPSIS}'), # ‘⋰’
    MacroTextSpec('barwedge', u'\N{PROJECTIVE}'), # ‘⌅’
    MacroTextSpec('varperspcorrespond', u'\N{PERSPECTIVE}'), # ‘⌆’
    MacroTextSpec('lceil', u'\N{LEFT CEILING}'), # ‘⌈’
    MacroTextSpec('rceil', u'\N{RIGHT CEILING}'), # ‘⌉’
    MacroTextSpec('lfloor', u'\N{LEFT FLOOR}'), # ‘⌊’
    MacroTextSpec('rfloor', u'\N{RIGHT FLOOR}'), # ‘⌋’
    MacroTextSpec('recorder', u'\N{TELEPHONE RECORDER}'), # ‘⌕’
    MacroTextSpec('ulcorner', u'\N{TOP LEFT CORNER}'), # ‘⌜’
    MacroTextSpec('urcorner', u'\N{TOP RIGHT CORNER}'), # ‘⌝’
    MacroTextSpec('llcorner', u'\N{BOTTOM LEFT CORNER}'), # ‘⌞’
    MacroTextSpec('lrcorner', u'\N{BOTTOM RIGHT CORNER}'), # ‘⌟’
    MacroTextSpec('frown', u'\N{FROWN}'), # ‘⌢’
    MacroTextSpec('smile', u'\N{SMILE}'), # ‘⌣’
    MacroTextSpec('lmoustache', u'\N{UPPER LEFT OR LOWER RIGHT CURLY BRACKET SECTION}'), # ‘⎰’
    MacroTextSpec('rmoustache', u'\N{UPPER RIGHT OR LOWER LEFT CURLY BRACKET SECTION}'), # ‘⎱’
    MacroTextSpec('textlangle', u'\N{LEFT-POINTING ANGLE BRACKET}'), # ‘〈’
    MacroTextSpec('textrangle', u'\N{RIGHT-POINTING ANGLE BRACKET}'), # ‘〉’
    MacroTextSpec('textblank', u'\N{BLANK SYMBOL}'), # ‘␢’
    MacroTextSpec('textvisiblespace', u'\N{OPEN BOX}'), # ‘␣’
    MacroTextSpec('blacksquare', u'\N{BLACK SQUARE}'), # ‘■’
    MacroTextSpec('square', u'\N{WHITE SQUARE}'), # ‘□’
    MacroTextSpec('bigtriangleup', u'\N{WHITE UP-POINTING TRIANGLE}'), # ‘△’
    MacroTextSpec('blacktriangle', u'\N{BLACK UP-POINTING SMALL TRIANGLE}'), # ‘▴’
    MacroTextSpec('vartriangle', u'\N{WHITE UP-POINTING SMALL TRIANGLE}'), # ‘▵’
    MacroTextSpec('blacktriangleright', u'\N{BLACK RIGHT-POINTING SMALL TRIANGLE}'), # ‘▸’
    MacroTextSpec('triangleright', u'\N{WHITE RIGHT-POINTING SMALL TRIANGLE}'), # ‘▹’
    MacroTextSpec('bigtriangledown', u'\N{WHITE DOWN-POINTING TRIANGLE}'), # ‘▽’
    MacroTextSpec('blacktriangledown', u'\N{BLACK DOWN-POINTING SMALL TRIANGLE}'), # ‘▾’
    MacroTextSpec('triangledown', u'\N{WHITE DOWN-POINTING SMALL TRIANGLE}'), # ‘▿’
    MacroTextSpec('blacktriangleleft', u'\N{BLACK LEFT-POINTING SMALL TRIANGLE}'), # ‘◂’
    MacroTextSpec('triangleleft', u'\N{WHITE LEFT-POINTING SMALL TRIANGLE}'), # ‘◃’
    MacroTextSpec('lozenge', u'\N{LOZENGE}'), # ‘◊’
    MacroTextSpec('bigcirc', u'\N{WHITE CIRCLE}'), # ‘○’
    MacroTextSpec('textopenbullet', u'\N{WHITE BULLET}'), # ‘◦’
    MacroTextSpec('textbigcircle', u'\N{LARGE CIRCLE}'), # ‘◯’
    MacroTextSpec('diamond', u'\N{WHITE DIAMOND SUIT}'), # ‘♢’
    MacroTextSpec('textmusicalnote', u'\N{EIGHTH NOTE}'), # ‘♪’
    MacroTextSpec('quarternote', u'\N{QUARTER NOTE}'), # ‘♩’
    MacroTextSpec('flat', u'\N{MUSIC FLAT SIGN}'), # ‘♭’
    MacroTextSpec('natural', u'\N{MUSIC NATURAL SIGN}'), # ‘♮’
    MacroTextSpec('sharp', u'\N{MUSIC SHARP SIGN}'), # ‘♯’
    MacroTextSpec('longleftrightarrow', u'\N{LONG LEFT RIGHT ARROW}'), # ‘⟷’
    MacroTextSpec('Longleftarrow', u'\N{LONG LEFTWARDS DOUBLE ARROW}'), # ‘⟸’
    MacroTextSpec('Longrightarrow', u'\N{LONG RIGHTWARDS DOUBLE ARROW}'), # ‘⟹’
    MacroTextSpec('Longleftrightarrow', u'\N{LONG LEFT RIGHT DOUBLE ARROW}'), # ‘⟺’
    MacroTextSpec('longmapsto', u'\N{LONG RIGHTWARDS ARROW FROM BAR}'), # ‘⟼’
    MacroTextSpec('blacklozenge', u'\N{BLACK LOZENGE}'), # ‘⧫’
    MacroTextSpec('clockoint', u'\N{INTEGRAL AVERAGE WITH SLASH}'), # ‘⨏’
    MacroTextSpec('sqrint', u'\N{QUATERNION INTEGRAL OPERATOR}'), # ‘⨖’
    MacroTextSpec('amalg', u'\N{AMALGAMATION OR COPRODUCT}'), # ‘⨿’
    MacroTextSpec('lessapprox', u'\N{LESS-THAN OR APPROXIMATE}'), # ‘⪅’
    MacroTextSpec('gtrapprox', u'\N{GREATER-THAN OR APPROXIMATE}'), # ‘⪆’
    MacroTextSpec('lneq', u'\N{LESS-THAN AND SINGLE-LINE NOT EQUAL TO}'), # ‘⪇’
    MacroTextSpec('gneq', u'\N{GREATER-THAN AND SINGLE-LINE NOT EQUAL TO}'), # ‘⪈’
    MacroTextSpec('lnapprox', u'\N{LESS-THAN AND NOT APPROXIMATE}'), # ‘⪉’
    MacroTextSpec('gnapprox', u'\N{GREATER-THAN AND NOT APPROXIMATE}'), # ‘⪊’
    MacroTextSpec('lesseqqgtr', u'\N{LESS-THAN ABOVE DOUBLE-LINE EQUAL ABOVE GREATER-THAN}'), # ‘⪋’
    MacroTextSpec('gtreqqless', u'\N{GREATER-THAN ABOVE DOUBLE-LINE EQUAL ABOVE LESS-THAN}'), # ‘⪌’
    MacroTextSpec('eqslantless', u'\N{SLANTED EQUAL TO OR LESS-THAN}'), # ‘⪕’
    MacroTextSpec('eqslantgtr', u'\N{SLANTED EQUAL TO OR GREATER-THAN}'), # ‘⪖’
    MacroTextSpec('precneqq', u'\N{PRECEDES ABOVE NOT EQUAL TO}'), # ‘⪵’
    MacroTextSpec('succneqq', u'\N{SUCCEEDS ABOVE NOT EQUAL TO}'), # ‘⪶’
    MacroTextSpec('precapprox', u'\N{PRECEDES ABOVE ALMOST EQUAL TO}'), # ‘⪷’
    MacroTextSpec('succapprox', u'\N{SUCCEEDS ABOVE ALMOST EQUAL TO}'), # ‘⪸’
    MacroTextSpec('precnapprox', u'\N{PRECEDES ABOVE NOT ALMOST EQUAL TO}'), # ‘⪹’
    MacroTextSpec('succnapprox', u'\N{SUCCEEDS ABOVE NOT ALMOST EQUAL TO}'), # ‘⪺’
    MacroTextSpec('subseteqq', u'\N{SUBSET OF ABOVE EQUALS SIGN}'), # ‘⫅’
    MacroTextSpec('supseteqq', u'\N{SUPERSET OF ABOVE EQUALS SIGN}'), # ‘⫆’
    MacroTextSpec('subsetneqq', u'\N{SUBSET OF ABOVE NOT EQUAL TO}'), # ‘⫋’
    MacroTextSpec('supsetneqq', u'\N{SUPERSET OF ABOVE NOT EQUAL TO}'), # ‘⫌’
    # Rules from latexencode defaults 'unicode-xml'
    MacroTextSpec('textdollar', u'\N{DOLLAR SIGN}'), # ‘$’
    MacroTextSpec('textquotesingle', u'\N{APOSTROPHE}'), # ‘'’
    MacroTextSpec('textasciigrave', u'\N{GRAVE ACCENT}'), # ‘`’
    MacroTextSpec('lbrace', u'\N{LEFT CURLY BRACKET}'), # ‘{’
    MacroTextSpec('rbrace', u'\N{RIGHT CURLY BRACKET}'), # ‘}’
    MacroTextSpec('textasciitilde', u'\N{TILDE}'), # ‘~’
    MacroTextSpec('textexclamdown', u'\N{INVERTED EXCLAMATION MARK}'), # ‘¡’
    MacroTextSpec('textcent', u'\N{CENT SIGN}'), # ‘¢’
    MacroTextSpec('textsterling', u'\N{POUND SIGN}'), # ‘£’
    MacroTextSpec('textcurrency', u'\N{CURRENCY SIGN}'), # ‘¤’
    MacroTextSpec('textyen', u'\N{YEN SIGN}'), # ‘¥’
    MacroTextSpec('textbrokenbar', u'\N{BROKEN BAR}'), # ‘¦’
    MacroTextSpec('textsection', u'\N{SECTION SIGN}'), # ‘§’
    MacroTextSpec('textasciidieresis', u'\N{DIAERESIS}'), # ‘¨’
    MacroTextSpec('textcopyright', u'\N{COPYRIGHT SIGN}'), # ‘©’
    MacroTextSpec('textordfeminine', u'\N{FEMININE ORDINAL INDICATOR}'), # ‘ª’
    MacroTextSpec('guillemotleft', u'\N{LEFT-POINTING DOUBLE ANGLE QUOTATION MARK}'), # ‘«’
    MacroTextSpec('lnot', u'\N{NOT SIGN}'), # ‘¬’
    MacroTextSpec('-', u'\N{SOFT HYPHEN}'), # ‘­’
    MacroTextSpec('textregistered', u'\N{REGISTERED SIGN}'), # ‘®’
    MacroTextSpec('textasciimacron', u'\N{MACRON}'), # ‘¯’
    MacroTextSpec('textdegree', u'\N{DEGREE SIGN}'), # ‘°’
    MacroTextSpec('textasciiacute', u'\N{ACUTE ACCENT}'), # ‘´’
    MacroTextSpec('textparagraph', u'\N{PILCROW SIGN}'), # ‘¶’
    MacroTextSpec('textordmasculine', u'\N{MASCULINE ORDINAL INDICATOR}'), # ‘º’
    MacroTextSpec('guillemotright', u'\N{RIGHT-POINTING DOUBLE ANGLE QUOTATION MARK}'), # ‘»’
    MacroTextSpec('textonequarter', u'\N{VULGAR FRACTION ONE QUARTER}'), # ‘¼’
    MacroTextSpec('textonehalf', u'\N{VULGAR FRACTION ONE HALF}'), # ‘½’
    MacroTextSpec('textthreequarters', u'\N{VULGAR FRACTION THREE QUARTERS}'), # ‘¾’
    MacroTextSpec('textquestiondown', u'\N{INVERTED QUESTION MARK}'), # ‘¿’
    MacroTextSpec('DH', u'\N{LATIN CAPITAL LETTER ETH}'), # ‘Ð’
    MacroTextSpec('texttimes', u'\N{MULTIPLICATION SIGN}'), # ‘×’
    MacroTextSpec('TH', u'\N{LATIN CAPITAL LETTER THORN}'), # ‘Þ’
    MacroTextSpec('dh', u'\N{LATIN SMALL LETTER ETH}'), # ‘ð’
    MacroTextSpec('div', u'\N{DIVISION SIGN}'), # ‘÷’
    MacroTextSpec('th', u'\N{LATIN SMALL LETTER THORN}'), # ‘þ’
    MacroTextSpec('DJ', u'\N{LATIN CAPITAL LETTER D WITH STROKE}'), # ‘Đ’
    MacroTextSpec('dj', u'\N{LATIN SMALL LETTER D WITH STROKE}'), # ‘đ’
    MacroTextSpec('NG', u'\N{LATIN CAPITAL LETTER ENG}'), # ‘Ŋ’
    MacroTextSpec('ng', u'\N{LATIN SMALL LETTER ENG}'), # ‘ŋ’
    MacroTextSpec('texthvlig', u'\N{LATIN SMALL LETTER HV}'), # ‘ƕ’
    MacroTextSpec('textnrleg', u'\N{LATIN SMALL LETTER N WITH LONG RIGHT LEG}'), # ‘ƞ’
    MacroTextSpec('eth', u'\N{LATIN LETTER REVERSED ESH LOOP}'), # ‘ƪ’
    MacroTextSpec('textdoublepipe', u'\N{LATIN LETTER ALVEOLAR CLICK}'), # ‘ǂ’
    MacroTextSpec('textphi', u'\N{LATIN SMALL LETTER PHI}'), # ‘ɸ’
    MacroTextSpec('textturnk', u'\N{LATIN SMALL LETTER TURNED K}'), # ‘ʞ’
    MacroTextSpec('textasciicaron', u'\N{CARON}'), # ‘ˇ’
    MacroTextSpec('textasciibreve', u'\N{BREVE}'), # ‘˘’
    MacroTextSpec('textperiodcentered', u'\N{DOT ABOVE}'), # ‘˙’
    MacroTextSpec('texttildelow', u'\N{SMALL TILDE}'), # ‘˜’
    MacroTextSpec('texttheta', u'\N{GREEK SMALL LETTER THETA}'), # ‘θ’
    MacroTextSpec('textvartheta', u'\N{GREEK THETA SYMBOL}'), # ‘ϑ’
    MacroTextSpec('Stigma', u'\N{GREEK LETTER STIGMA}'), # ‘Ϛ’
    MacroTextSpec('Digamma', u'\N{GREEK LETTER DIGAMMA}'), # ‘Ϝ’
    MacroTextSpec('digamma', u'\N{GREEK SMALL LETTER DIGAMMA}'), # ‘ϝ’
    MacroTextSpec('Koppa', u'\N{GREEK LETTER KOPPA}'), # ‘Ϟ’
    MacroTextSpec('Sampi', u'\N{GREEK LETTER SAMPI}'), # ‘Ϡ’
    MacroTextSpec('varkappa', u'\N{GREEK KAPPA SYMBOL}'), # ‘ϰ’
    MacroTextSpec('textTheta', u'\N{GREEK CAPITAL THETA SYMBOL}'), # ‘ϴ’
    MacroTextSpec('backepsilon', u'\N{GREEK REVERSED LUNATE EPSILON SYMBOL}'), # ‘϶’
    MacroTextSpec('textdagger', u'\N{DAGGER}'), # ‘†’
    MacroTextSpec('textdaggerdbl', u'\N{DOUBLE DAGGER}'), # ‘‡’
    MacroTextSpec('textbullet', u'\N{BULLET}'), # ‘•’
    MacroTextSpec('textperthousand', u'\N{PER MILLE SIGN}'), # ‘‰’
    MacroTextSpec('textpertenthousand', u'\N{PER TEN THOUSAND SIGN}'), # ‘‱’
    MacroTextSpec('backprime', u'\N{REVERSED PRIME}'), # ‘‵’
    MacroTextSpec('guilsinglleft', u'\N{SINGLE LEFT-POINTING ANGLE QUOTATION MARK}'), # ‘‹’
    MacroTextSpec('guilsinglright', u'\N{SINGLE RIGHT-POINTING ANGLE QUOTATION MARK}'), # ‘›’
    MacroTextSpec('nolinebreak', u'\N{WORD JOINER}'), # ‘⁠’
    MacroTextSpec('dddot', u'\N{COMBINING THREE DOTS ABOVE}'), # ‘⃛’
    MacroTextSpec('ddddot', u'\N{COMBINING FOUR DOTS ABOVE}'), # ‘⃜’
    MacroTextSpec('hslash', u'\N{PLANCK CONSTANT OVER TWO PI}'), # ‘ℏ’
    MacroTextSpec('wp', u'\N{SCRIPT CAPITAL P}'), # ‘℘’
    MacroTextSpec('texttrademark', u'\N{TRADE MARK SIGN}'), # ‘™’
    MacroTextSpec('mho', u'\N{INVERTED OHM SIGN}'), # ‘℧’
    MacroTextSpec('beth', u'\N{BET SYMBOL}'), # ‘ℶ’
    MacroTextSpec('gimel', u'\N{GIMEL SYMBOL}'), # ‘ℷ’
    MacroTextSpec('daleth', u'\N{DALET SYMBOL}'), # ‘ℸ’
    MacroTextSpec('leftrightarrow', u'\N{LEFT RIGHT ARROW}'), # ‘↔’
    MacroTextSpec('updownarrow', u'\N{UP DOWN ARROW}'), # ‘↕’
    MacroTextSpec('nwarrow', u'\N{NORTH WEST ARROW}'), # ‘↖’
    MacroTextSpec('nearrow', u'\N{NORTH EAST ARROW}'), # ‘↗’
    MacroTextSpec('searrow', u'\N{SOUTH EAST ARROW}'), # ‘↘’
    MacroTextSpec('swarrow', u'\N{SOUTH WEST ARROW}'), # ‘↙’
    MacroTextSpec('nleftarrow', u'\N{LEFTWARDS ARROW WITH STROKE}'), # ‘↚’
    MacroTextSpec('nrightarrow', u'\N{RIGHTWARDS ARROW WITH STROKE}'), # ‘↛’
    MacroTextSpec('arrowwaveleft', u'\N{LEFTWARDS WAVE ARROW}'), # ‘↜’
    MacroTextSpec('arrowwaveright', u'\N{RIGHTWARDS WAVE ARROW}'), # ‘↝’
    MacroTextSpec('twoheadleftarrow', u'\N{LEFTWARDS TWO HEADED ARROW}'), # ‘↞’
    MacroTextSpec('twoheadrightarrow', u'\N{RIGHTWARDS TWO HEADED ARROW}'), # ‘↠’
    MacroTextSpec('leftarrowtail', u'\N{LEFTWARDS ARROW WITH TAIL}'), # ‘↢’
    MacroTextSpec('rightarrowtail', u'\N{RIGHTWARDS ARROW WITH TAIL}'), # ‘↣’
    MacroTextSpec('mapsto', u'\N{RIGHTWARDS ARROW FROM BAR}'), # ‘↦’
    MacroTextSpec('hookleftarrow', u'\N{LEFTWARDS ARROW WITH HOOK}'), # ‘↩’
    MacroTextSpec('hookrightarrow', u'\N{RIGHTWARDS ARROW WITH HOOK}'), # ‘↪’
    MacroTextSpec('looparrowleft', u'\N{LEFTWARDS ARROW WITH LOOP}'), # ‘↫’
    MacroTextSpec('looparrowright', u'\N{RIGHTWARDS ARROW WITH LOOP}'), # ‘↬’
    MacroTextSpec('leftrightsquigarrow', u'\N{LEFT RIGHT WAVE ARROW}'), # ‘↭’
    MacroTextSpec('nleftrightarrow', u'\N{LEFT RIGHT ARROW WITH STROKE}'), # ‘↮’
    MacroTextSpec('Lsh', u'\N{UPWARDS ARROW WITH TIP LEFTWARDS}'), # ‘↰’
    MacroTextSpec('Rsh', u'\N{UPWARDS ARROW WITH TIP RIGHTWARDS}'), # ‘↱’
    MacroTextSpec('curvearrowleft', u'\N{ANTICLOCKWISE TOP SEMICIRCLE ARROW}'), # ‘↶’
    MacroTextSpec('curvearrowright', u'\N{CLOCKWISE TOP SEMICIRCLE ARROW}'), # ‘↷’
    MacroTextSpec('circlearrowleft', u'\N{ANTICLOCKWISE OPEN CIRCLE ARROW}'), # ‘↺’
    MacroTextSpec('circlearrowright', u'\N{CLOCKWISE OPEN CIRCLE ARROW}'), # ‘↻’
    MacroTextSpec('leftharpoonup', u'\N{LEFTWARDS HARPOON WITH BARB UPWARDS}'), # ‘↼’
    MacroTextSpec('leftharpoondown', u'\N{LEFTWARDS HARPOON WITH BARB DOWNWARDS}'), # ‘↽’
    MacroTextSpec('upharpoonright', u'\N{UPWARDS HARPOON WITH BARB RIGHTWARDS}'), # ‘↾’
    MacroTextSpec('upharpoonleft', u'\N{UPWARDS HARPOON WITH BARB LEFTWARDS}'), # ‘↿’
    MacroTextSpec('rightharpoonup', u'\N{RIGHTWARDS HARPOON WITH BARB UPWARDS}'), # ‘⇀’
    MacroTextSpec('rightharpoondown', u'\N{RIGHTWARDS HARPOON WITH BARB DOWNWARDS}'), # ‘⇁’
    MacroTextSpec('downharpoonright', u'\N{DOWNWARDS HARPOON WITH BARB RIGHTWARDS}'), # ‘⇂’
    MacroTextSpec('downharpoonleft', u'\N{DOWNWARDS HARPOON WITH BARB LEFTWARDS}'), # ‘⇃’
    MacroTextSpec('rightleftarrows', u'\N{RIGHTWARDS ARROW OVER LEFTWARDS ARROW}'), # ‘⇄’
    MacroTextSpec('dblarrowupdown', u'\N{UPWARDS ARROW LEFTWARDS OF DOWNWARDS ARROW}'), # ‘⇅’
    MacroTextSpec('leftrightarrows', u'\N{LEFTWARDS ARROW OVER RIGHTWARDS ARROW}'), # ‘⇆’
    MacroTextSpec('leftleftarrows', u'\N{LEFTWARDS PAIRED ARROWS}'), # ‘⇇’
    MacroTextSpec('upuparrows', u'\N{UPWARDS PAIRED ARROWS}'), # ‘⇈’
    MacroTextSpec('rightrightarrows', u'\N{RIGHTWARDS PAIRED ARROWS}'), # ‘⇉’
    MacroTextSpec('downdownarrows', u'\N{DOWNWARDS PAIRED ARROWS}'), # ‘⇊’
    MacroTextSpec('leftrightharpoons', u'\N{LEFTWARDS HARPOON OVER RIGHTWARDS HARPOON}'), # ‘⇋’
    MacroTextSpec('rightleftharpoons', u'\N{RIGHTWARDS HARPOON OVER LEFTWARDS HARPOON}'), # ‘⇌’
    MacroTextSpec('nLeftarrow', u'\N{LEFTWARDS DOUBLE ARROW WITH STROKE}'), # ‘⇍’
    MacroTextSpec('nLeftrightarrow', u'\N{LEFT RIGHT DOUBLE ARROW WITH STROKE}'), # ‘⇎’
    MacroTextSpec('nRightarrow', u'\N{RIGHTWARDS DOUBLE ARROW WITH STROKE}'), # ‘⇏’
    MacroTextSpec('Leftarrow', u'\N{LEFTWARDS DOUBLE ARROW}'), # ‘⇐’
    MacroTextSpec('Uparrow', u'\N{UPWARDS DOUBLE ARROW}'), # ‘⇑’
    MacroTextSpec('Rightarrow', u'\N{RIGHTWARDS DOUBLE ARROW}'), # ‘⇒’
    MacroTextSpec('Downarrow', u'\N{DOWNWARDS DOUBLE ARROW}'), # ‘⇓’
    MacroTextSpec('Leftrightarrow', u'\N{LEFT RIGHT DOUBLE ARROW}'), # ‘⇔’
    MacroTextSpec('Updownarrow', u'\N{UP DOWN DOUBLE ARROW}'), # ‘⇕’
    MacroTextSpec('Lleftarrow', u'\N{LEFTWARDS TRIPLE ARROW}'), # ‘⇚’
    MacroTextSpec('Rrightarrow', u'\N{RIGHTWARDS TRIPLE ARROW}'), # ‘⇛’
    MacroTextSpec('rightsquigarrow', u'\N{RIGHTWARDS SQUIGGLE ARROW}'), # ‘⇝’
    MacroTextSpec('DownArrowUpArrow', u'\N{DOWNWARDS ARROW LEFTWARDS OF UPWARDS ARROW}'), # ‘⇵’
    MacroTextSpec('dotplus', u'\N{DOT PLUS}'), # ‘∔’
    MacroTextSpec('surd', u'\N{SQUARE ROOT}'), # ‘√’
    MacroTextSpec('rightangle', u'\N{RIGHT ANGLE}'), # ‘∟’
    MacroTextSpec('angle', u'\N{ANGLE}'), # ‘∠’
    MacroTextSpec('measuredangle', u'\N{MEASURED ANGLE}'), # ‘∡’
    MacroTextSpec('sphericalangle', u'\N{SPHERICAL ANGLE}'), # ‘∢’
    MacroTextSpec('surfintegral', u'\N{SURFACE INTEGRAL}'), # ‘∯’
    MacroTextSpec('volintegral', u'\N{VOLUME INTEGRAL}'), # ‘∰’
    MacroTextSpec('clwintegral', u'\N{CLOCKWISE INTEGRAL}'), # ‘∱’
    MacroTextSpec('therefore', u'\N{THEREFORE}'), # ‘∴’
    MacroTextSpec('because', u'\N{BECAUSE}'), # ‘∵’
    MacroTextSpec('Colon', u'\N{PROPORTION}'), # ‘∷’
    MacroTextSpec('homothetic', u'\N{HOMOTHETIC}'), # ‘∻’
    MacroTextSpec('lazysinv', u'\N{INVERTED LAZY S}'), # ‘∾’
    MacroTextSpec('wr', u'\N{WREATH PRODUCT}'), # ‘≀’
    MacroTextSpec('cong', u'\N{APPROXIMATELY EQUAL TO}'), # ‘≅’
    MacroTextSpec('approxnotequal', u'\N{APPROXIMATELY BUT NOT ACTUALLY EQUAL TO}'), # ‘≆’
    MacroTextSpec('approxeq', u'\N{ALMOST EQUAL OR EQUAL TO}'), # ‘≊’
    MacroTextSpec('tildetrpl', u'\N{TRIPLE TILDE}'), # ‘≋’
    MacroTextSpec('allequal', u'\N{ALL EQUAL TO}'), # ‘≌’
    MacroTextSpec('asymp', u'\N{EQUIVALENT TO}'), # ‘≍’
    MacroTextSpec('Bumpeq', u'\N{GEOMETRICALLY EQUIVALENT TO}'), # ‘≎’
    MacroTextSpec('bumpeq', u'\N{DIFFERENCE BETWEEN}'), # ‘≏’
    MacroTextSpec('doteq', u'\N{APPROACHES THE LIMIT}'), # ‘≐’
    MacroTextSpec('doteqdot', u'\N{GEOMETRICALLY EQUAL TO}'), # ‘≑’
    MacroTextSpec('fallingdotseq', u'\N{APPROXIMATELY EQUAL TO OR THE IMAGE OF}'), # ‘≒’
    MacroTextSpec('risingdotseq', u'\N{IMAGE OF OR APPROXIMATELY EQUAL TO}'), # ‘≓’
    MacroTextSpec('eqcirc', u'\N{RING IN EQUAL TO}'), # ‘≖’
    MacroTextSpec('circeq', u'\N{RING EQUAL TO}'), # ‘≗’
    MacroTextSpec('estimates', u'\N{ESTIMATES}'), # ‘≙’
    MacroTextSpec('starequal', u'\N{STAR EQUALS}'), # ‘≛’
    MacroTextSpec('triangleq', u'\N{DELTA EQUAL TO}'), # ‘≜’
    MacroTextSpec('between', u'\N{BETWEEN}'), # ‘≬’
    MacroTextSpec('lessequivlnt', u'\N{LESS-THAN OR EQUIVALENT TO}'), # ‘≲’
    MacroTextSpec('greaterequivlnt', u'\N{GREATER-THAN OR EQUIVALENT TO}'), # ‘≳’
    MacroTextSpec('notlessgreater', u'\N{NEITHER LESS-THAN NOR GREATER-THAN}'), # ‘≸’
    MacroTextSpec('notgreaterless', u'\N{NEITHER GREATER-THAN NOR LESS-THAN}'), # ‘≹’
    MacroTextSpec('preccurlyeq', u'\N{PRECEDES OR EQUAL TO}'), # ‘≼’
    MacroTextSpec('succcurlyeq', u'\N{SUCCEEDS OR EQUAL TO}'), # ‘≽’
    MacroTextSpec('precapprox', u'\N{PRECEDES OR EQUIVALENT TO}'), # ‘≾’
    MacroTextSpec('succapprox', u'\N{SUCCEEDS OR EQUIVALENT TO}'), # ‘≿’
    MacroTextSpec('uplus', u'\N{MULTISET UNION}'), # ‘⊎’
    MacroTextSpec('sqsubset', u'\N{SQUARE IMAGE OF}'), # ‘⊏’
    MacroTextSpec('sqsupset', u'\N{SQUARE ORIGINAL OF}'), # ‘⊐’
    MacroTextSpec('sqsubseteq', u'\N{SQUARE IMAGE OF OR EQUAL TO}'), # ‘⊑’
    MacroTextSpec('sqsupseteq', u'\N{SQUARE ORIGINAL OF OR EQUAL TO}'), # ‘⊒’
    MacroTextSpec('sqcap', u'\N{SQUARE CAP}'), # ‘⊓’
    MacroTextSpec('sqcup', u'\N{SQUARE CUP}'), # ‘⊔’
    MacroTextSpec('ominus', u'\N{CIRCLED MINUS}'), # ‘⊖’
    MacroTextSpec('oslash', u'\N{CIRCLED DIVISION SLASH}'), # ‘⊘’
    MacroTextSpec('odot', u'\N{CIRCLED DOT OPERATOR}'), # ‘⊙’
    MacroTextSpec('circledcirc', u'\N{CIRCLED RING OPERATOR}'), # ‘⊚’
    MacroTextSpec('circledast', u'\N{CIRCLED ASTERISK OPERATOR}'), # ‘⊛’
    MacroTextSpec('circleddash', u'\N{CIRCLED DASH}'), # ‘⊝’
    MacroTextSpec('boxplus', u'\N{SQUARED PLUS}'), # ‘⊞’
    MacroTextSpec('boxminus', u'\N{SQUARED MINUS}'), # ‘⊟’
    MacroTextSpec('boxtimes', u'\N{SQUARED TIMES}'), # ‘⊠’
    MacroTextSpec('boxdot', u'\N{SQUARED DOT OPERATOR}'), # ‘⊡’
    MacroTextSpec('vdash', u'\N{RIGHT TACK}'), # ‘⊢’
    MacroTextSpec('dashv', u'\N{LEFT TACK}'), # ‘⊣’
    MacroTextSpec('top', u'\N{DOWN TACK}'), # ‘⊤’
    MacroTextSpec('perp', u'\N{UP TACK}'), # ‘⊥’
    MacroTextSpec('truestate', u'\N{MODELS}'), # ‘⊧’
    MacroTextSpec('forcesextra', u'\N{TRUE}'), # ‘⊨’
    MacroTextSpec('Vdash', u'\N{FORCES}'), # ‘⊩’
    MacroTextSpec('Vvdash', u'\N{TRIPLE VERTICAL BAR RIGHT TURNSTILE}'), # ‘⊪’
    MacroTextSpec('VDash', u'\N{DOUBLE VERTICAL BAR DOUBLE RIGHT TURNSTILE}'), # ‘⊫’
    MacroTextSpec('nvdash', u'\N{DOES NOT PROVE}'), # ‘⊬’
    MacroTextSpec('nvDash', u'\N{NOT TRUE}'), # ‘⊭’
    MacroTextSpec('nVdash', u'\N{DOES NOT FORCE}'), # ‘⊮’
    MacroTextSpec('nVDash', u'\N{NEGATED DOUBLE VERTICAL BAR DOUBLE RIGHT TURNSTILE}'), # ‘⊯’
    MacroTextSpec('vartriangleleft', u'\N{NORMAL SUBGROUP OF}'), # ‘⊲’
    MacroTextSpec('vartriangleright', u'\N{CONTAINS AS NORMAL SUBGROUP}'), # ‘⊳’
    MacroTextSpec('trianglelefteq', u'\N{NORMAL SUBGROUP OF OR EQUAL TO}'), # ‘⊴’
    MacroTextSpec('trianglerighteq', u'\N{CONTAINS AS NORMAL SUBGROUP OR EQUAL TO}'), # ‘⊵’
    MacroTextSpec('original', u'\N{ORIGINAL OF}'), # ‘⊶’
    MacroTextSpec('image', u'\N{IMAGE OF}'), # ‘⊷’
    MacroTextSpec('multimap', u'\N{MULTIMAP}'), # ‘⊸’
    MacroTextSpec('hermitconjmatrix', u'\N{HERMITIAN CONJUGATE MATRIX}'), # ‘⊹’
    MacroTextSpec('intercal', u'\N{INTERCALATE}'), # ‘⊺’
    MacroTextSpec('veebar', u'\N{XOR}'), # ‘⊻’
    MacroTextSpec('rightanglearc', u'\N{RIGHT ANGLE WITH ARC}'), # ‘⊾’
    MacroTextSpec('bigcap', u'\N{N-ARY INTERSECTION}'), # ‘⋂’
    MacroTextSpec('bigcup', u'\N{N-ARY UNION}'), # ‘⋃’
    MacroTextSpec('diamond', u'\N{DIAMOND OPERATOR}'), # ‘⋄’
    MacroTextSpec('star', u'\N{STAR OPERATOR}'), # ‘⋆’
    MacroTextSpec('divideontimes', u'\N{DIVISION TIMES}'), # ‘⋇’
    MacroTextSpec('bowtie', u'\N{BOWTIE}'), # ‘⋈’
    MacroTextSpec('ltimes', u'\N{LEFT NORMAL FACTOR SEMIDIRECT PRODUCT}'), # ‘⋉’
    MacroTextSpec('rtimes', u'\N{RIGHT NORMAL FACTOR SEMIDIRECT PRODUCT}'), # ‘⋊’
    MacroTextSpec('leftthreetimes', u'\N{LEFT SEMIDIRECT PRODUCT}'), # ‘⋋’
    MacroTextSpec('rightthreetimes', u'\N{RIGHT SEMIDIRECT PRODUCT}'), # ‘⋌’
    MacroTextSpec('backsimeq', u'\N{REVERSED TILDE EQUALS}'), # ‘⋍’
    MacroTextSpec('curlyvee', u'\N{CURLY LOGICAL OR}'), # ‘⋎’
    MacroTextSpec('curlywedge', u'\N{CURLY LOGICAL AND}'), # ‘⋏’
    MacroTextSpec('Subset', u'\N{DOUBLE SUBSET}'), # ‘⋐’
    MacroTextSpec('Supset', u'\N{DOUBLE SUPERSET}'), # ‘⋑’
    MacroTextSpec('Cap', u'\N{DOUBLE INTERSECTION}'), # ‘⋒’
    MacroTextSpec('Cup', u'\N{DOUBLE UNION}'), # ‘⋓’
    MacroTextSpec('pitchfork', u'\N{PITCHFORK}'), # ‘⋔’
    MacroTextSpec('lessdot', u'\N{LESS-THAN WITH DOT}'), # ‘⋖’
    MacroTextSpec('gtrdot', u'\N{GREATER-THAN WITH DOT}'), # ‘⋗’
    MacroTextSpec('verymuchless', u'\N{VERY MUCH LESS-THAN}'), # ‘⋘’
    MacroTextSpec('verymuchgreater', u'\N{VERY MUCH GREATER-THAN}'), # ‘⋙’
    MacroTextSpec('lesseqgtr', u'\N{LESS-THAN EQUAL TO OR GREATER-THAN}'), # ‘⋚’
    MacroTextSpec('gtreqless', u'\N{GREATER-THAN EQUAL TO OR LESS-THAN}'), # ‘⋛’
    MacroTextSpec('curlyeqprec', u'\N{EQUAL TO OR PRECEDES}'), # ‘⋞’
    MacroTextSpec('curlyeqsucc', u'\N{EQUAL TO OR SUCCEEDS}'), # ‘⋟’
    MacroTextSpec('lnsim', u'\N{LESS-THAN BUT NOT EQUIVALENT TO}'), # ‘⋦’
    MacroTextSpec('gnsim', u'\N{GREATER-THAN BUT NOT EQUIVALENT TO}'), # ‘⋧’
    MacroTextSpec('precedesnotsimilar', u'\N{PRECEDES BUT NOT EQUIVALENT TO}'), # ‘⋨’
    MacroTextSpec('succnsim', u'\N{SUCCEEDS BUT NOT EQUIVALENT TO}'), # ‘⋩’
    MacroTextSpec('ntriangleleft', u'\N{NOT NORMAL SUBGROUP OF}'), # ‘⋪’
    MacroTextSpec('ntriangleright', u'\N{DOES NOT CONTAIN AS NORMAL SUBGROUP}'), # ‘⋫’
    MacroTextSpec('ntrianglelefteq', u'\N{NOT NORMAL SUBGROUP OF OR EQUAL TO}'), # ‘⋬’
    MacroTextSpec('ntrianglerighteq', u'\N{DOES NOT CONTAIN AS NORMAL SUBGROUP OR EQUAL}'), # ‘⋭’
    MacroTextSpec('vdots', u'\N{VERTICAL ELLIPSIS}'), # ‘⋮’
    MacroTextSpec('upslopeellipsis', u'\N{UP RIGHT DIAGONAL ELLIPSIS}'), # ‘⋰’
    MacroTextSpec('downslopeellipsis', u'\N{DOWN RIGHT DIAGONAL ELLIPSIS}'), # ‘⋱’
    MacroTextSpec('barwedge', u'\N{PROJECTIVE}'), # ‘⌅’
    MacroTextSpec('varperspcorrespond', u'\N{PERSPECTIVE}'), # ‘⌆’
    MacroTextSpec('lceil', u'\N{LEFT CEILING}'), # ‘⌈’
    MacroTextSpec('rceil', u'\N{RIGHT CEILING}'), # ‘⌉’
    MacroTextSpec('lfloor', u'\N{LEFT FLOOR}'), # ‘⌊’
    MacroTextSpec('rfloor', u'\N{RIGHT FLOOR}'), # ‘⌋’
    MacroTextSpec('recorder', u'\N{TELEPHONE RECORDER}'), # ‘⌕’
    MacroTextSpec('ulcorner', u'\N{TOP LEFT CORNER}'), # ‘⌜’
    MacroTextSpec('urcorner', u'\N{TOP RIGHT CORNER}'), # ‘⌝’
    MacroTextSpec('llcorner', u'\N{BOTTOM LEFT CORNER}'), # ‘⌞’
    MacroTextSpec('lrcorner', u'\N{BOTTOM RIGHT CORNER}'), # ‘⌟’
    MacroTextSpec('frown', u'\N{FROWN}'), # ‘⌢’
    MacroTextSpec('smile', u'\N{SMILE}'), # ‘⌣’
    MacroTextSpec('lmoustache', u'\N{UPPER LEFT OR LOWER RIGHT CURLY BRACKET SECTION}'), # ‘⎰’
    MacroTextSpec('rmoustache', u'\N{UPPER RIGHT OR LOWER LEFT CURLY BRACKET SECTION}'), # ‘⎱’
    MacroTextSpec('textvisiblespace', u'\N{OPEN BOX}'), # ‘␣’
    MacroTextSpec('circledS', u'\N{CIRCLED LATIN CAPITAL LETTER S}'), # ‘Ⓢ’
    MacroTextSpec('diagup', u'\N{BOX DRAWINGS LIGHT DIAGONAL UPPER RIGHT TO LOWER LEFT}'), # ‘╱’
    MacroTextSpec('square', u'\N{WHITE SQUARE}'), # ‘□’
    MacroTextSpec('blacksquare', u'\N{BLACK SMALL SQUARE}'), # ‘▪’
    MacroTextSpec('bigtriangleup', u'\N{WHITE UP-POINTING TRIANGLE}'), # ‘△’
    MacroTextSpec('blacktriangle', u'\N{BLACK UP-POINTING SMALL TRIANGLE}'), # ‘▴’
    MacroTextSpec('vartriangle', u'\N{WHITE UP-POINTING SMALL TRIANGLE}'), # ‘▵’
    MacroTextSpec('blacktriangleright', u'\N{BLACK RIGHT-POINTING SMALL TRIANGLE}'), # ‘▸’
    MacroTextSpec('triangleright', u'\N{WHITE RIGHT-POINTING SMALL TRIANGLE}'), # ‘▹’
    MacroTextSpec('bigtriangledown', u'\N{WHITE DOWN-POINTING TRIANGLE}'), # ‘▽’
    MacroTextSpec('blacktriangledown', u'\N{BLACK DOWN-POINTING SMALL TRIANGLE}'), # ‘▾’
    MacroTextSpec('triangledown', u'\N{WHITE DOWN-POINTING SMALL TRIANGLE}'), # ‘▿’
    MacroTextSpec('blacktriangleleft', u'\N{BLACK LEFT-POINTING SMALL TRIANGLE}'), # ‘◂’
    MacroTextSpec('triangleleft', u'\N{WHITE LEFT-POINTING SMALL TRIANGLE}'), # ‘◃’
    MacroTextSpec('lozenge', u'\N{LOZENGE}'), # ‘◊’
    MacroTextSpec('bigcirc', u'\N{WHITE CIRCLE}'), # ‘○’
    MacroTextSpec('bigcirc', u'\N{LARGE CIRCLE}'), # ‘◯’
    MacroTextSpec('rightmoon', u'\N{LAST QUARTER MOON}'), # ‘☾’
    MacroTextSpec('mercury', u'\N{MERCURY}'), # ‘☿’
    MacroTextSpec('venus', u'\N{FEMALE SIGN}'), # ‘♀’
    MacroTextSpec('male', u'\N{MALE SIGN}'), # ‘♂’
    MacroTextSpec('jupiter', u'\N{JUPITER}'), # ‘♃’
    MacroTextSpec('saturn', u'\N{SATURN}'), # ‘♄’
    MacroTextSpec('uranus', u'\N{URANUS}'), # ‘♅’
    MacroTextSpec('neptune', u'\N{NEPTUNE}'), # ‘♆’
    MacroTextSpec('pluto', u'\N{PLUTO}'), # ‘♇’
    MacroTextSpec('aries', u'\N{ARIES}'), # ‘♈’
    MacroTextSpec('taurus', u'\N{TAURUS}'), # ‘♉’
    MacroTextSpec('gemini', u'\N{GEMINI}'), # ‘♊’
    MacroTextSpec('cancer', u'\N{CANCER}'), # ‘♋’
    MacroTextSpec('leo', u'\N{LEO}'), # ‘♌’
    MacroTextSpec('virgo', u'\N{VIRGO}'), # ‘♍’
    MacroTextSpec('libra', u'\N{LIBRA}'), # ‘♎’
    MacroTextSpec('scorpio', u'\N{SCORPIUS}'), # ‘♏’
    MacroTextSpec('sagittarius', u'\N{SAGITTARIUS}'), # ‘♐’
    MacroTextSpec('capricornus', u'\N{CAPRICORN}'), # ‘♑’
    MacroTextSpec('aquarius', u'\N{AQUARIUS}'), # ‘♒’
    MacroTextSpec('pisces', u'\N{PISCES}'), # ‘♓’
    MacroTextSpec('diamond', u'\N{WHITE DIAMOND SUIT}'), # ‘♢’
    MacroTextSpec('quarternote', u'\N{QUARTER NOTE}'), # ‘♩’
    MacroTextSpec('eighthnote', u'\N{EIGHTH NOTE}'), # ‘♪’
    MacroTextSpec('flat', u'\N{MUSIC FLAT SIGN}'), # ‘♭’
    MacroTextSpec('natural', u'\N{MUSIC NATURAL SIGN}'), # ‘♮’
    MacroTextSpec('sharp', u'\N{MUSIC SHARP SIGN}'), # ‘♯’
    MacroTextSpec('longleftrightarrow', u'\N{LONG LEFT RIGHT ARROW}'), # ‘⟷’
    MacroTextSpec('Longleftarrow', u'\N{LONG LEFTWARDS DOUBLE ARROW}'), # ‘⟸’
    MacroTextSpec('Longrightarrow', u'\N{LONG RIGHTWARDS DOUBLE ARROW}'), # ‘⟹’
    MacroTextSpec('Longleftrightarrow', u'\N{LONG LEFT RIGHT DOUBLE ARROW}'), # ‘⟺’
    MacroTextSpec('longmapsto', u'\N{LONG RIGHTWARDS ARROW FROM BAR}'), # ‘⟼’
    MacroTextSpec('UpArrowBar', u'\N{UPWARDS ARROW TO BAR}'), # ‘⤒’
    MacroTextSpec('DownArrowBar', u'\N{DOWNWARDS ARROW TO BAR}'), # ‘⤓’
    MacroTextSpec('LeftRightVector', u'\N{LEFT BARB UP RIGHT BARB UP HARPOON}'), # ‘⥎’
    MacroTextSpec('RightUpDownVector', u'\N{UP BARB RIGHT DOWN BARB RIGHT HARPOON}'), # ‘⥏’
    MacroTextSpec('DownLeftRightVector', u'\N{LEFT BARB DOWN RIGHT BARB DOWN HARPOON}'), # ‘⥐’
    MacroTextSpec('LeftUpDownVector', u'\N{UP BARB LEFT DOWN BARB LEFT HARPOON}'), # ‘⥑’
    MacroTextSpec('LeftVectorBar', u'\N{LEFTWARDS HARPOON WITH BARB UP TO BAR}'), # ‘⥒’
    MacroTextSpec('RightVectorBar', u'\N{RIGHTWARDS HARPOON WITH BARB UP TO BAR}'), # ‘⥓’
    MacroTextSpec('RightUpVectorBar', u'\N{UPWARDS HARPOON WITH BARB RIGHT TO BAR}'), # ‘⥔’
    MacroTextSpec('RightDownVectorBar', u'\N{DOWNWARDS HARPOON WITH BARB RIGHT TO BAR}'), # ‘⥕’
    MacroTextSpec('DownLeftVectorBar', u'\N{LEFTWARDS HARPOON WITH BARB DOWN TO BAR}'), # ‘⥖’
    MacroTextSpec('DownRightVectorBar', u'\N{RIGHTWARDS HARPOON WITH BARB DOWN TO BAR}'), # ‘⥗’
    MacroTextSpec('LeftUpVectorBar', u'\N{UPWARDS HARPOON WITH BARB LEFT TO BAR}'), # ‘⥘’
    MacroTextSpec('LeftDownVectorBar', u'\N{DOWNWARDS HARPOON WITH BARB LEFT TO BAR}'), # ‘⥙’
    MacroTextSpec('LeftTeeVector', u'\N{LEFTWARDS HARPOON WITH BARB UP FROM BAR}'), # ‘⥚’
    MacroTextSpec('RightTeeVector', u'\N{RIGHTWARDS HARPOON WITH BARB UP FROM BAR}'), # ‘⥛’
    MacroTextSpec('RightUpTeeVector', u'\N{UPWARDS HARPOON WITH BARB RIGHT FROM BAR}'), # ‘⥜’
    MacroTextSpec('RightDownTeeVector', u'\N{DOWNWARDS HARPOON WITH BARB RIGHT FROM BAR}'), # ‘⥝’
    MacroTextSpec('DownLeftTeeVector', u'\N{LEFTWARDS HARPOON WITH BARB DOWN FROM BAR}'), # ‘⥞’
    MacroTextSpec('DownRightTeeVector', u'\N{RIGHTWARDS HARPOON WITH BARB DOWN FROM BAR}'), # ‘⥟’
    MacroTextSpec('LeftUpTeeVector', u'\N{UPWARDS HARPOON WITH BARB LEFT FROM BAR}'), # ‘⥠’
    MacroTextSpec('LeftDownTeeVector', u'\N{DOWNWARDS HARPOON WITH BARB LEFT FROM BAR}'), # ‘⥡’
    MacroTextSpec('UpEquilibrium', u'\N{UPWARDS HARPOON WITH BARB LEFT BESIDE DOWNWARDS HARPOON WITH BARB RIGHT}'), # ‘⥮’
    MacroTextSpec('ReverseUpEquilibrium', u'\N{DOWNWARDS HARPOON WITH BARB LEFT BESIDE UPWARDS HARPOON WITH BARB RIGHT}'), # ‘⥯’
    MacroTextSpec('RoundImplies', u'\N{RIGHT DOUBLE ARROW WITH ROUNDED HEAD}'), # ‘⥰’
    MacroTextSpec('Angle', u'\N{RIGHT ANGLE VARIANT WITH SQUARE}'), # ‘⦜’
    MacroTextSpec('LeftTriangleBar', u'\N{LEFT TRIANGLE BESIDE VERTICAL BAR}'), # ‘⧏’
    MacroTextSpec('RightTriangleBar', u'\N{VERTICAL BAR BESIDE RIGHT TRIANGLE}'), # ‘⧐’
    MacroTextSpec('blacklozenge', u'\N{BLACK LOZENGE}'), # ‘⧫’
    MacroTextSpec('RuleDelayed', u'\N{RULE-DELAYED}'), # ‘⧴’
    MacroTextSpec('clockoint', u'\N{INTEGRAL AVERAGE WITH SLASH}'), # ‘⨏’
    MacroTextSpec('sqrint', u'\N{QUATERNION INTEGRAL OPERATOR}'), # ‘⨖’
    MacroTextSpec('amalg', u'\N{AMALGAMATION OR COPRODUCT}'), # ‘⨿’
    MacroTextSpec('perspcorrespond', u'\N{LOGICAL AND WITH DOUBLE OVERBAR}'), # ‘⩞’
    MacroTextSpec('Equal', u'\N{TWO CONSECUTIVE EQUALS SIGNS}'), # ‘⩵’
    MacroTextSpec('lessapprox', u'\N{LESS-THAN OR APPROXIMATE}'), # ‘⪅’
    MacroTextSpec('gtrapprox', u'\N{GREATER-THAN OR APPROXIMATE}'), # ‘⪆’
    MacroTextSpec('lneq', u'\N{LESS-THAN AND SINGLE-LINE NOT EQUAL TO}'), # ‘⪇’
    MacroTextSpec('gneq', u'\N{GREATER-THAN AND SINGLE-LINE NOT EQUAL TO}'), # ‘⪈’
    MacroTextSpec('lnapprox', u'\N{LESS-THAN AND NOT APPROXIMATE}'), # ‘⪉’
    MacroTextSpec('gnapprox', u'\N{GREATER-THAN AND NOT APPROXIMATE}'), # ‘⪊’
    MacroTextSpec('lesseqqgtr', u'\N{LESS-THAN ABOVE DOUBLE-LINE EQUAL ABOVE GREATER-THAN}'), # ‘⪋’
    MacroTextSpec('gtreqqless', u'\N{GREATER-THAN ABOVE DOUBLE-LINE EQUAL ABOVE LESS-THAN}'), # ‘⪌’
    MacroTextSpec('eqslantless', u'\N{SLANTED EQUAL TO OR LESS-THAN}'), # ‘⪕’
    MacroTextSpec('eqslantgtr', u'\N{SLANTED EQUAL TO OR GREATER-THAN}'), # ‘⪖’
    MacroTextSpec('NestedLessLess', u'\N{DOUBLE NESTED LESS-THAN}'), # ‘⪡’
    MacroTextSpec('NestedGreaterGreater', u'\N{DOUBLE NESTED GREATER-THAN}'), # ‘⪢’
    MacroTextSpec('precneqq', u'\N{PRECEDES ABOVE NOT EQUAL TO}'), # ‘⪵’
    MacroTextSpec('succneqq', u'\N{SUCCEEDS ABOVE NOT EQUAL TO}'), # ‘⪶’
    MacroTextSpec('precapprox', u'\N{PRECEDES ABOVE ALMOST EQUAL TO}'), # ‘⪷’
    MacroTextSpec('succapprox', u'\N{SUCCEEDS ABOVE ALMOST EQUAL TO}'), # ‘⪸’
    MacroTextSpec('precnapprox', u'\N{PRECEDES ABOVE NOT ALMOST EQUAL TO}'), # ‘⪹’
    MacroTextSpec('succnapprox', u'\N{SUCCEEDS ABOVE NOT ALMOST EQUAL TO}'), # ‘⪺’
    MacroTextSpec('subseteqq', u'\N{SUBSET OF ABOVE EQUALS SIGN}'), # ‘⫅’
    MacroTextSpec('supseteqq', u'\N{SUPERSET OF ABOVE EQUALS SIGN}'), # ‘⫆’
    MacroTextSpec('subsetneqq', u'\N{SUBSET OF ABOVE NOT EQUAL TO}'), # ‘⫋’
    MacroTextSpec('supsetneqq', u'\N{SUPERSET OF ABOVE NOT EQUAL TO}'), # ‘⫌’
    MacroTextSpec('openbracketleft', u'\N{LEFT WHITE SQUARE BRACKET}'), # ‘〚’
    MacroTextSpec('openbracketright', u'\N{RIGHT WHITE SQUARE BRACKET}'), # ‘〛’
]

# ==============================================================================


specs = [
    #
    # CATEGORY: latex-base
    #
    ('latex-base', _latex_specs_base),

    #
    # CATEGORY: latex-approximations
    #
    ('latex-approximations', _latex_specs_approximations),

    #
    # CATEGORY: latex-placeholders
    #
    ('latex-placeholders', _latex_specs_placeholders),

    #
    # CATEGORY: nonascii-specials
    #
    ('nonascii-specials', {
        'macros': [],
        'environments': [],
        'specials': [
            SpecialsTextSpec('~', u"\N{NO-BREAK SPACE}"),
            SpecialsTextSpec('``', u"\N{LEFT DOUBLE QUOTATION MARK}"),
            SpecialsTextSpec("''", u"\N{RIGHT DOUBLE QUOTATION MARK}"),
            SpecialsTextSpec("--", u"\N{EN DASH}"),
            SpecialsTextSpec("---", u"\N{EM DASH}"),
            SpecialsTextSpec("!`", u"\N{INVERTED EXCLAMATION MARK}"),
            SpecialsTextSpec("?`", u"\N{INVERTED QUESTION MARK}"),
        ]
    }),

    #
    # CATEGORY: advanced-symbols
    #
    ('advanced-symbols', {
        'macros': advanced_symbols_macros,
        'environments': [],
        'specials': [],
    }),

    #
    # CATEGORY: latex-ethuebung
    #
    # expect these to be removed in a future version.  These definitions should
    # be manually included in the applications where they are relevant.
    ('latex-ethuebung', {
        'macros': [
            MacroTextSpec('exercise', simplify_repl=_format_uebung),
            MacroTextSpec('uebung', simplify_repl=_format_uebung),
            MacroTextSpec('hint', 'Hint: %s'),
            MacroTextSpec('hints', 'Hints: %s'),
            MacroTextSpec('hinweis', 'Hinweis: %s'),
            MacroTextSpec('hinweise', 'Hinweise: %s'),
        ],
        'environments': [],
        'specials': []
    }),

    #
    # CATEGORY: nonstandard-qit
    #
    # expect these to be removed in a future version.  These definitions should
    # be manually included in the applications where they are relevant.
    ('nonstandard-qit', {
        'environments': [],
        'specials': [],
        'macros': [
            # we use these conventions as Identity operator (\mathbbm{1})
            MacroTextSpec('id', u'\N{MATHEMATICAL DOUBLE-STRUCK CAPITAL I}'),
            MacroTextSpec('Ident', u'\N{MATHEMATICAL DOUBLE-STRUCK CAPITAL I}'),
        ]
    }),

]





def _greekletters(letterlist):
    for l in letterlist:
        ucharname = l.upper()
        if ucharname == 'LAMBDA':
            ucharname = 'LAMDA'
        smallname = "GREEK SMALL LETTER "+ucharname
        if ucharname == 'EPSILON':
            smallname = "GREEK LUNATE EPSILON SYMBOL"
        if ucharname == 'PHI':
            smallname = "GREEK PHI SYMBOL"
        _latex_specs_base['macros'].append(
            MacroTextSpec(l, unicodedata.lookup(smallname))
        )
        _latex_specs_base['macros'].append(
            MacroTextSpec(l[0].upper()+l[1:], unicodedata.lookup("GREEK CAPITAL LETTER "+ucharname))
            )
_greekletters(
    ('alpha', 'beta', 'gamma', 'delta', 'epsilon', 'zeta', 'eta', 'theta', 'iota', 'kappa',
     'lambda', 'mu', 'nu', 'xi', 'omicron', 'pi', 'rho', 'sigma', 'tau', 'upsilon', 'phi',
     'chi', 'psi', 'omega')
)
_latex_specs_base['macros'] += [
    MacroTextSpec('varepsilon', u'\N{GREEK SMALL LETTER EPSILON}'),
    MacroTextSpec('vartheta', u'\N{GREEK THETA SYMBOL}'),
    MacroTextSpec('varpi', u'\N{GREEK PI SYMBOL}'),
    MacroTextSpec('varrho', u'\N{GREEK RHO SYMBOL}'),
    MacroTextSpec('varsigma', u'\N{GREEK SMALL LETTER FINAL SIGMA}'),
    MacroTextSpec('varphi', u'\N{GREEK SMALL LETTER PHI}'),
    ]


unicode_accents_list = (
    # see http://en.wikibooks.org/wiki/LaTeX/Special_Characters for a list
    ("'", u"\N{COMBINING ACUTE ACCENT}"),
    ("`", u"\N{COMBINING GRAVE ACCENT}"),
    ('"', u"\N{COMBINING DIAERESIS}"),
    ("c", u"\N{COMBINING CEDILLA}"),
    ("^", u"\N{COMBINING CIRCUMFLEX ACCENT}"),
    ("~", u"\N{COMBINING TILDE}"),
    ("H", u"\N{COMBINING DOUBLE ACUTE ACCENT}"),
    ("k", u"\N{COMBINING OGONEK}"),
    ("=", u"\N{COMBINING MACRON}"),
    ("b", u"\N{COMBINING MACRON BELOW}"),
    (".", u"\N{COMBINING DOT ABOVE}"),
    ("d", u"\N{COMBINING DOT BELOW}"),
    ("r", u"\N{COMBINING RING ABOVE}"),
    ("u", u"\N{COMBINING BREVE}"),
    ("v", u"\N{COMBINING CARON}"),

    ("vec", u"\N{COMBINING RIGHT ARROW ABOVE}"),
    ("dot", u"\N{COMBINING DOT ABOVE}"),
    ("hat", u"\N{COMBINING CIRCUMFLEX ACCENT}"),
    ("check", u"\N{COMBINING CARON}"),
    ("breve", u"\N{COMBINING BREVE}"),
    ("acute", u"\N{COMBINING ACUTE ACCENT}"),
    ("grave", u"\N{COMBINING GRAVE ACCENT}"),
    ("tilde", u"\N{COMBINING TILDE}"),
    ("bar", u"\N{COMBINING OVERLINE}"),
    ("ddot", u"\N{COMBINING DIAERESIS}"),

    ("not", u"\N{COMBINING LONG SOLIDUS OVERLAY}"),

    )

def make_accented_char(node, combining, l2tobj):
    if node.nodeargs and len(node.nodeargs):
        nodearg = node.nodeargs[0]
        c = l2tobj.nodelist_to_text([nodearg]).strip()
    else:
        c = ' '

    def getaccented(ch, combining):
        ch = unicode(ch)
        combining = unicode(combining)
        if (ch == u"\N{LATIN SMALL LETTER DOTLESS I}"):
            ch = u"i"
        if (ch == u"\N{LATIN SMALL LETTER DOTLESS J}"):
            ch = u"j"
        #print u"Accenting %s with %s"%(ch, combining) # this causes UnicdeDecodeError!!!
        return unicodedata.normalize('NFC', unicode(ch)+combining)

    return u"".join([getaccented(ch, combining) for ch in c])


for u in unicode_accents_list:
    (mname, mcombining) = u
    _latex_specs_base['macros'].append(
        MacroTextSpec(mname, lambda x, l2tobj, c=mcombining: make_accented_char(x, c, l2tobj))
    )

# specs structure now complete

