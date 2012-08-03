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
    _inherit = "document.page"
    _description = "Document Page"
    _order = 'name'

    _columns = {
        'name': fields.char('Title', size=256, select=True, required=True),
        'type':fields.selection([('normal','Content Page'),  ('index','Index Page')], 'Type', help="Define the type of the document"), 

        'parent_id': fields.many2one('document.page', 'Section', select=1 , ondelete='set null'),
        'child_ids': fields.one2many('document.page', 'parent_id', 'Children'),

        'display_content': fields.text('Displayed Content'),
        'content': fields.text("Content"),
        'history_ids': fields.one2many('document.page.history', 'document_id', 'History'),
        'menu_id': fields.many2one('ir.ui.menu', "Menu", readonly=True),

        'create_date': fields.datetime("Created on", select=True, readonly=True),
        'write_date': fields.datetime("Modification Date", select=True, readonly=True),
        'write_uid': fields.many2one('res.users', "Last Contributor", select=True),
        'create_uid': fields.many2one('res.users', 'Author', select=True, readonly=True),

        'index': fields.char('Index', size=256),
        'minor_edit': fields.boolean('Minor edit', select=True),
        'edit_summary': fields.char('Summary', size=256),
        'tags': fields.char('Keywords', size=1024, select=True),

    }
    _defaults = {
        'type':'normal',
    }

    def onchange_parent_id(self, cr, uid, ids, parent_id, content, context=None):
        if (not parent_id) or content:
            return {}
        grp = self.pool.get('document.page.type').browse(cr, uid, parent_id, context=context)
        template = grp.content_template
        try:
            s[-1] = str(int(s[-1])+1)
        except:
            pass
        return {
            'value':{
                'content': template,
            }
        }

    def onchange_content(self, cr, uid, ids, content, context=None):
        if content:
            return {'value':{'summary': content}}
        return {}

    def copy_data(self, cr, uid, id, default=None, context=None):
        return super(document_page2, self).copy_data(cr, uid, id, {'document_id': False}, context)

    def create_history(self, cr, uid, ids, vals, context=None):
        history_id = False
        history = self.pool.get('document.page.history')
        if vals.get('content'):
            res = {
                'content': vals.get('content', ''),
                'write_uid': uid,
                'document_id': ids[0],
                'summary':vals.get('edit_summary', '')
            }
            history_id = history.create(cr, uid, res)
        return history_id

    def create(self, cr, uid, vals, context=None):
        document_id = super(document_page2, self).create(cr, uid, vals, context)
        self.create_history(cr, uid, [document_id], vals, context)
        return document_id

    def write(self, cr, uid, ids, vals, context=None):
        result = super(document_page2, self).write(cr, uid, ids, vals, context)
        self.create_history(cr, uid, ids, vals, context)
        return result


class document_page_history(osv.osv):
    _name = "document.page.history"
    _description = "Document Page History"
    _rec_name = "summary"
    _order = 'id DESC'

    _columns = {
          'document_id': fields.many2one('document.page', 'Document Page', select=True)
          'summary': fields.char('Summary', size=256, select=True),
          'content': fields.text("Content"),
          'create_date': fields.datetime("Date", select=True),
          'write_uid': fields.many2one('res.users', "Modify By", select=True),
    }

    _defaults = {
        'write_uid': lambda obj, cr, uid, context: uid,
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
            raise osv.except_osv(_('Warning !'), _('There are no changes in revisions'))
        diff = difflib.HtmlDiff()
        return diff.make_file(line1, line2, "Revision-%s" % (v1), "Revision-%s" % (v2), context=False)


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
