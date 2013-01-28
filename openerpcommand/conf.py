"""
Display the currently used configuration. The configuration for any
sub-command is normally given by options. But some options can be specified
using environment variables. This sub-command shows those variables.
A `set` sub-command should be provided when the configuration is in a real
configuration file instead of environment variables.
"""
import os
import sys
import textwrap

def run(args):
    for x in ('database', 'addons', 'host', 'port'):
        x_ = ('openerp_' + x).upper()
        if x_ in os.environ:
            print '%s: %s' % (x, os.environ[x_])
        else:
            print '%s: <not set>' % (x, )
    os.environ['OPENERP_DATABASE'] = 'yeah'

def add_parser(subparsers):
    parser = subparsers.add_parser('conf',
        description='Display the currently used configuration.')

    parser.set_defaults(run=run)
