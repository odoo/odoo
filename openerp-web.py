#!/usr/bin/env python
import optparse
import os
import sys
import tempfile
import logging
import logging.config

import werkzeug.serving
import werkzeug.contrib.fixers

path_root = os.path.dirname(os.path.abspath(__file__))
path_addons = os.path.join(path_root, 'addons')
if path_addons not in sys.path:
    sys.path.insert(0, path_addons)

optparser = optparse.OptionParser()
optparser.add_option("-s", "--session-path", dest="session_storage",
                     default=os.path.join(tempfile.gettempdir(), "oe-sessions"),
                     help="directory used for session storage", metavar="DIR")
optparser.add_option("--server-host", dest="server_host",
                     default='127.0.0.1', help="OpenERP server hostname", metavar="HOST")
optparser.add_option("--server-port", dest="server_port", default=8069,
                     help="OpenERP server port", type="int", metavar="NUMBER")
optparser.add_option("--db-filter", dest="dbfilter", default='.*',
                     help="Filter listed database", metavar="REGEXP")
optparser.add_option('--addons-path', dest='addons_path', default=[path_addons], action='append',
                    help="Path do addons directory", metavar="PATH")

server_options = optparse.OptionGroup(optparser, "Server configuration")
server_options.add_option("-p", "--port", dest="socket_port", default=8002,
                          help="listening port", type="int", metavar="NUMBER")
server_options.add_option('--reloader', dest='reloader',
                          default=False, action='store_true',
                          help="Reload application when python files change")
server_options.add_option('--no-serve-static', dest='serve_static',
                          default=True, action='store_false',
                          help="Do not serve static files via this server")
server_options.add_option('--multi-threaded', dest='threaded',
                          default=False, action='store_true',
                          help="Spawn one thread per HTTP request")
server_options.add_option('--proxy-mode', dest='proxy_mode',
                          default=False, action='store_true',
                          help="Enable correct behavior when behind a reverse proxy")
optparser.add_option_group(server_options)

logging_opts = optparse.OptionGroup(optparser, "Logging")
logging_opts.add_option("--log-level", dest="log_level", type="choice",
                        default='debug', help="Global logging level", metavar="LOG_LEVEL",
                        choices=['debug', 'info', 'warning', 'error', 'critical'])
logging_opts.add_option("--log-config", dest="log_config",
                        help="Logging configuration file", metavar="FILE")
optparser.add_option_group(logging_opts)

import web.common.dispatch

if __name__ == "__main__":
    (options, args) = optparser.parse_args(sys.argv[1:])
    options.backend =  'xmlrpc'

    os.environ["TZ"] = "UTC"

    if not options.log_config:
        logging.basicConfig(level=getattr(logging, options.log_level.upper()))
    else:
        logging.config.fileConfig(options.log_config)

    app = web.common.dispatch.Root(options)

    if options.proxy_mode:
        app = werkzeug.contrib.fixers.ProxyFix(app)

    werkzeug.serving.run_simple(
        '0.0.0.0', options.socket_port, app,
        use_reloader=options.reloader, threaded=options.threaded)

