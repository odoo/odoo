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

class wiki_wiki(osv.osv):
    """ wiki """
    _name = "wiki.wiki"

wiki_wiki()

class wiki_group(osv.osv):
    """ Wiki Groups """

    _name = "wiki.groups"
    _description = "Wiki Groups"
    _order = 'name'

    _columns = {
       'name':fields.char('Wiki Group', size=256, select=True, required=True),
       'page_ids':fields.one2many('wiki.wiki', 'group_id', 'Pages'),
       'notes':fields.text("Description"),
       'create_date':fields.datetime("Created Date", select=True),
       'template': fields.text('Wiki Template'),
       'section': fields.boolean("Make Section ?"),
       'method':fields.selection([('list', 'List'), ('page', 'Home Page'), \
                                   ('tree', 'Tree')], 'Display Method', help="Define the default behaviour of the menu created on this group"),
       'home':fields.many2one('wiki.wiki', 'Home Page', help="Required to select home page if display method is Home Page"),
       'menu_id': fields.many2one('ir.ui.menu', "Menu", readonly=True),
    }

    _defaults = {
        'method': lambda *a: 'page',
    }

    def open_wiki_page(self, cr, uid, ids, context=None):

        """ Opens Wiki Page of Group
        @param cr: the current row, from the database cursor,
        @param uid: the current user’s ID for security checks,
        @param ids: List of open wiki group’s IDs
        @return: dictionay of open wiki window on give group id
        """
        if type(ids) in (int,long,):
            ids = [ids]
        group_id = False
        if ids:
            group_id = ids[0]
        if not group_id:
            return {}
        value = {
            'name': 'Wiki Page',
            'view_type': 'form',
            'view_mode': 'form,tree',
            'res_model': 'wiki.wiki',
            'view_id': False,
            'type': 'ir.actions.act_window',
            'nodestroy': True,
        }
        group = self.browse(cr, uid, group_id, context=context)
        value['domain'] = "[('group_id','=',%d)]" % (group.id)
        if group.method == 'page':
            value['res_id'] = group.home.id
        elif group.method == 'list':
            value['view_type'] = 'form'
            value['view_mode'] = 'tree,form'
        elif group.method == 'tree':
            view_id = self.pool.get('ir.ui.view').search(cr, uid, [('name', '=', 'wiki.wiki.tree.children')])
            value['view_id'] = view_id
            value['domain'] = [('group_id', '=', group.id), ('parent_id', '=', False)]
            value['view_type'] = 'tree'

        return value
wiki_group()


