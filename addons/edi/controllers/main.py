import simplejson
import urllib

import openerp.addons.web.http as openerpweb
import openerp.addons.web.controllers.main as webmain

class EDI(openerpweb.Controller):
    # http://hostname:8069/edi/import_url?url=URIEncodedURL
    _cp_path = "/edi"

    @openerpweb.httprequest
    def import_url(self, req, url):
        modules = webmain.module_boot(req) + ['edi']
        modules_str = ','.join(modules)
        modules_json = simplejson.dumps(modules)
        js = "\n        ".join('<script type="text/javascript" src="%s"></script>' % i for i in webmain.manifest_list(req, modules_str, 'js'))
        css = "\n        ".join('<link rel="stylesheet" href="%s">' % i for i in webmain.manifest_list(req, modules_str, 'css'))

        # `url` may contain a full URL with a valid query string, we basically want to watch out for XML brackets and double-quotes 
        safe_url = urllib.quote_plus(url,':/?&;=')

        return webmain.html_template % {
            'js': js,
            'css': css,
            'modules': modules_json,
            'init': 's.edi.edi_import("%s");' % safe_url,
        }

    @openerpweb.jsonrequest
    def import_edi_url(self, req, url):
        result = req.session.proxy('edi').import_edi_url(req.session._db, req.session._uid, req.session._password, url)
        if len(result) == 1:
            return {"action": webmain.clean_action(req, result[0][2])}
        return True

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
