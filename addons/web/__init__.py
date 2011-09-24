import common
import controllers
import common.dispatch
import logging
import optparse

_logger = logging.getLogger(__name__)

class Options(object):
    pass

def wsgi_postload():
    import openerp.wsgi
    import os
    import tempfile
    _logger.info("embedded mode")
    o = Options()
    o.dbfilter = '.*'
    o.session_storage = os.path.join(tempfile.gettempdir(), "oe-sessions")
    o.addons_path = os.path.dirname(os.path.dirname(__file__))
    o.serve_static = True
    o.backend = 'local'

    app = common.dispatch.Root(o)
    openerp.wsgi.register_wsgi_handler(app)

