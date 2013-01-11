"""
Define a few common arguments for server-side command-line tools.
"""
import argparse
import os
import sys

def add_addons_argument(parser):
    """
    Add a common --addons argument to a parser.
    """
    parser.add_argument('--addons', metavar='ADDONS',
        **required_or_default('ADDONS',
                              'colon-separated list of paths to addons'))

def get_addons_from_paths(paths, exclude):
    """
    Build a list of available modules from a list of addons paths.
    """
    exclude = exclude or []
    module_names = []
    for p in paths:
        if os.path.exists(p):
            names = list(set(os.listdir(p)))
            names = filter(lambda a: not (a.startswith('.') or a in exclude), names)
            module_names.extend(names)
        else:
            print "The addons path `%s` doesn't exist." % p
            sys.exit(1)
    return module_names

def required_or_default(name, h):
    """
    Helper to define `argparse` arguments. If the name is the environment,
    the argument is optional and draw its value from the environment if not
    supplied on the command-line. If it is not in the environment, make it
    a mandatory argument.
    """
    if os.environ.get('OPENERP_' + name.upper()):
	d = {'default': os.environ['OPENERP_' + name.upper()]}
    else:
	d = {'required': True}
    d['help'] = h + '. The environment variable OPENERP_' + \
	name.upper() + ' can be used instead.'
    return d

class Command(object):
    """
    Base class to create command-line tools. It must be inherited and the
    run() method overriden.
    """

    command_name = 'stand-alone'

    def __init__(self, subparsers=None):
        if subparsers:
            self.parser = parser = subparsers.add_parser(self.command_name,
	        description=self.__class__.__doc__)
        else:
	    self.parser = parser = argparse.ArgumentParser(
                description=self.__class__.__doc__)

        parser.add_argument('-d', '--database', metavar='DATABASE',
            **required_or_default('DATABASE', 'the database to connect to'))
        parser.add_argument('-u', '--user', metavar='USER',
            **required_or_default('USER', 'the user login or ID. When using '
            'RPC, providing an ID avoid the login() step'))
        parser.add_argument('-p', '--password', metavar='PASSWORD',
            **required_or_default('PASSWORD', 'the user password')) # TODO read it from the command line or from file.

        parser.set_defaults(run=self.run_with_args)

    def run_with_args(self, args):
        self.args = args
        self.run()

    def run(self):
        print 'Stub Command.run().'

    @classmethod
    def stand_alone(cls):
        """
        A single Command object is a complete command-line program. See
        `openerp-command/stand-alone` for an example.
        """
        command = cls()
        args = command.parser.parse_args()
        args.run(args)
