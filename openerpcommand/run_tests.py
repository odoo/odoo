"""
Execute the unittest2 tests available in OpenERP addons.
"""

import os
import sys
import types

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

    if submodule is None:
        # Use auto-discovered sub-modules.
        ms = submodules
    elif submodule == '__fast_suite__':
        # Obtain the explicit test sub-modules list.
        ms = getattr(sys.modules[module], 'fast_suite', None)
        # `suite` was used before the 6.1 release instead of `fast_suite`.
        ms = ms if ms else getattr(sys.modules[module], 'suite', None)
        if ms is None:
            if explode:
                print 'The module `%s` has no defined test suite.' % (module,)
                show_submodules_and_exit()
            else:
                ms = []
    elif submodule == '__sanity_checks__':
        ms = getattr(sys.modules[module], 'checks', None)
        if ms is None:
            if explode:
                print 'The module `%s` has no defined sanity checks.' % (module,)
                show_submodules_and_exit()
            else:
                ms = []
    else:
        # Pick the command-line-specified test sub-module.
        m = getattr(sys.modules[module], submodule, None)
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
    config['db_name'] = args.database
    if args.port:
        config['xmlrpc_port'] = int(args.port)
    config['admin_passwd'] = 'admin'
    config['db_password'] = 'a2aevl8w' # TODO from .openerpserverrc
    config['addons_path'] = args.addons.replace(':',',')
    if args.addons:
        args.addons = args.addons.split(':')
    else:
        args.addons = []
    if args.sanity_checks and args.fast_suite:
        print 'Only at most one of `--sanity-checks` and `--fast-suite` ' \
            'can be specified.'
        sys.exit(1)

    import logging
    openerp.netsvc.init_alternative_logger()
    logging.getLogger('openerp').setLevel(logging.CRITICAL)

    # Install the import hook, to import openerp.addons.<module>.
    openerp.modules.module.initialize_sys_path()
    openerp.modules.loading.open_openerp_namespace()

    # Extract module, submodule from the command-line args.
    if args.module is None:
        module, submodule = None, None
    else:
        splitted = args.module.split('.')
        if len(splitted) == 1:
            module, submodule = splitted[0], None
        elif len(splitted) == 2:
            module, submodule = splitted
        else:
            print 'The `module` argument must have the form ' \
                '`module[.submodule]`.'
            sys.exit(1)

    # Import the necessary modules and get the corresponding suite.
    if module is None:
        # TODO
        modules = common.get_addons_from_paths(args.addons, []) # TODO openerp.addons.base is not included ?
	test_modules = []
        for module in ['openerp'] + modules:
            if args.fast_suite:
                submodule = '__fast_suite__'
            if args.sanity_checks:
                submodule = '__sanity_checks__'
            test_modules.extend(get_test_modules(module,
                submodule, explode=False))
    else:
        if submodule and args.fast_suite:
            print "Submodule name `%s` given, ignoring `--fast-suite`." % (submodule,)
        if submodule and args.sanity_checks:
            print "Submodule name `%s` given, ignoring `--sanity-checks`." % (submodule,)
        if not submodule and args.fast_suite:
            submodule = '__fast_suite__'
        if not submodule and args.sanity_checks:
            submodule = '__sanity_checks__'
        test_modules = get_test_modules(module,
            submodule, explode=True)

    # Run the test suite.
    if not args.dry_run:
        suite = unittest2.TestSuite()
        for test_module in test_modules:
            suite.addTests(unittest2.TestLoader().loadTestsFromModule(test_module))
        r = unittest2.TextTestRunner(verbosity=2).run(suite)
        if r.errors or r.failures:
            sys.exit(1)
    else:
        print 'Test modules:'
        for test_module in test_modules:
            print ' ', test_module.__name__

def add_parser(subparsers):
    parser = subparsers.add_parser('run-tests',
        description='Run the OpenERP server and/or addons tests.')
    parser.add_argument('-d', '--database', metavar='DATABASE', required=True,
        help='the database to test. Depending on the test suites, the '
        'database must already exist or not.')
    parser.add_argument('-p', '--port', metavar='PORT',
        help='the port used for WML-RPC tests')
    common.add_addons_argument(parser)
    parser.add_argument('-m', '--module', metavar='MODULE',
        default=None,
        help='the module to test in `module[.submodule]` notation. '
        'Use `openerp` for the core OpenERP tests. '
        'Leave empty to run every declared tests. '
        'Give a module but no submodule to run all the module\'s declared '
        'tests. If both the module and the submodule are given, '
        'the sub-module can be run even if it is not declared in the module.')
    parser.add_argument('--fast-suite', action='store_true',
        help='run only the tests explicitely declared in the fast suite (this '
        'makes sense only with the bare `module` notation or no module at '
        'all).')
    parser.add_argument('--sanity-checks', action='store_true',
        help='run only the sanity check tests')
    parser.add_argument('--dry-run', action='store_true',
        help='do not run the tests')

    parser.set_defaults(run=run)
