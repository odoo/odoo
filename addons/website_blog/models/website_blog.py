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

import random
import difflib
from datetime import datetime

from openerp import tools
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

    def _compute_ranking(self, cr, uid, ids, name, arg, context=None):
        res = {}
        for blog_post in self.browse(cr, uid, ids, context=context):
            d = datetime.now() - datetime.strptime(blog_post.create_date, tools.DEFAULT_SERVER_DATETIME_FORMAT)
            res[blog_post.id] = blog_post.visits * (0.5+random.random()) / max(3, d.days)
        return res

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
        'history_ids': fields.one2many(
            'blog.post.history', 'post_id',
            'History', help='Last post modifications',
            deprecated= 'Will be removed in v9.'
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
        'visits': fields.integer('No of Views', readonly=True),
        'ranking': fields.function(_compute_ranking, string='Ranking', type='float'),
    }
    _defaults = {
        'website_published': False,
        'visits': 0,
        'ranking': 0
    }

    def create_history(self, cr, uid, ids, vals, context=None):
        for i in ids:
            history = self.pool.get('blog.post.history')
            if vals.get('content'):
                res = {
                    'content': vals.get('content', ''),
                    'post_id': i,
                }
                history.create(cr, uid, res)

    def create(self, cr, uid, vals, context=None):
        if context is None:
            context = {}
        create_context = dict(context, mail_create_nolog=True)
        post_id = super(BlogPost, self).create(cr, uid, vals, context=create_context)
        self.create_history(cr, uid, [post_id], vals, context)
        return post_id

    def write(self, cr, uid, ids, vals, context=None):
        result = super(BlogPost, self).write(cr, uid, ids, vals, context)
        self.create_history(cr, uid, ids, vals, context)
        return result

    def copy(self, cr, uid, id, default=None, context=None):
        if default is None:
            default = {}
        default.update({
            'website_message_ids': [],
            'website_published': False,
            'website_published_datetime': False,
        })
        return super(BlogPost, self).copy(cr, uid, id, default=default, context=context)

class BlogPostHistory(osv.Model):
    _name = "blog.post.history"
    _description = "Blog Post History"
    _order = 'id DESC'
    _rec_name = "create_date"

    _columns = {
        'post_id': fields.many2one('blog.post', 'Blog Post'),
        'summary': fields.char('Summary', size=256, select=True),
        'content': fields.text("Content"),
        'create_date': fields.datetime("Date"),
        'create_uid': fields.many2one('res.users', "Modified By"),
    }

    def getDiff(self, cr, uid, v1, v2, context=None):
        history_pool = self.pool.get('blog.post.history')
        text1 = history_pool.read(cr, uid, [v1], ['content'])[0]['content']
        text2 = history_pool.read(cr, uid, [v2], ['content'])[0]['content']
        line1 = line2 = ''
        if text1:
            line1 = text1.splitlines(1)
        if text2:
            line2 = text2.splitlines(1)
        if (not line1 and not line2) or (line1 == line2):
            raise osv.except_osv(_('Warning!'), _('There are no changes in revisions.'))
        diff = difflib.HtmlDiff()
        return diff.make_table(line1, line2, "Revision-%s" % (v1), "Revision-%s" % (v2), context=True)

