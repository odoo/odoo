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

import sys
import fileinput
import argparse
import logging


from .. import latexwalker
from ..latex2text import LatexNodes2Text, _strict_latex_spaces_predef
from ..version import version_str


def main(argv=None):

    if argv is None:
        argv = sys.argv[1:]

    parser = argparse.ArgumentParser(prog='latex2text', add_help=False)

    codegroup = parser.add_argument_group("Input options")

    codegroup.add_argument('--code', '-c', action='store', default=None, metavar="LATEX_CODE",
                           help="Convert the given LATEX_CODE to unicode text instead of reading "
                           "from FILE or standard input.  You cannot specify FILEs if you use this "
                           "option, and any standard input is ignored.")


    codegroup.add_argument('files', metavar="FILE", nargs='*',
                           help="Input files to read LaTeX code from. If no FILE(s) is/are specified, "
                           "LaTeX code is read from standard input unless --code is specified")



    group = parser.add_argument_group("LatexWalker options")

    group.add_argument('--parser-keep-inline-math', action='store_const', const=True,
                       dest='parser_keep_inline_math', default=None,
                       help=argparse.SUPPRESS)
    group.add_argument('--no-parser-keep-inline-math', action='store_const', const=False,
                       dest='parser_keep_inline_math',
                       help=argparse.SUPPRESS)

    group.add_argument('--tolerant-parsing', action='store_const', const=True,
                       dest='tolerant_parsing', default=True)
    group.add_argument('--no-tolerant-parsing', action='store_const', const=False,
                       dest='tolerant_parsing',
                       help="Tolerate syntax errors when parsing, and attempt to continue (default yes)")

    # I'm not sure this flag is useful and if it should be exposed at all.
    # Accept it, but make it hidden.
    parser.add_argument('--strict-braces', action='store_const', const=True,
                        dest='strict_braces', default=False,
                        help=argparse.SUPPRESS)
    parser.add_argument('--no-strict-braces', action='store_const', const=False,
                        dest='strict_braces',
                        #help="Report errors for mismatching LaTeX braces (default no)"
                        help=argparse.SUPPRESS)

    group = parser.add_argument_group("LatexNodes2Text options")

    group.add_argument('--text-keep-inline-math', action='store_const', const=True,
                       dest='text_keep_inline_math', default=None,
                       help=argparse.SUPPRESS)
    group.add_argument('--no-text-keep-inline-math', action='store_const', const=False,
                       dest='text_keep_inline_math',
                       help=argparse.SUPPRESS)

    group.add_argument('--math-mode', action='store', dest='math_mode',
                       choices=['text', 'with-delimiters', 'verbatim', 'remove'],
                       default='text',
                       help="How to handle chunks of math mode LaTeX code. 'text' = convert "
                       "to text like the rest; 'with-delimiters' = same as 'text' but retain "
                       "the original math mode delimiters; 'verbatim' = keep verbatim LaTeX code; "
                       "'remove' = remove from input entirely")

    group.add_argument('--fill-text', dest='fill_text', action='store', nargs='?',
                       default=-1,
                       help="Attempt to wrap text to the given width, or 80 columns if option is "
                       "specified with no argument")

    group.add_argument('--keep-comments', action='store_const', const=True,
                       dest='keep_comments', default=False)
    group.add_argument('--no-keep-comments', action='store_const', const=False,
                       dest='keep_comments',
                       help="Keep LaTeX comments in text output (default no)")

    class ListWithHiddenItems(list):
        def __init__(self, thelist, hiddenitems):
            super(ListWithHiddenItems, self).__init__(thelist)
            self.hiddenitems = hiddenitems
        def __contains__(self, value):
            return super(ListWithHiddenItems, self).__contains__(value) \
                or value in self.hiddenitems

    strict_latex_spaces_choices = ListWithHiddenItems(
        # the list
        ['off', 'on']+list(k for k in _strict_latex_spaces_predef.keys() if k != 'default'),
        # hidden items: Value is accepted, but not shown in list of choices
        ['default']
    )
    group.add_argument('--strict-latex-spaces', choices=strict_latex_spaces_choices,
                       dest='strict_latex_spaces', default='macros',
                       help="How to handle whitespace. See documentation for the class "
                       "LatexNodes2Text().")

    group.add_argument('--keep-braced-groups', action='store_const', const=True,
                       dest='keep_braced_groups', default=False)
    group.add_argument('--no-keep-braced-groups', action='store_const', const=False,
                       dest='keep_braced_groups',
                       help="Keep LaTeX {braced groups} in text output (default no)")

    group.add_argument('--keep-braced-groups-minlen', type=int, default=2,
                       dest='keep_braced_groups_minlen',
                       help="Only apply --keep-braced-groups to groups that contain at least "
                       "this many characters")

    group = parser.add_argument_group("General options")

    group.add_argument('-q', '--quiet', dest='logging_level', action='store_const',
                       const=logging.ERROR, default=logging.INFO,
                       help="Suppress warning messages")
    group.add_argument('-v', '--verbose', dest='logging_level', action='store_const',
                       const=logging.DEBUG,
                       help="Verbose output")
    group.add_argument('--version', action='version',
                       version='pylatexenc {}'.format(version_str),
                       help="Show version information and exit")
    group.add_argument('--help', action='help',
                       help="Show this help information and exit")

    args = parser.parse_args(argv)

    logging.basicConfig()
    logging.getLogger().setLevel(args.logging_level)
    logger = logging.getLogger(__name__)


    if args.parser_keep_inline_math is not None or args.text_keep_inline_math is not None:
        logger.warning("Options --parser-keep-inline-math and --text-keep-inline-math are "
                       "deprecated and no longer have any effect.  Please use "
                       "--math-mode=... instead.")

    latex = ''
    if args.code:
        if args.files:
            logger.error("Cannot specify both FILEs and --code option. "
                         "Use --help option for more information.")
            sys.exit(1)
        latex = args.code
    else:
        for line in fileinput.input(files=args.files):
            latex += line

    if args.fill_text != -1:
        if args.fill_text is not None and len(args.fill_text):
            fill_text = int(args.fill_text)
        else:
            fill_text = True
    else:
        fill_text = None

    lw = latexwalker.LatexWalker(latex,
                                 tolerant_parsing=args.tolerant_parsing,
                                 strict_braces=args.strict_braces)

    (nodelist, pos, len_) = lw.get_latex_nodes()

    ln2t = LatexNodes2Text(math_mode=args.math_mode,
                           keep_comments=args.keep_comments,
                           strict_latex_spaces=args.strict_latex_spaces,
                           keep_braced_groups=args.keep_braced_groups,
                           keep_braced_groups_minlen=args.keep_braced_groups_minlen,
                           fill_text=fill_text)

    print(ln2t.nodelist_to_text(nodelist))



def run_main():

    try:

        main()

    except SystemExit:
        raise
    except: # lgtm [py/catch-base-exception]
        import pdb
        import traceback
        traceback.print_exc()
        pdb.post_mortem()


if __name__ == '__main__':

    main()
    #run_main() # debug
