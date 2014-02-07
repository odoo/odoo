"""
Execute the unittest2 tests available in OpenERP addons.
"""

import sys
import types
import argparse

import common

def get_test_modules(module, submodule, explode):
    """
    Return a list of submodules containing tests.
    `submodule` can be:
      - None
      - the name of a submodule
      - '__fast_suite__'
      - '__sanity_checks__'
    """
    # Turn command-line module, submodule into importable names.
    if module is None:
        pass
    elif module == 'openerp':
        module = 'openerp.tests'
    else:
        module = 'openerp.addons.' + module + '.tests'

    # Try to import the module
    try:
        __import__(module)
    except Exception, e:
        if explode:
            print 'Can not `import %s`.' % module
            import logging
            logging.exception('')
            sys.exit(1)
        else:
            if str(e) == 'No module named tests':
                # It seems the module has no `tests` sub-module, no problem.
                pass
            else:
                print 'Can not `import %s`.' % module
            return []

    # Discover available test sub-modules.
    m = sys.modules[module]
    submodule_names =  sorted([x for x in dir(m) \
        if x.startswith('test_') and \
        isinstance(getattr(m, x), types.ModuleType)])
    submodules = [getattr(m, x) for x in submodule_names]

    def show_submodules_and_exit():
        if submodule_names:
            print 'Available submodules are:'
            for x in submodule_names:
                print ' ', x
        sys.exit(1)

    fast_suite = getattr(m, 'fast_suite', [])
    checks = getattr(m, 'checks', [])
    if submodule is None:
        # Use auto-discovered sub-modules.
        ms = submodules
    elif submodule == '__fast_suite__':
        # `suite` was used before the 6.1 release instead of `fast_suite`.
        ms = fast_suite if hasattr(m, 'fast_suite') else getattr(m, 'suite', None)
        if not ms:
            if explode:
                print 'The module `%s` has no defined test suite.' % (module,)
                show_submodules_and_exit()
            else:
                ms = []
    elif submodule == '__sanity_checks__':
        ms = checks
        if not ms:
            if explode:
                print 'The module `%s` has no defined sanity checks.' % (module,)
                show_submodules_and_exit()
            else:
                ms = []
    elif submodule == '__slow_suite__':
        ms = list(set(submodules).difference(fast_suite, checks))
    else:
        # Pick the command-line-specified test sub-module.
        m = getattr(m, submodule, None)
        ms = [m]

        if m is None:
            if explode:
                print 'The module `%s` has no submodule named `%s`.' % \
                    (module, submodule)
                show_submodules_and_exit()
            else:
                ms = []

    return ms

def run(args):
    import unittest2

    import openerp

    config = openerp.tools.config
    config.load()

    config['db_name'] = args.database
    if args.port:
        config['xmlrpc_port'] = int(args.port)

    if args.addons:
        args.addons = args.addons.replace(':',',').split(',')
    else:
        args.addons = []

    # ensure no duplication in addons paths
    args.addons = list(set(args.addons))
    config['addons_path'] = ','.join(args.addons)

    import logging
    openerp.netsvc.init_alternative_logger()
    logging.getLogger('openerp').setLevel(logging.CRITICAL)

    # Install the import hook, to import openerp.addons.<module>.
    openerp.modules.module.initialize_sys_path()

    module = args.module
    submodule = args.submodule

    # Import the necessary modules and get the corresponding suite.
    if module is None:
        # TODO
        modules = common.get_addons_from_paths(args.addons, []) # TODO openerp.addons.base is not included ?
        test_modules = []
        for module in ['openerp'] + modules:
            test_modules.extend(
                get_test_modules(module, submodule, explode=False))
    else:
        test_modules = get_test_modules(module, submodule, explode=True)

    print 'Test modules:'
    for test_module in test_modules:
        print '    ', test_module.__name__
    print
    sys.stdout.flush()

    if not args.dry_run:
        suite = unittest2.TestSuite()
        for test_module in test_modules:
            suite.addTests(unittest2.TestLoader().loadTestsFromModule(test_module))
        r = unittest2.TextTestRunner(verbosity=2).run(suite)
        if r.errors or r.failures:
            sys.exit(1)

def add_parser(subparsers):
    parser = subparsers.add_parser('run-tests',
        description='Run the OpenERP server and/or addons tests.')
    parser.add_argument('-d', '--database', metavar='DATABASE', required=True,
        help='the database to test. Depending on the test suites, the '
        'database must already exist or not.')
    parser.add_argument('-p', '--port', metavar='PORT',
        help='the port used for WML-RPC tests')
    common.add_addons_argument(parser)

    parser.add_argument(
        '-m', '--module', metavar='MODULE', action=ModuleAction, default=None,
        help="the module to test in `module[.submodule]` notation. "
             "Use `openerp` for the core OpenERP tests. "
             "Leave empty to run every declared tests. "
             "Give a module but no submodule to run all the module's declared "
             "tests. If both the module and the submodule are given, "
             "the sub-module can be run even if it is not declared in the module.")
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        '--fast-suite',
        dest='submodule', action=GuardAction, nargs=0, const='__fast_suite__',
        help='run only the tests explicitly declared in the fast suite (this '
        'makes sense only with the bare `module` notation or no module at '
        'all).')
    group.add_argument(
        '--sanity-checks',
        dest='submodule', action=GuardAction, nargs=0, const='__sanity_checks__',
        help='run only the sanity check tests')
    group.add_argument(
        '--slow-suite',
        dest='submodule', action=GuardAction, nargs=0, const='__slow_suite__',
        help="Only run slow tests (tests which are neither in the fast nor in"
             " the sanity suite)")
    parser.add_argument('--dry-run', action='store_true',
        help='do not run the tests')

    parser.set_defaults(run=run, submodule=None)

class ModuleAction(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        split = values.split('.')
        if len(split) == 1:
            module, submodule = values, None
        elif len(split) == 2:
            module, submodule = split
        else:
            raise argparse.ArgumentError(
                option_string,
                "must have the form 'module[.submodule]', got '%s'" % values)

        setattr(namespace, self.dest, module)
        if submodule is not None:
            setattr(namespace, 'submodule', submodule)

class GuardAction(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        if getattr(namespace, self.dest, None):
            print "%s value provided, ignoring '%s'" % (self.dest, option_string)
            return
        setattr(namespace, self.dest, self.const)
