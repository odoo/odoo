"""
Install OpenERP on a new (by default) database.
"""
import contextlib
import errno
import os
import sys
import time

import common

# From http://code.activestate.com/recipes/576572/
@contextlib.contextmanager
def lock_file(path, wait_delay=.1, max_try=600):
    attempt = 0
    while True:
        attempt += 1
        if attempt > max_try:
            raise IOError("Could not lock file %s." % path)
        try:
            fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_RDWR)
        except OSError, e:
            if e.errno != errno.EEXIST:
                raise
            time.sleep(wait_delay)
            continue
        else:
            break
    try:
        yield fd
    finally:
        os.close(fd)
        os.unlink(path)

def run(args):
    assert args.database
    assert not (args.module and args.all_modules)

    import openerp

    config = openerp.tools.config
    config['db_name'] = args.database

    if args.tests:
        config['log_handler'] = [':INFO']
        config['test_enable'] = True
        config['without_demo'] = False
        if args.port:
            config['xmlrpc_port'] = int(args.port)
    else:
        config['log_handler'] = [':CRITICAL']
        config['test_enable'] = False
        config['without_demo'] = True

    if args.addons:
        args.addons = args.addons.split(':')
    else:
        args.addons = []
    config['addons_path'] = ','.join(args.addons)

    if args.all_modules:
        module_names = common.get_addons_from_paths(args.addons, args.exclude)
    elif args.module:
        module_names = args.module
    else:
        module_names = ['base']
    config['init'] = dict.fromkeys(module_names, 1)

    if args.coverage:
        import coverage
        # Without the `include` kwarg, coverage generates 'memory:0xXXXXX'
        # filenames (which do not exist) and cause it to crash. No idea why.
        cov = coverage.coverage(branch=True, include='*.py')
        cov.start()
    openerp.netsvc.init_logger()

    if not args.no_create:
        with lock_file('/tmp/global_openerp_create_database.lock'):
            openerp.service.db._create_empty_database(args.database)

    config['workers'] = False

    rc = openerp.service.server.start(preload=[args.database], stop=True)

    if args.coverage:
        cov.stop()
        cov.html_report(directory='coverage')
        # If we wanted the report on stdout:
        # cov.report()

    sys.exit(rc)

def add_parser(subparsers):
    parser = subparsers.add_parser('initialize',
        description='Create and initialize a new OpenERP database.')
    parser.add_argument('-d', '--database', metavar='DATABASE',
        **common.required_or_default('DATABASE', 'the database to create'))
    common.add_addons_argument(parser)
    parser.add_argument('-P', '--port', metavar='PORT',
        **common.required_or_default('PORT', 'the server port'))
    parser.add_argument('--module', metavar='MODULE', action='append',
        help='specify a module to install'
        ' (this option can be repeated)')
    parser.add_argument('--all-modules', action='store_true',
        help='install all visible modules (not compatible with --module)')
    parser.add_argument('--no-create', action='store_true',
        help='do not create the database, only initialize it')
    parser.add_argument('--exclude', metavar='MODULE', action='append',
        help='exclude a module from installation'
        ' (this option can be repeated)')
    parser.add_argument('--tests', action='store_true',
        help='run the tests as modules are installed'
        ' (use the `run-tests` command to choose specific'
        ' tests to run against an existing database).'
        ' Demo data are installed.')
    parser.add_argument('--coverage', action='store_true',
        help='report code coverage (particularly useful with --tests).'
        ' The report is generated in a coverage directory and you can'
        ' then point your browser to coverage/index.html.')

    parser.set_defaults(run=run)
