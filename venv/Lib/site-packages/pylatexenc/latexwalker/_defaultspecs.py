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


# Internal module. May change without notice.


from ..macrospec import std_macro, std_environment, std_specials, \
    MacroSpec, EnvironmentSpec, MacroStandardArgsParser, VerbatimArgsParser

specs = [
    #
    # CATEGORY: latex-base
    #
    ('latex-base', {
        'macros': [

            std_macro('documentclass', True, 1),
            std_macro('usepackage', True, 1),
            std_macro('RequirePackage', True, 1),
            std_macro('selectlanguage', True, 1),
            std_macro('setlength', True, 2),
            std_macro('addlength', True, 2),
            std_macro('setcounter', True, 2),
            std_macro('addcounter', True, 2),
            std_macro('newcommand', "*{[[{"),
            std_macro('renewcommand', "*{[[{"),
            std_macro('providecommand', "*{[[{"),
            std_macro('newenvironment', "*{[[{{"),
            std_macro('renewenvironment', "*{[[{{"),
            std_macro('provideenvironment', "*{[[{{"),

            std_macro('DeclareMathOperator', '*{{'),

            std_macro('hspace', '*{'),
            std_macro('vspace', '*{'),

            MacroSpec('mbox',
                      args_parser=MacroStandardArgsParser('{', args_math_mode=[False])),

            # \title, \author, \date
            MacroSpec('title', '{'),
            MacroSpec('author', '{'),
            MacroSpec('date', '{'),

            # (Note: single backslash) end of line with optional no-break ('*') and
            # additional vertical spacing, e.g. \\*[2mm]
            #
            # Special for this command: don't allow an optional spacing argument
            # [2mm] to be separated by spaces from the rest of the macro.  This
            # emulates the behavior in AMS environments, and avoids some errors;
            # e.g. in "\begin{align} A=0 \\ [C,D]=0 \end{align}" the "[C,D]"
            # does not get captured as an optional macro argument.
            MacroSpec('\\',
                      args_parser=MacroStandardArgsParser('*[', optional_arg_no_space=True)),

            std_macro('item', True, 0),

            # \input{someotherfile}
            std_macro('input', False, 1),
            std_macro('include', False, 1),

            std_macro('includegraphics', True, 1),

            std_macro('chapter', '*[{'),
            std_macro('section', '*[{'),
            std_macro('subsection', '*[{'),
            std_macro('subsubsection', '*[{'),
            std_macro('pagagraph', '*[{'),
            std_macro('subparagraph', '*[{'),

            std_macro('bibliography', '{'),


            std_macro('emph', False, 1),
            MacroSpec('textrm',
                      args_parser=MacroStandardArgsParser('{', args_math_mode=[False])),
            MacroSpec('textit',
                      args_parser=MacroStandardArgsParser('{', args_math_mode=[False])),
            MacroSpec('textbf',
                      args_parser=MacroStandardArgsParser('{', args_math_mode=[False])),
            MacroSpec('textmd',
                      args_parser=MacroStandardArgsParser('{', args_math_mode=[False])),
            MacroSpec('textsc',
                      args_parser=MacroStandardArgsParser('{', args_math_mode=[False])),
            MacroSpec('textsf',
                      args_parser=MacroStandardArgsParser('{', args_math_mode=[False])),
            MacroSpec('textsl',
                      args_parser=MacroStandardArgsParser('{', args_math_mode=[False])),
            MacroSpec('texttt',
                      args_parser=MacroStandardArgsParser('{', args_math_mode=[False])),
            MacroSpec('textup',
                      args_parser=MacroStandardArgsParser('{', args_math_mode=[False])),
            MacroSpec('text',
                      args_parser=MacroStandardArgsParser('{', args_math_mode=[False])),
            std_macro('mathrm', False, 1), # only allowed in math mode anyway
            std_macro('mathbb', False, 1), # only allowed in math mode anyway
            std_macro('mathbf', False, 1),
            std_macro('mathit', False, 1),
            std_macro('mathsf', False, 1),
            std_macro('mathtt', False, 1),
            std_macro('mathcal', False, 1),
            std_macro('mathscr', False, 1),
            std_macro('mathfrak', False, 1),

            std_macro('label', False, 1),
            std_macro('ref', False, 1),
            std_macro('autoref', False, 1),
            std_macro('cref', False, 1),
            std_macro('Cref', False, 1),
            std_macro('eqref', False, 1),
            std_macro('url', False, 1),
            std_macro('hypersetup', False, 1),
            std_macro('footnote', True, 1),

            std_macro('keywords', False, 1),

            std_macro('hphantom', True, 1),
            std_macro('vphantom', True, 1),

            std_macro("'", False, 1),
            std_macro("`", False, 1),
            std_macro('"', False, 1),
            std_macro("c", False, 1),
            std_macro("^", False, 1),
            std_macro("~", False, 1),
            std_macro("H", False, 1),
            std_macro("k", False, 1),
            std_macro("=", False, 1),
            std_macro("b", False, 1),
            std_macro(".", False, 1),
            std_macro("d", False, 1),
            std_macro("r", False, 1),
            std_macro("u", False, 1),
            std_macro("v", False, 1),

            MacroSpec('ensuremath',
                      args_parser=MacroStandardArgsParser('{', args_math_mode=[True])),

            std_macro("not", False, 1),

            std_macro("vec", False, 1),
            std_macro("dot", False, 1),
            std_macro("hat", False, 1),
            std_macro("check", False, 1),
            std_macro("breve", False, 1),
            std_macro("acute", False, 1),
            std_macro("grave", False, 1),
            std_macro("tilde", False, 1),
            std_macro("bar", False, 1),
            std_macro("ddot", False, 1),

            std_macro('frac', False, 2),
            std_macro('nicefrac', False, 2),

            std_macro('sqrt', True, 1),

            MacroSpec('overline', '{'),
            MacroSpec('underline', '{'),
            MacroSpec('widehat', '{'),
            MacroSpec('widetilde', '{'),
            MacroSpec('wideparen', '{'),
            MacroSpec('overleftarrow', '{'),
            MacroSpec('overrightarrow', '{'),
            MacroSpec('overleftrightarrow', '{'),
            MacroSpec('underleftarrow', '{'),
            MacroSpec('underrightarrow', '{'),
            MacroSpec('underleftrightarrow', '{'),
            MacroSpec('overbrace', '{'),
            MacroSpec('underbrace', '{'),
            MacroSpec('overgroup', '{'),
            MacroSpec('undergroup', '{'),
            MacroSpec('overbracket', '{'),
            MacroSpec('underbracket', '{'),
            MacroSpec('overlinesegment', '{'),
            MacroSpec('underlinesegment', '{'),
            MacroSpec('overleftharpoon', '{'),
            MacroSpec('overrightharpoon', '{'),

            MacroSpec('xleftarrow', '[{'),
            MacroSpec('xrightarrow', '[{'),

            std_macro('ket', False, 1),
            std_macro('bra', False, 1),
            std_macro('braket', False, 2),
            std_macro('ketbra', False, 2),

            std_macro('texorpdfstring', False, 2),

            # xcolor commands
            MacroSpec('definecolor', '[{{{'),
            MacroSpec('providecolor', '[{{{'),
            MacroSpec('colorlet', '[{[{'),
            MacroSpec('color', '[{'),
            MacroSpec('textcolor', '[{{'),
            MacroSpec('pagecolor', '[{'),
            MacroSpec('nopagecolor', ''),
            MacroSpec('colorbox', '[{{'),
            MacroSpec('fcolorbox', '[{[{{'),
            MacroSpec('boxframe', '{{{'),
            MacroSpec('rowcolors', '*[{{{'),
        ],
        'environments': [
            # NOTE: Starred variants (as in \begin{equation*}) are not specified as
            # for macros with an argspec='*'.  Rather, we need to define a separate
            # spec for the starred variant as the star really is part of the
            # environment name.  If you specify argspec='*', the parser will try to
            # look for an expression of the form '\begin{equation}*'

            std_environment('figure', '['),
            std_environment('figure*', '['),
            std_environment('table', '['),
            std_environment('table*', '['),

            std_environment('abstract', None),
            
            std_environment('tabular', '{'),
            std_environment('tabular*', '{{'),
            std_environment('tabularx', '{[{'),

            std_environment('array', '[{'),

            std_environment('equation', None, is_math_mode=True),
            std_environment('equation*', None, is_math_mode=True),
            std_environment('eqnarray', None, is_math_mode=True),
            std_environment('eqnarray*', None, is_math_mode=True),
        
            # AMS environments
            std_environment('align', None, is_math_mode=True),
            std_environment('align*', None, is_math_mode=True),
            std_environment('gather', None, is_math_mode=True),
            std_environment('gather*', None, is_math_mode=True),
            std_environment('flalign', None, is_math_mode=True),
            std_environment('flalign*', None, is_math_mode=True),
            std_environment('multline', None, is_math_mode=True),
            std_environment('multline*', None, is_math_mode=True),
            std_environment('alignat', '{', is_math_mode=True),
            std_environment('alignat*', '{', is_math_mode=True),
            std_environment('split', None, is_math_mode=True),
        ],
        'specials': [
            std_specials('&'),

            # TODO --- for this, we need to parse their argument but don't use
            #          the standard args parser because we need to be able to
            #          accept arguments like "x_\mathrm{initial}"
            #
            #std_specials('^'),
            #std_specials('_'),
        ]}),


    #
    # CATEGORY: nonascii-specials
    #
    ('nonascii-specials', {
        'macros': [],
        'environments': [],
        'specials': [
            std_specials("~"),
            
            # cf. https://tex.stackexchange.com/a/439652/32188 "fake ligatures":
            std_specials('``'),
            std_specials("''"),
            std_specials("--"),
            std_specials("---"),
            std_specials("!`"),
            std_specials("?`"),
        ]}),


    #
    # CATEGORY: verbatim
    #
    ('verbatim', {
        'macros': [
            MacroSpec('verb',
                      args_parser=VerbatimArgsParser(verbatim_arg_type='verb-macro')),
            ],
        'environments': [
            EnvironmentSpec('verbatim',
                            args_parser=VerbatimArgsParser(verbatim_arg_type='verbatim-environment')),
        ],
        'specials': [
            # optionally users could include the specials "|" like in latex-doc
            # for verbatim |\like \this|...
        ]}),

    #
    # CATEGORY: theorems
    #
    ('theorems', {
        'macros': [],
        'environments': [
            std_environment('theorem', '['),
            std_environment('proposition', '['),
            std_environment('lemma', '['),
            std_environment('corollary', '['),
            std_environment('definition', '['),
            std_environment('conjecture', '['),
            std_environment('remark', '['),
            #
            std_environment('proof', '['),
            # short names
            std_environment('thm', '['),
            std_environment('prop', '['),
            std_environment('lem', '['),
            std_environment('cor', '['),
            std_environment('conj', '['),
            std_environment('rem', '['),
            std_environment('defn', '['),
        ],
        'specials': [
        ]}),

    #
    # CATEGORY: enumitem
    #
    ('enumitem', {
        'macros': [],
        'environments': [
            std_environment('enumerate', '['),
            std_environment('itemize', '['),
            std_environment('description', '['),
        ],
        'specials': [
        ]}),

    #
    # CATEGORY: natbib
    #
    ('natbib', {
        'macros': [
            std_macro('cite', '*[[{'),
            std_macro('citet', '*[[{'),
            std_macro('citep', '*[[{'),
            std_macro('citealt', '*[[{'),
            std_macro('citealp', '*[[{'),
            std_macro('citeauthor', '*[[{'),
            std_macro('citefullauthor', '[[{'),
            std_macro('citeyear', '[[{'),
            std_macro('citeyearpar', '[[{'),
            std_macro('Citet', '*[[{'),
            std_macro('Citep', '*[[{'),
            std_macro('Citealt', '*[[{'),
            std_macro('Citealp', '*[[{'),
            std_macro('Citeauthor', '*[[{'),

            std_macro('citetext', '{'),
            std_macro('citenum', '{'),

            std_macro('defcitealias', '{{'),
            std_macro('citetalias', '[[{'),
            std_macro('citepalias', '[[{'),
        ],
        'environments': [
        ],
        'specials': [
        ]}),


    #
    # CATEGORY: latex-ethuebung
    #
    ('latex-ethuebung', {
        'macros': [
            # ethuebung
            std_macro('UebungLoesungFont', False, 1),
            std_macro('UebungHinweisFont', False, 1),
            std_macro('UebungExTitleFont', False, 1),
            std_macro('UebungSubExTitleFont', False, 1),
            std_macro('UebungTipsFont', False, 1),
            std_macro('UebungLabel', False, 1),
            std_macro('UebungSubLabel', False, 1),
            std_macro('UebungLabelEnum', False, 1),
            std_macro('UebungLabelEnumSub', False, 1),
            std_macro('UebungSolLabel', False, 1),
            std_macro('UebungHinweisLabel', False, 1),
            std_macro('UebungHinweiseLabel', False, 1),
            std_macro('UebungSolEquationLabel', False, 1),
            std_macro('UebungTipsLabel', False, 1),
            std_macro('UebungTipsEquationLabel', False, 1),
            std_macro('UebungsblattTitleSeries', False, 1),
            std_macro('UebungsblattTitleSolutions', False, 1),
            std_macro('UebungsblattTitleTips', False, 1),
            std_macro('UebungsblattNumber', False, 1),
            std_macro('UebungsblattTitleFont', False, 1),
            std_macro('UebungTitleCenterVSpacing', False, 1),
            std_macro('UebungAttachedSolutionTitleTop', False, 1),
            std_macro('UebungAttachedSolutionTitleFont', False, 1),
            std_macro('UebungAttachedSolutionTitle', False, 1),
            std_macro('UebungTextAttachedSolution', False, 1),
            std_macro('UebungDueByLabel', False, 1),
            std_macro('UebungDueBy', False, 1),
            std_macro('UebungLecture', False, 1),
            std_macro('UebungProf', False, 1),
            std_macro('UebungLecturer', False, 1),
            std_macro('UebungSemester', False, 1),
            std_macro('UebungLogoFile', False, 1),
            std_macro('UebungLanguage', False, 1),
            std_macro('UebungStyle', False, 1),
            #
            std_macro('uebung', '{['),
            std_macro('exercise', '{['),
            std_macro('keywords', False, 1),
            std_macro('subuebung', False, 1),
            std_macro('subexercise', False, 1),
            std_macro('pdfloesung', True, 1),
            std_macro('pdfsolution', True, 1),
            std_macro('exenumfulllabel', False, 1),
            std_macro('hint', False, 1),
            std_macro('hints', False, 1),
            std_macro('hinweis', False, 1),
            std_macro('hinweise', False, 1),
        ],
        'environments': [
        ],
        'specials': [
        ]
    }),
]
