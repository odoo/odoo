#!/usr/bin/env python
import optparse
import os
import sys
import tempfile
import logging

import werkzeug.serving

path_root = os.path.dirname(os.path.abspath(__file__))
path_addons = os.path.join(path_root, 'addons')
if path_addons not in sys.path:
    sys.path.insert(0, path_addons)

optparser = optparse.OptionParser()
optparser.add_option("-p", "--port", dest="socket_port", default=8002,
                     help="listening port", type="int", metavar="NUMBER")
optparser.add_option("-s", "--session-path", dest="session_storage",
                     default=os.path.join(tempfile.gettempdir(), "oe-sessions"),
                     help="directory used for session storage", metavar="DIR")
optparser.add_option("--server-host", dest="server_host",
                     default='127.0.0.1', help="OpenERP server hostname", metavar="HOST")
optparser.add_option("--server-port", dest="server_port", default=8069,
                     help="OpenERP server port", type="int", metavar="NUMBER")
optparser.add_option("--db-filter", dest="dbfilter", default='.*',
                     help="Filter listed database", metavar="REGEXP")
optparser.add_option('--addons-path', dest='addons_path', default=path_addons,
                    help="Path do addons directory", metavar="PATH")
optparser.add_option('--no-serve-static', dest='serve_static',
                     default=True, action='store_false',
                     help="Do not serve static files via this server")
optparser.add_option('--reloader', dest='reloader',
                     default=False, action='store_true',
                     help="Reload application when python files change")
optparser.add_option("--log-level", dest="log_level",
                     default='debug', help="Log level", metavar="LOG_LEVEL")
optparser.add_option("--log-config", dest="log_config",
                     default='', help="Log config file", metavar="LOG_CONFIG")

import web.common.dispatch

if __name__ == "__main__":
    (options, args) = optparser.parse_args(sys.argv[1:])

    os.environ["TZ"] = "UTC"
    
    if not options.log_config:
        logging.basicConfig(level=getattr(logging, options.log_level.upper()))
    else:
        logging.config.fileConfig(options.log_config)
    
    app = web.common.dispatch.Root(options)

    werkzeug.serving.run_simple(
        '0.0.0.0', options.socket_port, app,
        use_reloader=options.reloader, threaded=True)

