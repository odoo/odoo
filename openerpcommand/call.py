"""
Call an arbitrary model's method.
"""
import ast
import os
import pprint
import sys
import time
import xmlrpclib

import client

class Call(client.Client):
    """\
    Call an arbitrary model's method.

    Example:
      > oe call res.users.read '[1, 3]' '[]' -u 1 -p admin
    """
    # TODO The above docstring is completely borked in the
    # --help message.

    command_name = 'call'

    def __init__(self, subparsers=None):
        super(Call, self).__init__(subparsers)
        self.parser.add_argument('call', metavar='MODEL.METHOD',
            help='the model and the method to call, using the '
            '<model>.<method> format.')
        self.parser.add_argument('args', metavar='ARGUMENT',
            nargs='+',
            help='the argument for the method call, must be '
            '`ast.literal_eval` compatible. Can be repeated.')

    def work(self):
        try:
            model, method = self.args.call.rsplit('.', 1)
        except:
            print "Invalid syntax `%s` must have the form <model>.<method>."
            sys.exit(1)
        args = tuple(map(ast.literal_eval, self.args.args)) if self.args.args else ()
        x = self.execute(model, method, *args)
        pprint.pprint(x, indent=4)

