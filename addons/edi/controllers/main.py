import simplejson
import werkzeug.urls

import openerp
import openerp.addons.web.controllers.main as webmain

class EDI(openerp.http.Controller):

    @openerp.http.route('/edi/import_url', type='http', auth='none')
    def import_url(self, url):
        # http://hostname:8069/edi/import_url?url=URIEncodedURL
        req = openerp.http.request
        modules = webmain.module_boot(req) + ['edi']
        modules_str = ','.join(modules)
        modules_json = simplejson.dumps(modules)
        js = "\n        ".join('<script type="text/javascript" src="%s"></script>' % i for i in webmain.manifest_list(req, modules_str, 'js'))
        css = "\n        ".join('<link rel="stylesheet" href="%s">' % i for i in webmain.manifest_list(req, modules_str, 'css'))

        # `url` may contain a full URL with a valid query string, we basically want to watch out for XML brackets and double-quotes 
        safe_url = werkzeug.url_quote_plus(url,':/?&;=')

        return webmain.html_template % {
            'js': js,
            'css': css,
            'modules': modules_json,
            'init': 's.edi.edi_import("%s");' % safe_url,
        }

    @openerp.http.route('/edi/import_edi_url', type='json', auth='none')
    def import_edi_url(self, url):
        req = openerp.http.request
        result = req.session.proxy('edi').import_edi_url(req.session._db, req.session._uid, req.session._password, url)
        if len(result) == 1:
            return {"action": webmain.clean_action(req, result[0][2])}
        return True

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
