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
    """ document.page """
    _name = "document.page"

document_page()

class document_page_type(osv.osv):
    """ document page type """

    _name = "document.page.type"
    _description = "Document page type"
    _order = 'name'

    _columns = {
       'name':fields.char('Document Page Type', size=256, select=True, required=True),
       'page_ids':fields.one2many('document.page', 'parent_id', 'Pages'),
       'notes':fields.text("Description"),
       'create_date':fields.datetime("Created Date", select=True),
       'content_template': fields.text('Document Page Template'),
       'method':fields.selection([('list', 'List'), ('page', 'Home Page'), \
                                   ('tree', 'Tree')], 'Display Method', help="Define the default behaviour of the menu created on this group"),
       'home':fields.many2one('document.page', 'Home Page', help="Required to select home page if display method is Home Page"),
       'menu_id': fields.many2one('ir.ui.menu', "Menu", readonly=True),
    }

    _defaults = {
        'method': lambda *a: 'page',
    }

    def open_document_page(self, cr, uid, ids, context=None):

        """ Opens document Page of Group
        @param cr: the current row, from the database cursor,
        @param uid: the current user’s ID for security checks,
        @param ids: List of open document group’s IDs
        @return: dictionay of open Document window on give group id
        """
        if type(ids) in (int,long,):
            ids = [ids]
        group_id = False
        if ids:
            group_id = ids[0]
        if not group_id:
            return {}
        value = {
            'name': 'Document Page',
            'view_type': 'form',
            'view_mode': 'form,tree',
            'res_model': 'document.page',
            'view_id': False,
            'type': 'ir.actions.act_window',
            'nodestroy': True,
        }
        group = self.browse(cr, uid, group_id, context=context)
        value['domain'] = "[('parent_id','=',%d)]" % (group.id)
        if group.method == 'page':
            value['res_id'] = group.home.id
        elif group.method == 'list':
            value['view_type'] = 'form'
            value['view_mode'] = 'tree,form'
        elif group.method == 'tree':
            view_id = self.pool.get('ir.ui.view').search(cr, uid, [('name', '=', 'document.page.tree.children')])
            value['view_id'] = view_id
            value['domain'] = [('parent_id', '=', group.id)]
            value['view_type'] = 'tree'
            value['view_mode'] = 'tree'

        return value
document_page_type()


class document_page2(osv.osv):
    """ Document Page """

    _inherit = "document.page"
    _description = "Document Page"
    _order = 'create_date desc'
    
    _columns = {
        'name': fields.char('Title', size=256, select=True, required=True),
        'write_uid': fields.many2one('res.users', "Last Contributor", select=True),
        'content': fields.text("Content"),
        'index': fields.char('Index', size=256),
        'create_uid': fields.many2one('res.users', 'Author', select=True, readonly=True),
        'create_date': fields.datetime("Created on", select=True, readonly=True),
        'content_template': fields.text('Document Template'),
        'write_date': fields.datetime("Modification Date", select=True, readonly=True),
        'tags': fields.char('Keywords', size=1024, select=True),
        'history_ids': fields.one2many('document.page.history', 'document_id', 'History Lines'),
        'minor_edit': fields.boolean('Minor edit', select=True),
        'edit_summary': fields.char('Summary', size=256),
        'type':fields.selection([('normal','Content Page'),  ('index','Index Page')], 'Type', help="Define the type of the document"), 
        'review': fields.boolean('Needs Review', select=True,
            help="Indicates that this page should be reviewed, raising the attention of other contributors"),
        'parent_id': fields.many2one('document.page.type', 'Parent Page', select=1 , ondelete='set null', help="Allows you to link with the topic"),
        'child_ids': fields.one2many('document.page', 'parent_id', 'Child Pages'),
    }
    _defaults = {
        'type':'normal',
        'review': True,
        'minor_edit': True,
        'index' : 1,
    }

    

    def onchange_parent_id(self, cr, uid, ids, parent_id, content, context=None):

        """ @param cr: the current row, from the database cursor,
            @param uid: the current user’s ID for security checks,
            @param ids: List of document page’s IDs
            @return: dictionay of open document page on give page section  """

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

        """ @param cr: the current row, from the database cursor,
            @param uid: the current user’s ID for security checks,
            @param id: Give document page's ID """

        return super(document_page2, self).copy_data(cr, uid, id, {'document_id': False}, context)

    def create_history(self, cr, uid, ids, vals, context=None):
        history_id = False
        history = self.pool.get('document.page.history')
        if vals.get('content'):
            res = {
                'minor_edit': vals.get('minor_edit', True),
                'content': vals.get('content', ''),
                'write_uid': uid,
                'document_id': ids[0],
                'summary':vals.get('edit_summary', '')
            }
            history_id = history.create(cr, uid, res)
        return history_id

    def create(self, cr, uid, vals, context=None):

        """ @param cr: the current row, from the database cursor,
            @param uid: the current user’s ID for security checks, """
        document_id = super(document_page2, self).create(cr, uid,
                             vals, context)
        self.create_history(cr, uid, [document_id], vals, context)
        return document_id

    def write(self, cr, uid, ids, vals, context=None):

        """ @param cr: the current row, from the database cursor,
            @param uid: the current user’s ID for security checks, """
        result = super(document_page2, self).write(cr, uid, ids, vals, context)
        self.create_history(cr, uid, ids, vals, context)
        return result

document_page2()


class document_page_history(osv.osv):
    """ Document Page History """

    _name = "document.page.history"
    _description = "Document Page History"
    _rec_name = "summary"
    _order = 'id DESC'

    _columns = {
          'create_date': fields.datetime("Date", select=True),
          'content': fields.text("Content"),
          'minor_edit': fields.boolean('This is a major edit ?', select=True),
          'summary': fields.char('Summary', size=256, select=True),
          'write_uid': fields.many2one('res.users', "Modify By", select=True),
          'document_id': fields.many2one('document.page', 'Document Page', select=True)
    }

    _defaults = {
        'write_uid': lambda obj, cr, uid, context: uid,
    }

    def getDiff(self, cr, uid, v1, v2, context=None):

        """ @param cr: the current row, from the database cursor,
            @param uid: the current user’s ID for security checks, """

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

document_page_history()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
