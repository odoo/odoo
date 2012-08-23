try:
    # embedded
    import openerp.addons.web.common.http as openerpweb
    import openerp.addons.web.controllers.main as webmain
except ImportError:
    # standalone
    import web.common.http as openerpweb
    import web.controllers.main as webmain

class Shortcuts(openerpweb.Controller):
    _cp_path = "/web/shortcuts"

    @openerpweb.jsonrequest
    def list(self, req):
        return req.session.model('ir.ui.view_sc').get_sc(
            req.session._uid, "ir.ui.menu", req.session.eval_context(req.context))

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
