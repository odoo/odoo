# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-Today OpenERP SA (<http://www.openerp.com>).
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


from openerp import tools
from openerp import SUPERUSER_ID
from openerp.osv import osv, fields
from openerp.tools.translate import _

class Blog(osv.Model):
    _name = 'blog.blog'
    _description = 'Blogs'
    _inherit = ['mail.thread', 'website.seo.metadata']
    _order = 'name'
    _columns = {
        'name': fields.char('Blog Name', required=True),
        'subtitle': fields.char('Blog Subtitle'),
        'description': fields.text('Description'),
        'image': fields.binary('Image'),
    }


class BlogTag(osv.Model):
    _name = 'blog.tag'
    _description = 'Blog Tag'
    _inherit = ['website.seo.metadata']
    _order = 'name'
    _columns = {
        'name': fields.char('Name', required=True),
    }

class MailMessage(osv.Model):
    _inherit = 'mail.message'
    _columns = {
        'discussion': fields.char('Discussion Unique Name'),
    }

class BlogPost(osv.Model):
    _name = "blog.post"
    _description = "Blog Post"
    _inherit = ['mail.thread', 'website.seo.metadata']
    _order = 'id DESC'
    _columns = {
        'name': fields.char('Title', required=True, translate=True),
        'sub_title' : fields.char('Sub Title', translate=True),
        'content_image': fields.binary('Background Image'),
        'blog_id': fields.many2one(
            'blog.blog', 'Blog',
            required=True, ondelete='cascade',
        ),
        'tag_ids': fields.many2many(
            'blog.tag', string='Tags',
        ),
        'content': fields.html('Content', translate=True),
        # website control
        'website_published': fields.boolean(
            'Publish', help="Publish on the website"
        ),
        'website_message_ids': fields.one2many(
            'mail.message', 'res_id',
            domain=lambda self: [
                '&', '&', ('model', '=', self._name), ('type', '=', 'comment') , ('discussion', '=', False)
            ],
            string='Website Messages',
            help="Website communication history",
        ),
        # creation / update stuff
        'create_date': fields.datetime(
            'Created on',
            select=True, readonly=True,
        ),
        'create_uid': fields.many2one(
            'res.users', 'Author',
            select=True, readonly=True,
        ),
        'write_date': fields.datetime(
            'Last Modified on',
            select=True, readonly=True,
        ),
        'write_uid': fields.many2one(
            'res.users', 'Last Contributor',
            select=True, readonly=True,
        ),
        'visits': fields.integer('No of Views'),
        'ranking': fields.float('Ranking'),
        'author_image': fields.related('create_uid','partner_id', 'image_small', string='Author Photo', type='binary')
    }
    _defaults = {
        'website_published': False,
        'visits': 0,
        'ranking': 0
    }

    def create(self, cr, uid, vals, context=None):
        if context is None:
            context = {}
        create_context = dict(context, mail_create_nolog=True)
        return super(BlogPost, self).create(cr, uid, vals, context=create_context)

    def copy(self, cr, uid, id, default=None, context=None):
        default = default or {}
        default.update({
            'website_published': False,
        })
        return super(BlogPost, self).copy(cr, uid, id, default=default, context=context)

