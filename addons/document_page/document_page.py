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

from openerp.osv import fields, osv
from openerp.tools.translate import _
import difflib


class BlogCategory(osv.Model):
    _name = 'blog.category'
    _description = 'Blog Category'
    _inherit = ['mail.thread']
    _order = 'name'

    _columns = {
        'name': fields.char('Name', required=True),
        'description': fields.text('Description'),
        'template': fields.text('Template'),
        'blog_ids': fields.one2many(
            'blog.post', 'category_id',
            'Blogs',
        ),
    }


class BlogTag(osv.Model):
    _name = 'blog.tag'
    _description = 'Blog Tag'
    _order = 'name'

    _columns = {
        'name': fields.char('Name', required=True),
    }


class BlogPost(osv.Model):
    _name = "blog.post"
    _description = "Blog Post"
    _inherit = ['mail.thread']
    _order = 'name'

    _columns = {
        'name': fields.char('Title', required=True),
        'category_id': fields.many2one(
            'blog.category', 'Category',
            ondelete='set null',
        ),
        'tag_ids': fields.many2many(
            'blog.tag', 'blog_tag_rel',
            'blog_id', 'tag_id',
            'Tags',
        ),

        'content': fields.text("Content"),

        'history_ids': fields.one2many('blog.post.history', 'post_id', 'History'),
        'menu_id': fields.many2one('ir.ui.menu', "Menu", readonly=True),

        'create_date': fields.datetime("Created on", select=True, readonly=True),
        'create_uid': fields.many2one('res.users', 'Author', select=True, readonly=True),
        'write_date': fields.datetime("Modification Date", select=True, readonly=True),
        'write_uid': fields.many2one('res.users', "Last Contributor", select=True, readonly=True),
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


class BlogPostHistory(osv.Model):
    _name = "blog.post.history"
    _description = "Document Page History"
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
        history_pool = self.pool.get('document.page.history')
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

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
