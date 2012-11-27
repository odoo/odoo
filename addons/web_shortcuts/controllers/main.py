import openerp

class Shortcuts(openerp.addons.web.http.Controller):
    _cp_path = "/web/shortcuts"

    @openerp.addons.web.http.jsonrequest
    def list(self, req):
        return req.session.model('ir.ui.view_sc').get_sc(
            req.session._uid, "ir.ui.menu", req.session.eval_context(req.context))

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
