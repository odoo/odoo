"""
Run an OpenERP cron process.
"""

import os

import common

def set_addons(args):
    import openerp.tools.config
    config = openerp.tools.config

    assert hasattr(args, 'addons')
    if args.addons:
        args.addons = args.addons.split(':')
    else:
        args.addons = []

    config['addons_path'] = ','.join(args.addons)

def run(args):
    import openerp
    import openerp.cli.server
    import openerp.tools.config
    import openerp.service.cron
    config = openerp.tools.config

    os.environ["TZ"] = "UTC"
    set_addons(args)
    args.database = args.database or []

    config['log_handler'] = [':WARNING', 'openerp.addons.base.ir.ir_cron:DEBUG']

    openerp.multi_process = True
    common.setproctitle('openerp-cron [%s]' % ', '.join(args.database))

    openerp.cli.server.check_root_user()
    openerp.netsvc.init_logger()
    #openerp.cli.server.report_configuration()
    openerp.cli.server.configure_babel_localedata_path()
    openerp.cli.server.setup_signal_handlers()
    import openerp.addons.base
    if args.database:
        for db in args.database:
            openerp.cli.server.preload_registry(db)
        openerp.service.cron.start_service()
        openerp.cli.server.quit_on_signals()
    else:
        print "No database given."


def add_parser(subparsers):
    parser = subparsers.add_parser('cron',
        description='Run an OpenERP cron process.')
    common.add_addons_argument(parser)
    parser.add_argument('--database', action='append',
        help='Database for which cron jobs are processed (can be given repeated)')

    parser.set_defaults(run=run)
