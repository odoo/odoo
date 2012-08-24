import logging

from . import common
from . import controllers
from . import ir_module

_logger = logging.getLogger(__name__)

class Options(object):
    pass

def wsgi_postload():
    import openerp
    import os
    import tempfile
    import getpass
    _logger.info("embedded mode")
    o = Options()
    o.dbfilter = openerp.tools.config['dbfilter']
    o.server_wide_modules = openerp.conf.server_wide_modules or ['web']
    try:
        username = getpass.getuser()
    except Exception:
        username = "unknown"
    o.session_storage = os.path.join(tempfile.gettempdir(), "oe-sessions-" + username)
    o.addons_path = openerp.modules.module.ad_paths
    o.serve_static = True
    o.backend = 'local'

    app = common.http.Root(o)
    openerp.wsgi.register_wsgi_handler(app)

