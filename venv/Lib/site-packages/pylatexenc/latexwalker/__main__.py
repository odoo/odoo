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
import json
import logging


from ..latexwalker import LatexWalker, disp_node, make_json_encoder
from ..version import version_str



def main(argv=None):

    if argv is None:
        argv = sys.argv[1:]

    parser = argparse.ArgumentParser(prog='latexwalker', add_help=False)

    parser.add_argument('--output-format', metavar="FORMAT", dest="output_format",
                        choices=["human", "json"], default='human',
                        help='Requested output format for the node tree ("human" or "json")')
    parser.add_argument('--json-indent', metavar="NUMSPACES", dest="json_indent",
                        type=int, default=2,
                        help='Indentation in JSON output (specify number of spaces '
                        'per indentation level)')
    parser.add_argument('--json-compact', dest="json_indent", action='store_const', const=None,
                        help='Output compact JSON')

    parser.add_argument('--keep-inline-math', action='store_const', const=True,
                        dest='keep_inline_math', default=True,
                        help=argparse.SUPPRESS)
    parser.add_argument('--no-keep-inline-math', action='store_const', const=False,
                        dest='keep_inline_math',
                        help=argparse.SUPPRESS)

    parser.add_argument('--tolerant-parsing', action='store_const', const=True,
                        dest='tolerant_parsing', default=True)
    parser.add_argument('--no-tolerant-parsing', action='store_const', const=False,
                        dest='tolerant_parsing',
                        help="Tolerate syntax errors when parsing, and attempt "
                        "to continue (default yes)")

    # I'm not sure this flag is useful and if it should be exposed at all.
    # Accept it, but make it hidden.
    parser.add_argument('--strict-braces', action='store_const', const=True,
                        dest='strict_braces', default=False,
                        help=argparse.SUPPRESS)
    parser.add_argument('--no-strict-braces', action='store_const', const=False,
                        dest='strict_braces',
                        #help="Report errors for mismatching LaTeX braces (default no)"
                        help=argparse.SUPPRESS)

    parser.add_argument('-q', '--quiet', dest='logging_level', action='store_const',
                        const=logging.ERROR, default=logging.INFO,
                        help="Suppress warning messages")
    parser.add_argument('-v', '--verbose', dest='logging_level', action='store_const',
                        const=logging.DEBUG,
                        help="Verbose output")
    parser.add_argument('--version', action='version',
                        version='pylatexenc {}'.format(version_str),
                        help="Show version information and exit")
    parser.add_argument('--help', action='help',
                        help="Show this help information and exit")


    parser.add_argument('--code', '-c', action='store', default=None, metavar="LATEX_CODE",
                        help="Convert the given LATEX_CODE to unicode text instead of reading "
                        "from FILE or standard input.  You cannot specify FILEs if you use this "
                        "option, and any standard input is ignored.")

    parser.add_argument('files', metavar="FILE", nargs='*',
                        help='Input files (if none specified, read from stdandard input)')

    args = parser.parse_args(argv)

    logging.basicConfig()
    logging.getLogger().setLevel(args.logging_level)
    logger = logging.getLogger(__name__)

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
    
    latexwalker = LatexWalker(latex,
                              tolerant_parsing=args.tolerant_parsing,
                              strict_braces=args.strict_braces)

    (nodelist, pos, len_) = latexwalker.get_latex_nodes()

    if args.output_format == 'human':
        print('\n--- NODES ---\n')
        for n in nodelist:
            disp_node(n)
        print('\n-------------\n')
        return

    if args.output_format == 'json':
        json.dump({ 'nodelist': nodelist, },
                  sys.stdout,
                  cls=make_json_encoder(latexwalker),
                  indent=args.json_indent)
        sys.stdout.write("\n")
        return
    
    raise ValueError("Invalid output format: "+args.output_format)



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

    #run_main() # debug
    main()
