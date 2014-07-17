import pprint
from openerp.addons.web import http
from openerp.addons.web.http import request

import urllib2


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
        
         
    @http.route('/slides', type="http" , website=True,)
    def slides(self ,search=""):
    	objattachment = request.registry['ir.attachment']
    	attachment = objattachment.search_read(request.cr, request.uid, [("mimetype","=","application/pdf"),("is_slide","=","TRUE"),("name","like",search)],[])
    	
    	pprint.pprint(attachment)    	
        return request.website.render('slides.home', {"attachment" : attachment})
       
        
    @http.route('/slides/download/<model("ir.attachment"):slide>', type='http', website=True,)
    def download(self, slide):        
        return request.make_response(slide.url,[('Content-Type', 'application/octet-stream'),('Content-Disposition',self.content_disposition(slide.datas_fname))])
            
            
    @http.route('/slides/view/<model("ir.attachment"):slide>', type="http" , website=True)
    def view(self ,slide):
        return request.website.render('slides.view', {"slide" : slide})
        
        