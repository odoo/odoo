import pprint
import urllib2
import werkzeug
import werkzeug.urls
import werkzeug.wrappers

from openerp import tools
from openerp import SUPERUSER_ID

from openerp.addons.web import http
from openerp.addons.web.http import request
from openerp.addons.website.models.website import slug


class main(http.Controller):
    _slides_per_page = 8

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


    @http.route(['/slides',
                 '/slides/page/<int:page>',
                 ], type='http', auth="public", website=True)
    def slides(self, page=1, filters='all', sorting='creation', search='', tags=''):
        cr, uid, context = request.cr, request.uid, request.context
        attachment = request.registry['ir.attachment']

        domain = [("is_slide","=","TRUE")]
        if search:
            domain += [('name', 'ilike', search)]
        
        if tags:
            domain += [('tag_ids.name', 'like', tags)]
        
        if filters == 'ppt':
            domain += [('slide_type', '=', 'ppt')]
        elif filters == 'doc':
            domain += [('slide_type', '=', 'doc')]
        elif filters == 'video':
            domain += [('slide_type', '=', 'video')]
        else:
            filters = 'all'
        
        if sorting == 'date':
            order = 'write_date desc'
        elif sorting == 'view':
            order = 'slide_views desc'
        else:
            sorting = 'creation'
            order = 'create_date desc'

        attachment_count = attachment.search(cr, uid, domain, count=True, context=context)
        url = "/slides"

        url_args = {}
        if search:
            url_args['search'] = search
        if filters:
            url_args['filters'] = filters
        if sorting:
            url_args['sorting'] = sorting
        if tags:
            url_args['tags'] = tags
        pager = request.website.pager(url=url, total=attachment_count, page=page,
                                      step=self._slides_per_page, scope=self._slides_per_page,
                                      url_args=url_args)

        obj_ids = attachment.search(cr, uid, domain, limit=self._slides_per_page, offset=pager['offset'], order=order, context=context)
        attachment_ids = attachment.browse(cr, uid, obj_ids, context=context)
        print ">>>>>>>>",attachment_ids,domain,order
        values = {}
        values.update({
            'attachment_ids': attachment_ids,
            'attachment_count': attachment_count,
            'pager': pager,
            'filters': filters,
            'sorting': sorting,
            'search': search,
            'tags':tags,
        })
        return request.website.render('slides.home', values)


    @http.route('/slides/download/<model("ir.attachment"):slide>', type='http', auth="public", website=True,)
    def download(self, slide):        
        return request.make_response(slide.url,[('Content-Type', 'application/octet-stream'),('Content-Disposition',self.content_disposition(slide.datas_fname))])
            
            
    @http.route('/slides/view/<model("ir.attachment"):slide>', type="http", auth="public", website=True)
    def view(self ,slide):
        cr, uid, context = request.cr, request.uid, request.context
        # increment view counter
        request.registry['ir.attachment'].set_viewed(cr, SUPERUSER_ID, [slide.id], context=context)
        return request.website.render('slides.view', {"slide" : slide})


    @http.route(['/slides/thumb/<int:document_id>'], type='http', auth="public", website=True)
    def slide_thumb(self, document_id=0, **post):
        cr, uid, context = request.cr, request.uid, request.context
        response = werkzeug.wrappers.Response()
        Files = request.registry['ir.attachment']
        Website = request.registry['website']
        user = Files.browse(cr, SUPERUSER_ID, document_id, context=context)
        return Website._image(cr, SUPERUSER_ID, 'ir.attachment', user.id, 'image', response, max_height=225)


    @http.route('/set_slide_thumbnail/', type='http', auth="public", website=True)
    def set_slide_thumbnail(self,**post):
        if post.get('id'):
            request.registry['ir.attachment'].write(request.cr, request.uid, int(post['id']), {'image' : post['dataURL'][22:]}, context=request.context) 
        return ""
