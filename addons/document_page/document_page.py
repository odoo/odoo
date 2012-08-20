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

from osv import fields, osv
from tools.translate import _
import difflib
import tools

class document_page(osv.osv):
    _name = "document.page"
    _description = "Document Page"
    _order = 'name'

    def _get_page_index(self, cr, uid, page):
        index = []
        for subpage in page.child_ids:
            index += ["<li>"+ self._get_page_index(cr, uid, subpage) +"</li>"]
        r = '<a href="#id=%s">%s</a>'%(page.id,page.name)
        if index:
            r += "<ul>" + "".join(index) + "</ul>"
        return r

    def _get_display_content(self, cr, uid, ids, name, args, context=None):
        res = {}
        for page in self.browse(cr, uid, ids, context=context):
            if page.type == "category":
               content = self._get_page_index(cr, uid, page)
            else:
               content = page.content
            res[page.id] =  content
        return res

    _columns = {
        'name': fields.char('Title', required=True),
        'type':fields.selection([('content','Content'), ('category','Category')], 'Type', help="Page type"), 

        'parent_id': fields.many2one('document.page', 'Category', domain=[('type','=','category')]),
        'child_ids': fields.one2many('document.page', 'parent_id', 'Children'),

        'content': fields.text("Content"),
        'display_content': fields.function(_get_display_content, string='Displayed Content', type='text'),

        'history_ids': fields.one2many('document.page.history', 'page_id', 'History'),
        'menu_id': fields.many2one('ir.ui.menu', "Menu", readonly=True),

        'create_date': fields.datetime("Created on", select=True, readonly=True),
        'create_uid': fields.many2one('res.users', 'Author', select=True, readonly=True),
        'write_date': fields.datetime("Modification Date", select=True, readonly=True),
        'write_uid': fields.many2one('res.users', "Last Contributor", select=True),
    }
    _defaults = {
        'type':'content',
    }

    def onchange_parent_id(self, cr, uid, ids, parent_id, content, context=None):
        res = {}
        if parent_id and not content:
            parent = self.browse(cr, uid, parent_id, context=context)
            if parent.type == "category":
                res['value'] = {
                    'content': parent.content,
                }
        return res

    def create_history(self, cr, uid, ids, vals, context=None):
        for i in ids:
            history = self.pool.get('document.page.history')
            if vals.get('content'):
                res = {
                    'content': vals.get('content', ''),
                    'page_id': i,
                }
                history.create(cr, uid, res)

    def create(self, cr, uid, vals, context=None):
        page_id = super(document_page, self).create(cr, uid, vals, context)
        self.create_history(cr, uid, [page_id], vals, context)
        return page_id

    def write(self, cr, uid, ids, vals, context=None):
        result = super(document_page, self).write(cr, uid, ids, vals, context)
        self.create_history(cr, uid, ids, vals, context)
        return result

class document_page_history(osv.osv):
    _name = "document.page.history"
    _description = "Document Page History"
    _order = 'id DESC'
    _rec_name = "create_date"

    _columns = {
          'page_id': fields.many2one('document.page', 'Page'),
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
            line1 = tools.ustr(text1.splitlines(1))
        if text2:
            line2=tools.ustr(text2.splitlines(1))
        if (not line1 and not line2) or (line1 == line2):
            raise osv.except_osv(_('Warning!'), _('There are no changes in revisions.'))
        diff = difflib.HtmlDiff()
        return diff.make_file(line1, line2, "Revision-%s" % (v1), "Revision-%s" % (v2), context=False)

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
