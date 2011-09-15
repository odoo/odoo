import common
import controllers
import common.dispatch
import logging

_logger = logging.getLogger(__name__)


try:
    import openerp.wsgi
    import os
    import tempfile
    _logger.info("embedded mode")
    class Options(object):
        pass
    o = Options()
    o.dbfilter = '.*'
    o.session_storage = os.path.join(tempfile.gettempdir(), "oe-sessions")
    o.addons_path = os.path.dirname(os.path.dirname(__file__))
    o.serve_static = True
    o.backend = 'local'

    app = common.dispatch.Root(o)
    #import openerp.wsgi
    openerp.wsgi.register_wsgi_handler(app)

except ImportError:
    _logger.info("standalone mode")

# TODO
# if we detect that we are imported from the openerp server register common.Root() as a wsgi entry point

