"""
Run a normal OpenERP HTTP process.
"""

import logging
import os
import threading

import common

_logger = logging.getLogger(__name__)

def run(args):
    import openerp.cli.server
    import openerp.service.wsgi_server
    import openerp.tools.config
    config = openerp.tools.config

    os.environ["TZ"] = "UTC"
    common.set_addons(args)

    openerp.multi_process = True
    common.setproctitle('openerp-web')

    openerp.cli.server.check_root_user()
    openerp.netsvc.init_logger()
    #openerp.cli.server.report_configuration()
    openerp.cli.server.configure_babel_localedata_path()
    openerp.cli.server.setup_signal_handlers()

    target = openerp.service.wsgi_server.serve
    if not args.gevent:
        config["gevent"] = False
        # TODO openerp.multi_process with a multi-threaded process probably
        # doesn't work very well (e.g. waiting for all threads to complete
        # before killing the process is not implemented).
        arg = (args.interface, int(args.port), args.threaded)
        threading.Thread(target=target, args=arg).start()
        openerp.cli.server.quit_on_signals()
    else:
        config["gevent"] = True
        import gevent.monkey
        import gevent.wsgi
        import gevent_psycopg2
        gevent.monkey.patch_all()
        gevent_psycopg2.monkey_patch()

        app = openerp.service.wsgi_server.application
        server = gevent.wsgi.WSGIServer((args.interface, int(args.port)), app)
        server.serve_forever()
        # TODO quit_on_signals

def add_parser(subparsers):
    parser = subparsers.add_parser('web',
        description='Run a normal OpenERP HTTP process. By default a '
        'singly-threaded Werkzeug server is used.')
    common.add_addons_argument(parser)
    parser.add_argument('--interface', default='0.0.0.0',
        help='HTTP interface to listen on (default is %(default)s)')
    parser.add_argument('--port', metavar='INT', default=8069,
        help='HTTP port to listen on (default is %(default)s)')
    parser.add_argument('--threaded', action='store_true',
        help='Use a multithreaded Werkzeug server (incompatible with --gevent)')
    parser.add_argument('--gevent', action='store_true',
        help="Use gevent's WSGI server (incompatible with --threaded)")

    parser.set_defaults(run=run)
