#!/usr/bin/env python
import optparse
import os
import sys
import tempfile

import werkzeug.serving

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

path_root = os.path.dirname(os.path.abspath(__file__))
path_addons = os.path.join(path_root, 'addons')
if path_addons not in sys.path:
    sys.path.insert(0, path_addons)

import base

if __name__ == "__main__":
    (options, args) = optparser.parse_args(sys.argv[1:])
    options.serve_static = True

    os.environ["TZ"] = "UTC"
    app = base.common.Root(options)

    werkzeug.serving.run_simple(
        '0.0.0.0', options.socket_port, app,
        use_reloader=True, threaded=True)

