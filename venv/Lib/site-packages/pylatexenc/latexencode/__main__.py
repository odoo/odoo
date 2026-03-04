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


import sys
import fileinput
import argparse
import logging


from ..latexencode import unicode_to_latex
from ..version import version_str



def main(argv=None):

    if argv is None:
        argv = sys.argv[1:]

    parser = argparse.ArgumentParser(prog='latexencode', add_help=False)
    parser.add_argument('files', metavar="FILE", nargs='*',
                        help='Input files (if none specified, read from stdandard input)')

    parser.add_argument('--non-ascii-only', action='store_const', const=True,
                        dest='non_ascii_only', default=False)
    parser.add_argument('--no-non-ascii-only', action='store_const', const=False,
                        dest='non_ascii_only',
                        help="The option --non-ascii-only specifies that only non-ascii characters "
                        "are to be encoded into LaTeX sequences, and not characters like '$' "
                        "even though they might have a special LaTeX meaning.")

    parser.add_argument('--replacement-latex-protection',
                        choices=('braces', 'braces-all', 'braces-almost-all', 'braces-after-macro',
                                 'none'),
                        dest='replacement_latex_protection', default='braces',
                        help=r"How to protect replacement latex code from producing invalid latex code "
                        r"when concatenated in a longer string.  One of 'braces', 'braces-all', "
                        r"'braces-almost-all', 'braces-after-macro', 'none'.  Example: using "
                        r"choice 'braces' we avoid the invalid replacement 'a→b' -> 'a\tob' "
                        r"with instead 'a{\to}b'.")

    parser.add_argument('--unknown-char-policy',
                        choices=('keep', 'replace', 'ignore', 'fail'),
                        dest='unknown_char_policy', default='keep',
                        help="How to deal with nonascii characters with no known latex code equivalent.")

    parser.add_argument('-q', '--quiet', dest='logging_level', action='store_const',
                        const=logging.ERROR, default=logging.INFO,
                        help="Suppress warning messages")
    parser.add_argument('--version', action='version',
                        version='pylatexenc {}'.format(version_str),
                        help="Show version information and exit")
    parser.add_argument('--help', action='help',
                        help="Show this help information and exit")

    args = parser.parse_args(argv)

    logging.basicConfig()
    logging.getLogger().setLevel(args.logging_level)

    latex = ''
    for line in fileinput.input(files=args.files):
        latex += line

    result = unicode_to_latex(
        latex,
        non_ascii_only=args.non_ascii_only,
        replacement_latex_protection=args.replacement_latex_protection,
        unknown_char_policy=args.unknown_char_policy
    )

    sys.stdout.write(result)


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

    # run_main()  ## DEBUG
    main()
