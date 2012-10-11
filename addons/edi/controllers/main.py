import openerp.addons.web.common.http as openerpweb
import openerp.addons.web.controllers.main as webmain

class EDI(openerpweb.Controller):
    # http://hostname:8069/edi/import_url?url=URIEncodedURL
    _cp_path = "/edi"

    @openerpweb.httprequest
    def import_url(self, req, url):
        d = self.template(req)
        d["init"] = 's.edi.edi_import("%s");'%(url)
        r = webmain.html_template % d
        return r

    @openerpweb.jsonrequest
    def import_edi_url(self, req, url):
        result = req.session.proxy('edi').import_edi_url(req.session._db, req.session._uid, req.session._password, url)
        if len(result) == 1:
            return {"action": webmain.clean_action(req, result[0][2])}
        return True

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
