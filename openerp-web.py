#!/usr/bin/env python
import optparse,os,sys,tempfile

import cherrypy
import cherrypy.lib.static

optparser = optparse.OptionParser()
optparser.add_option("-p", "--port", dest="server.socket_port", default=8002,
                     help="listening port", type="int", metavar="NUMBER")
optparser.add_option("-s", "--session-path", dest="tools.sessions.storage_path",
                     default=os.path.join(tempfile.gettempdir(), "cpsessions"),
                     help="directory used for session storage", metavar="DIR")
optparser.add_option("--server-host", dest="openerp.server.host",
                     default='127.0.0.1', help="OpenERP server hostname", metavar="HOST")
optparser.add_option("--server-port", dest="openerp.server.port", default=8069,
                     help="OpenERP server port", type="int", metavar="NUMBER")
optparser.add_option("--db-filter", dest="openerp.dbfilter", default='.*',
                     help="Filter listed database", metavar="REGEXP")

path_root = os.path.dirname(os.path.abspath(__file__))
path_addons = os.path.join(path_root, 'addons')
if path_addons not in sys.path:
    sys.path.insert(0, path_addons)

import base

def main(options):
    # change the timezone of the program to the OpenERP server's assumed timezone
    os.environ["TZ"] = "UTC"

    DEFAULT_CONFIG = {
        'server.socket_host': '0.0.0.0',
        'tools.sessions.on': True,
        'tools.sessions.storage_type': 'file',
        'tools.sessions.timeout': 60
    }

    cherrypy.config.update(config=DEFAULT_CONFIG)
    if os.path.exists(os.path.join(path_root,'openerp-web.cfg')):
        cherrypy.config.update(os.path.join(path_root,'openerp-web.cfg'))
    if os.path.exists(os.path.expanduser('~/.openerp_webrc')):
        cherrypy.config.update(os.path.expanduser('~/.openerp_webrc'))
    cherrypy.config.update(options)

    if not os.path.exists(cherrypy.config['tools.sessions.storage_path']):
        os.makedirs(cherrypy.config['tools.sessions.storage_path'], 0700)

    return base.common.Root()

if __name__ == "__main__":
    (o, args) = optparser.parse_args(sys.argv[1:])
    o = dict((k, v) for k, v in vars(o).iteritems() if v is not None)

    cherrypy.tree.mount(main(o))
    cherrypy.server.subscribe()
    cherrypy.engine.start()
    cherrypy.engine.block()

