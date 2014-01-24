"""
Run a normal OpenERP HTTP process.
"""

import logging
import os
import signal

import common

_logger = logging.getLogger(__name__)

def mk_signal_handler(server):
    def signal_handler(sig, frame):
        """
        Specialized signal handler for the evented process.
        """
        print "\n\n\nStopping gevent HTTP server...\n\n\n"
        server.stop()
    return signal_handler

def setup_signal_handlers(signal_handler):
    SIGNALS = (signal.SIGINT, signal.SIGTERM)
    map(lambda sig: signal.signal(sig, signal_handler), SIGNALS)

def run(args):
    # Note that gevent monkey patching must be done before importing the
    # `threading` module, see http://stackoverflow.com/questions/8774958/.
    if args.gevent:
        import gevent
        import gevent.monkey
        import gevent.wsgi
        import psycogreen.gevent
        gevent.monkey.patch_all()
        psycogreen.gevent.patch_psycopg()
    import threading
    import openerp
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

    target = openerp.service.wsgi_server.serve
    if not args.gevent:
        openerp.evented = False
        openerp.cli.server.setup_signal_handlers(openerp.cli.server.signal_handler)
        # TODO openerp.multi_process with a multi-threaded process probably
        # doesn't work very well (e.g. waiting for all threads to complete
        # before killing the process is not implemented).
        arg = (args.interface, int(args.port), args.threaded)
        threading.Thread(target=target, args=arg).start()
        openerp.cli.server.quit_on_signals()
    else:
        openerp.evented = True

        app = openerp.service.wsgi_server.application
        server = gevent.wsgi.WSGIServer((args.interface, int(args.port)), app)
        setup_signal_handlers(mk_signal_handler(server))
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            try:
                server.stop()
                gevent.shutdown()
            except KeyboardInterrupt:
                sys.stderr.write("Forced shutdown.\n")
                gevent.shutdown()

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
