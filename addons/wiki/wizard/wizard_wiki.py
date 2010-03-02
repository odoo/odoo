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
from service import web_services
import time
import wizard
import pooler


class wizard_create_menu(osv.osv_memory):
    _name = "wiki.wizard.create.menu"
    _description="Wiki.Wizard Create Menu"
    _columns={
        'menu_name':fields.char('Menu Name', size=256, select=True, required=True), 
        'menu_parent_id': fields.many2one('ir.ui.menu', 'Parent Menu', required=True), 
        'page': fields.many2one('wiki.wiki', 'Group Home Page'), 
    }

    def wiki_menu_create(self, cr, uid, ids, context):
        group = self.pool.get('wiki.groups').browse(cr, uid, ids)[0]
        menu = self.pool.get('wiki.wizard.create.menu').browse(cr, uid, ids)[0]
        action_id = self.pool.get('').search(cr, uid, [('wiz_name', '=', 'wiki.wiki.page.open')])

        menu_id = self.pool.get('ir.ui.menu').create(cr, uid, {
        'name':menu.menu_name, 
        'parent_id':menu.menu_parent_id.id, 
        'icon': 'STOCK_DIALOG_QUESTION', 
        'action': 'ir.actions.wizard,'+str(action_id[0])
        }, context)

        home = menu.page.id
        group_id = menu.id
        res = {
        'home':home, 
    }
        self.pool.get('wiki.groups').write(cr, uid, ids, res)
        self.pool.get('wiki.groups.link').create(cr, uid, {'group_id':group_id, 'action_id':menu_id})

        return {}


wizard_create_menu()

class wiz_open_help(osv.osv_memory):
    _name = "wiki.wiz.open.help"
    _description="Wiki Open Help"
    _columns={
        'name':fields.char('Basic Wiki Editing', size=256, select=True, required=False), 

    }
    def _open_wiki_page(self, cr, uid, ids, context):
        pages = self.pool.get('wiki.wiki').search(cr, uid, [('name', '=', 'Basic Wiki Editing')])

        value = {
            'view_id': False, 
            'res_id': pages[0], 
        }

        return value

wiz_open_help()

class wiz_open_page(osv.osv_memory):
    _name = "wiki.wiz.open.page"
    _description="wiz open page"
    _columns={
        'name':fields.char('Wiki Page', size=256, select=True, required=False), 

    }
    def _open_wiki_page(self, cr, uid, ids, context):
        group = self.pool.get('wiki.groups').browse(cr, uid, ids)[0]
        openpage = self.pool.get('wiki.wiz.open.page').browse(cr, uid, ids)[0]

        value = {
            'context': "{'group_id':%d, 'section':%s}" % (group.id, group.section), 
            'domain': "[('group_id','=',%d)]" % (group.id), 
            'type': 'ir.actions.act_window', 
        }
        if group.method == 'page':
            value['res_id'] = group.home.id
        elif group.method == 'list':
            value['view_type'] = 'form'
            value['view_mode'] = 'tree,form'
        elif group.method == 'tree':
            view_id = pool.get('ir.ui.view').search(cr, uid, [('name', '=', 'wiki.wiki.tree.childs')])
            value['view_id'] = view_id
            value['domain'] = [('group_id', '=', group.id), ('parent_id', '=', False)]
            value['view_type'] = 'tree'

        return value
wiz_open_page()

class showdiff(osv.osv_memory):
    _name = 'wizard.wiki.history.show_diff'

    def _get_diff(self, cr, uid, ctx):
        history = self.pool.get('wiki.wiki.history')
        ids = ctx.get('active_ids')
        diff = ""
        if len(ids) == 2:
            if ids[0] > ids[1]:
                diff = history.getDiff(cr, uid, ids[1], ids[0])
            else:
                diff = history.getDiff(cr, uid, ids[0], ids[1])

        elif len(ids) == 1:
            old = history.browse(cr, uid, ids[0])
            nids = history.search(cr, uid, [('wiki_id', '=', old.wiki_id.id)])
            nids.sort()
            diff = history.getDiff(cr, uid, ids[0], nids[-1])
        else:
            raise osv.except_osv(_('Warning'), _('You need to select minimum 1 or maximum 2 history revision!'))
        return diff

    _columns = {
        'diff': fields.text('Diff'), 
    }
    _defaults = {
        'diff': _get_diff
    }

showdiff()

