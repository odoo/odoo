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
from openerp.osv import fields, osv
from urlparse import urlparse,parse_qs
import urllib2
import json


class ir_attachment_tags(osv.osv):
    _name = 'ir.attachment.tag'
    _columns = {
        'name': fields.char('Name')
    }

class document_directory(osv.osv):
    _name = 'document.directory'
    _inherit = ['document.directory','mail.thread']

    _columns = {
        'website_published': fields.boolean(
            'Publish', help="Publish on the website", copy=False,
        ),
    }

class MailMessage(osv.Model):
    _inherit = 'mail.message'

    _columns = {
        'path': fields.char(
            'Discussion Path', select=1,
            help='Used to display messages in a paragraph-based chatter using a unique path;'),
    }

class ir_attachment(osv.osv):
    _name = 'ir.attachment'
    _inherit = ['ir.attachment','mail.thread']
    
    _order = "id desc"
    _columns = {
        'is_slide': fields.boolean('Is Slide'),
        'slide_type': fields.selection([('ppt', 'Presentation'), ('doc', 'Document'), ('video', 'Video')], 'Type'),
        'tag_ids': fields.many2many('ir.attachment.tag', 'rel_attachments_tags', 'attachment_id', 'tag_id', 'Tags'),
        'image': fields.binary('Thumb'),
        'slide_views': fields.integer('Number of Views'),
        'youtube_id': fields.char(string="Youtube Video ID"),
        'website_published': fields.boolean(
            'Publish', help="Publish on the website", copy=False,
        ),
        'website_message_ids': fields.one2many(
            'mail.message', 'res_id',
            domain=lambda self: [
                '&', '&', ('model', '=', self._name), ('type', '=', 'comment'), ('path', '=', False)
            ],
            string='Website Messages',
            help="Website communication history",
        ),
        'website_desccription': fields.html('Website Desription', tranalate=True)
    }

    def _get_slide_setting(self, cr, uid, context):
        return context.get('is_slide', False)

    def _get_slide_type(self, cr, uid, context):
        return context.get('slide_type', 'ppt')

    def _get_slide_views(self, cr, uid, context):
        return context.get('slide_views', 0)

    def get_default_channel(self, cr, uid, context):
        directory = self.pool.get('document.directory')
        vals = directory.search(cr, uid, [('name','=','Documents')])
        return vals

    _defaults = {
        'is_slide': _get_slide_setting,
        'slide_type':_get_slide_type,
        'slide_views':_get_slide_views
    }

    def set_viewed(self, cr, uid, ids, context=None):
        cr.execute("""UPDATE ir_attachment SET slide_views = slide_views+1 WHERE id IN %s""", (tuple(ids),))
        return True

    def create(self, cr, uid, values, context=None):
        if values.get('is_slide'):
            if values.get('datas_fname'):
                values['url'] = "/website_slides/" + values['datas_fname']
            elif values.get('url'):
                values["youtube_id"] = self.extract_youtube_id(values['url'].strip())
                statistics = self.youtube_statistics(values["youtube_id"])
                if statistics:
                    if statistics['items'][0].get('snippet').get('thumbnails') and statistics['items'][0]['snippet'].get('thumbnails'):
                        values['image'] = statistics['items'][0]['snippet']['thumbnails']['medium']['url']
                    if statistics['items'][0].get('statistics'):
                        values['slide_views'] = statistics['items'][0]['statistics']['viewCount']
        return super(ir_attachment, self).create(cr, uid, values, context)

    def search(self, cr, uid, args, offset=0, limit=None, order=None, context=None, count=False):
        ids = super(ir_attachment, self)._search(cr, uid, args, offset=offset, limit=limit, order=order, context=context, count=False)
        return len(ids) if count else ids
 
    def extract_youtube_id(self, url):
        youtube_id = ""
        query = urlparse(url)
        if query.hostname == 'youtu.be':
            youtube_id = query.path[1:]
        elif query.hostname in ('www.youtube.com', 'youtube.com'):
            if query.path == '/watch':
                p = parse_qs(query.query)
                youtube_id = p['v'][0]
            elif query.path[:7] == '/embed/':
                youtube_id = query.path.split('/')[2]
            elif query.path[:3] == '/v/':
                youtube_id = query.path.split('/')[2]
        return youtube_id

    def youtube_statistics(self,video_id):
        request_url = "https://www.googleapis.com/youtube/v3/videos?id=%s&key=AIzaSyBKDzf7KjjZqwPWAME6JOeHzzBlq9nrpjk&part=snippet,statistics&fields=items(id,snippet,statistics)" % (video_id)
        try:
            req = urllib2.Request(request_url)
            content = urllib2.urlopen(req).read()
        except urllib2.HTTPError:
            return False
        return json.loads(content)
