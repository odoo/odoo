# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
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
    

    @http.route(['/slides',
                 '/slides/page/<int:page>',
                 '/slides/view/<model("ir.attachment"):slideview>'
                 ], type='http', auth="public", website=True)
    def slides(self, page=1, filters='all', sorting='creation', search='', tags='', slideview=''):
        cr, uid, context = request.cr, SUPERUSER_ID, request.context
        attachment = request.registry['ir.attachment']

        if slideview:
            attachment.set_viewed(cr, uid, [slideview.id], context=context)

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
            'slideview':slideview,
        })
        return request.website.render('website_slides.home', values)


    @http.route('/slides/thumb/<int:document_id>', type='http', auth="public", website=True)
    def slide_thumb(self, document_id=0, **post):
        cr, uid, context = request.cr, SUPERUSER_ID, request.context
        response = werkzeug.wrappers.Response()
        Files = request.registry['ir.attachment']
        Website = request.registry['website']
        user = Files.browse(cr, uid, document_id, context=context)
        return Website._image(cr, uid, 'ir.attachment', user.id, 'image', response, max_height=225)

        
