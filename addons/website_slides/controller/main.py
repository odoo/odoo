# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
import werkzeug
from urlparse import urlparse
import simplejson

from openerp import tools
from openerp import SUPERUSER_ID

from openerp.addons.web import http
from openerp.addons.web.http import request


class main(http.Controller):
    _slides_per_page = 8
    _slides_per_list = 20

    def _slides_urldata(self):
        urldata = urlparse(request.httprequest.url)
        # print ">>>>>>>>",urldata
        values = {}
        values.update({
            'urlscheme':urldata.scheme+'://',
            'urlhost':urldata.netloc,
            'urlpath':urldata.path,
            'urlquery':urldata.query,
        })
        return values

    def _slides_message(self, user, attachment_id=0, **post):
        cr, uid, context = request.cr, request.uid, request.context
        attachment = request.registry['ir.attachment']
        partner_obj = request.registry['res.partner']

        if uid != request.website.user_id.id:
            partner_ids = [user.partner_id.id]
        else:
            partner_ids = attachment._find_partner_from_emails(cr, SUPERUSER_ID, 0, [post.get('email')], context=context)
            if not partner_ids or not partner_ids[0]:
                partner_ids = [partner_obj.create(cr, SUPERUSER_ID, {'name': post.get('name'), 'email': post.get('email')}, context=context)]

        message_id = attachment.message_post(
            cr, SUPERUSER_ID, int(attachment_id),
            body=post.get('comment'),
            type='comment',
            subtype='mt_comment',
            author_id=partner_ids[0],
            path=post.get('path', False),
            context=dict(context, mail_create_nosubcribe=True))
        return message_id


    @http.route(['/slides',
                 '/slides/page/<int:page>',                 
                 ], type='http', auth="public", website=True)
    def slides(self, page=1, filters='all', sorting='creation', search='', tags=''):
        cr, uid, context = request.cr, SUPERUSER_ID, request.context
        attachment = request.registry['ir.attachment']

        domain = [("is_slide","=","TRUE")]
        if search:
            domain += [('name', 'ilike', search)]
        
        if tags:
            domain += [('tag_ids.name', '=', tags)]
        
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
        return request.website.render('website_slides.home', values)


    @http.route('/slides/view/<model("ir.attachment"):slideview>', type='http', auth="public", website=True)
    def slide_view(self, slideview, filters='', sorting='', search='', tags=''):        
        cr, uid, context = request.cr, SUPERUSER_ID, request.context
        attachment = request.registry['ir.attachment']
        domain = [("is_slide","=","TRUE")]
        
        # increment view counter 
        attachment.set_viewed(cr, uid, [slideview.id], context=context)

        # most viewed slides
        ids = attachment.search(cr, uid, domain, limit=self._slides_per_list, offset=0, order='slide_views desc', context=context)
        most_viewed_ids = attachment.browse(cr, uid, ids, context=context)

        # related slides
        tags = slideview.tag_ids.ids
        if tags:
            domain += [('tag_ids', 'in', tags)]
        ids = attachment.search(cr, uid, domain, limit=self._slides_per_list, offset=0, context=context)
        related_ids = attachment.browse(cr, uid, ids, context=context)

        # get comments 
        comments = slideview.website_message_ids
        
        # get share url
        urldata = self._slides_urldata()
        shareurl = urldata['urlscheme']+urldata['urlhost']+urldata['urlpath']

        values = {}
        values.update({
            'slideview':slideview,
            'most_viewed_ids':most_viewed_ids,
            'related_ids': related_ids,
            'comments': comments,
            'shareurl':shareurl,
        })
        return request.website.render('website_slides.slide_view', values)


    @http.route('/slides/comment/<model("ir.attachment"):slideview>', type='http', auth="public", methods=['POST'], website=True)
    def slides_comment(self, slideview, **post):
        cr, uid, context = request.cr, request.uid, request.context
        attachment = request.registry['ir.attachment']
        if post.get('comment'):
            user = request.registry['res.users'].browse(cr, uid, uid, context=context)
            attachment = request.registry['ir.attachment']
            attachment.check_access_rights(cr, uid, 'read')
            self._slides_message(user, slideview.id, **post)            
        return werkzeug.utils.redirect(request.httprequest.referrer + "#discuss")


    @http.route('/slides/thumb/<int:document_id>', type='http', auth="public", website=True)
    def slide_thumb(self, document_id=0, **post):
        cr, uid, context = request.cr, SUPERUSER_ID, request.context
        response = werkzeug.wrappers.Response()
        Files = request.registry['ir.attachment']
        Website = request.registry['website']
        user = Files.browse(cr, uid, document_id, context=context)
        return Website._image(cr, uid, 'ir.attachment', user.id, 'image', response, max_height=225)


    @http.route('/slides/get_tags', type='http', auth="public", methods=['GET'], website=True)
    def tag_read(self, **post):
        tags = request.registry['ir.attachment.tag'].search_read(request.cr, request.uid, [], ['name'], context=request.context)
        data = [tag['name'] for tag in tags]
        return simplejson.dumps(data)

    @http.route(['/slides/add_slide'], type='http', auth="user", methods=['POST'], website=True)
    def add_slide(self, *args, **post):
        print '>>>>>>>>',args
        print 'post',post