class wiki_wiki2(osv.osv):
    """ Wiki Page """

    _inherit = "wiki.wiki"
    _description = "Wiki Page"
    _order = 'section,create_date desc'

    _columns = {
        'name': fields.char('Title', size=256, select=True, required=True),
        'write_uid': fields.many2one('res.users', "Last Contributor", select=True),
        'text_area': fields.text("Content"),
        'create_uid': fields.many2one('res.users', 'Author', select=True, readonly=True),
        'create_date': fields.datetime("Created on", select=True, readonly=True),
        'write_date': fields.datetime("Modification Date", select=True, readonly=True),
        'tags': fields.char('Keywords', size=1024, select=True),
        'history_id': fields.one2many('wiki.wiki.history', 'wiki_id', 'History Lines'),
        'minor_edit': fields.boolean('Minor edit', select=True),
        'summary': fields.char('Summary', size=256),
        'section': fields.char('Section', size=32, help="Use page section code like 1.2.1", select=True),
        'group_id': fields.many2one('wiki.groups', 'Wiki Group', select=1, ondelete='set null',
            help="Topic, also called Wiki Group"),
        'toc': fields.boolean('Table of Contents',
            help="Indicates that this pages have a table of contents or not"),
        'review': fields.boolean('Needs Review', select=True,
            help="Indicates that this page should be reviewed, raising the attention of other contributors"),
        'parent_id': fields.many2one('wiki.wiki', 'Parent Page', help="Allows you to link with the other page with in the current topic"),
        'child_ids': fields.one2many('wiki.wiki', 'parent_id', 'Child Pages'),
    }
    _defaults = {
        'toc': lambda *a: True,
        'review': lambda *a: True,
        'minor_edit': lambda *a: True,
    }

    def onchange_group_id(self, cr, uid, ids, group_id, content, context=None):

        """ @param cr: the current row, from the database cursor,
            @param uid: the current user’s ID for security checks,
            @param ids: List of wiki page’s IDs
            @return: dictionay of open wiki page on give page section  """

        if (not group_id) or content:
            return {}
        grp = self.pool.get('wiki.groups').browse(cr, uid, group_id, context=context)
        section = '0'
        for page in grp.page_ids:
            if page.section: section = page.section
        s = section.split('.')
        template = grp.template
        try:
            s[-1] = str(int(s[-1])+1)
        except:
            pass
        section = '.'.join(s)
        return {
            'value':{
                'text_area': template,
                'section': section
            }
        }

    def copy_data(self, cr, uid, id, default=None, context=None):

        """ @param cr: the current row, from the database cursor,
            @param uid: the current user’s ID for security checks,
            @param id: Give wiki page's ID """

        return super(wiki_wiki2, self).copy_data(cr, uid, id, {'wiki_id': False}, context)

    def create_history(self, cr, uid, ids, vals, context=None):
        history_id = False
        history = self.pool.get('wiki.wiki.history')
        if vals.get('text_area'):
            res = {
                'minor_edit': vals.get('minor_edit', True),
                'text_area': vals.get('text_area', ''),
                'write_uid': uid,
                'wiki_id': ids[0],
                'summary':vals.get('summary', '')
            }
            history_id = history.create(cr, uid, res)
        return history_id

    def create(self, cr, uid, vals, context=None):

        """ @param cr: the current row, from the database cursor,
            @param uid: the current user’s ID for security checks, """
        wiki_id = super(wiki_wiki2, self).create(cr, uid,
                             vals, context)
        self.create_history(cr, uid, [wiki_id], vals, context)
        return wiki_id

    def write(self, cr, uid, ids, vals, context=None):

        """ @param cr: the current row, from the database cursor,
            @param uid: the current user’s ID for security checks, """
        result = super(wiki_wiki2, self).write(cr, uid, ids, vals, context)
        self.create_history(cr, uid, ids, vals, context)
        return result

wiki_wiki2()


class wiki_history(osv.osv):
    """ Wiki History """

    _name = "wiki.wiki.history"
    _description = "Wiki History"
    _rec_name = "summary"
    _order = 'id DESC'

    _columns = {
          'create_date': fields.datetime("Date", select=True),
          'text_area': fields.text("Text area"),
          'minor_edit': fields.boolean('This is a major edit ?', select=True),
          'summary': fields.char('Summary', size=256, select=True),
          'write_uid': fields.many2one('res.users', "Modify By", select=True),
          'wiki_id': fields.many2one('wiki.wiki', 'Wiki Id', select=True)
    }

    _defaults = {
        'write_uid': lambda obj, cr, uid, context: uid,
    }

    def getDiff(self, cr, uid, v1, v2, context=None):

        """ @param cr: the current row, from the database cursor,
            @param uid: the current user’s ID for security checks, """

        history_pool = self.pool.get('wiki.wiki.history')
        text1 = history_pool.read(cr, uid, [v1], ['text_area'])[0]['text_area']
        text2 = history_pool.read(cr, uid, [v2], ['text_area'])[0]['text_area']
        line1 = line2 = ''
        if text1:
            line1 = tools.ustr(text1.splitlines(1))
        if text2:
            line2=tools.ustr(text2.splitlines(1))
        if (not line1 and not line2) or (line1 == line2):
            raise osv.except_osv(_('Warning !'), _('There are no changes in revisions'))
        diff = difflib.HtmlDiff()
        return diff.make_file(line1, line2, "Revision-%s" % (v1), "Revision-%s" % (v2), context=False)

wiki_history()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
