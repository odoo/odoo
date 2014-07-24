import pprint
import urllib2
import werkzeug
import werkzeug.urls
import werkzeug.wrappers

from openerp import tools
from openerp import SUPERUSER_ID

from openerp.addons.web import http
from openerp.addons.web.http import request


class main(http.Controller):
	
    def content_disposition(self,filename):
        filename = filename.encode('utf8')
        escaped = urllib2.quote(filename)
        browser = request.httprequest.user_agent.browser
        version = int((request.httprequest.user_agent.version or '0').split('.')[0])
        if browser == 'msie' and version < 9:
            return "attachment; filename=%s" % escaped
        elif browser == 'safari':
            return "attachment; filename=%s" % filename
        else:
            return "attachment; filename*=UTF-8''%s" % escaped
        
         
    @http.route('/slides', type="http", auth="public", website=True,)
    def slides(self ,search=""):
    	attachment_obj = request.registry['ir.attachment']
    	attachment_ids = attachment_obj.search(request.cr, request.uid, [("is_slide","=","TRUE"),("name","like",search)],[])
    	attachment = attachment_obj.browse(request.cr, request.uid, attachment_ids)	
        return request.website.render('slides.home', {"attachment" : attachment})
       
        
    @http.route('/slides/download/<model("ir.attachment"):slide>', type='http', auth="public", website=True,)
    def download(self, slide):        
        return request.make_response(slide.url,[('Content-Type', 'application/octet-stream'),('Content-Disposition',self.content_disposition(slide.datas_fname))])
            
            
    @http.route('/slides/view/<model("ir.attachment"):slide>', type="http", auth="public", website=True)
    def view(self ,slide):
        return request.website.render('slides.view', {"slide" : slide})

    @http.route(['/slides/thumb/<int:document_id>'], type='http', auth="public", website=True)
    def slide_thumb(self, document_id=0, **post):
        cr, uid, context = request.cr, request.uid, request.context
        response = werkzeug.wrappers.Response()
        Files = request.registry['ir.attachment']
        Website = request.registry['website']
        user = Files.browse(cr, SUPERUSER_ID, document_id, context=context)
        return Website._image(cr, SUPERUSER_ID, 'ir.attachment', user.id, 'image', response, max_height=250)