#!/usr/bin/env python
# -*- coding: utf-8 -*-

import tokenize

from pylint import checkers, interfaces

class PEP3110TokenChecker(checkers.BaseTokenChecker):
    __implements__ = interfaces.ITokenChecker
    name = 'python3'
    enabled = False

    msgs = {
        'E3110': ('Python 3 uses `as` instead of comma token to catch exceptions',
                  'no-comma-exception',
                  'See http://www.python.org/dev/peps/pep-3110/',
                  {'maxversion': (3, 0)}),
    }

    def process_tokens(self, tokens):
        comma_found = in_except = False
        pcount = 0
        for tok_type, token, start, _, _ in tokens:
            if tok_type == tokenize.NAME and token == 'except':
                in_except = True
                comma_found = False
                pcount = 0

            elif tok_type == tokenize.OP and in_except:
                if token == '(':
                    pcount += 1
                elif token == ')':
                    pcount -= 1
                elif token == ',' and pcount == 0:
                    comma_found = True
                if token == ':':
                    if in_except and comma_found:
                        self.add_message('no-comma-exception', line=start[0])
                    comma_found = in_except = False
                    pcount = 0


def register(linter):
    linter.register_checker(PEP3110TokenChecker(linter))
