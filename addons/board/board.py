# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
#    Copyright (C) 2010-2012 OpenERP s.a. (<http://openerp.com>).
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

from operator import itemgetter
from textwrap import dedent

from openerp import tools
from openerp.osv import fields, osv

class board_board(osv.osv):
    _name = 'board.board'
    _description = "Board"
    _auto = False
    _columns = {}

    @tools.cache()
    def list(self, cr, uid, context=None):
        Actions = self.pool.get('ir.actions.act_window')
        Menus = self.pool.get('ir.ui.menu')
        IrValues = self.pool.get('ir.values')

        act_ids = Actions.search(cr, uid, [('res_model', '=', self._name)], context=context)
        refs = ['%s,%s' % (Actions._name, act_id) for act_id in act_ids]

        # cannot search "action" field on menu (non stored function field without search_fnct)
        irv_ids = IrValues.search(cr, uid, [
            ('model', '=', 'ir.ui.menu'),
            ('key', '=', 'action'),
            ('key2', '=', 'tree_but_open'),
            ('value', 'in', refs),
        ], context=context)
        menu_ids = map(itemgetter('res_id'), IrValues.read(cr, uid, irv_ids, ['res_id'], context=context))
        menu_names = Menus.name_get(cr, uid, menu_ids, context=context)
        return [dict(id=m[0], name=m[1]) for m in menu_names]

    def _clear_list_cache(self):
        self.list.clear_cache(self)

    def create(self, cr, user, vals, context=None):
        return 0

    def fields_view_get(self, cr, user, view_id=None, view_type='form', context=None, toolbar=False, submenu=False):
        """
        Overrides orm field_view_get.
        @return: Dictionary of Fields, arch and toolbar.
        """

        res = {}
        res = super(board_board, self).fields_view_get(cr, user, view_id, view_type,
                                                       context, toolbar=toolbar, submenu=submenu)

        CustView = self.pool.get('ir.ui.view.custom')
        vids = CustView.search(cr, user, [('user_id', '=', user), ('ref_id', '=', view_id)], context=context)
        if vids:
            view_id = vids[0]
            arch = CustView.browse(cr, user, view_id, context=context)
            res['custom_view_id'] = view_id
            res['arch'] = arch.arch
        res['arch'] = self._arch_preprocessing(cr, user, res['arch'], context=context)
        res['toolbar'] = {'print': [], 'action': [], 'relate': []}
        return res

    def _arch_preprocessing(self, cr, user, arch, context=None):
        from lxml import etree
        def remove_unauthorized_children(node):
            for child in node.iterchildren():
                if child.tag == 'action' and child.get('invisible'):
                    node.remove(child)
                else:
                    child = remove_unauthorized_children(child)
            return node

        def encode(s):
            if isinstance(s, unicode):
                return s.encode('utf8')
            return s

        archnode = etree.fromstring(encode(arch))
        return etree.tostring(remove_unauthorized_children(archnode), pretty_print=True)


class board_create(osv.osv_memory):

    def board_create(self, cr, uid, ids, context=None):
        assert len(ids) == 1
        this = self.browse(cr, uid, ids[0], context=context)

        view_arch = dedent("""<?xml version="1.0"?>
            <form string="%s" version="7.0">
            <board style="2-1">
                <column/>
                <column/>
            </board>
            </form>
        """.strip() % (this.name,))

        view_id = self.pool.get('ir.ui.view').create(cr, uid, {
            'name': this.name,
            'model': 'board.board',
            'priority': 16,
            'type': 'form',
            'arch': view_arch,
        }, context=context)

        action_id = self.pool.get('ir.actions.act_window').create(cr, uid, {
            'name': this.name,
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'board.board',
            'usage': 'menu',
            'view_id': view_id,
            'help': dedent('''<div class="oe_empty_custom_dashboard">
              <p>
                <b>This dashboard is empty.</b>
              </p><p>
                To add the first report into this dashboard, go to any
                menu, switch to list or graph view, and click <i>'Add to
                Dashboard'</i> in the extended search options.
              </p><p>
                You can filter and group data before inserting into the
                dashboard using the search options.
              </p>
          </div>
            ''')
        }, context=context)

        menu_id = self.pool.get('ir.ui.menu').create(cr, uid, {
            'name': this.name,
            'parent_id': this.menu_parent_id.id,
            'action': 'ir.actions.act_window,%s' % (action_id,)
        }, context=context)

        self.pool.get('board.board')._clear_list_cache()

        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
            'params': {
                'menu_id': menu_id
            },
        }

    def _default_menu_parent_id(self, cr, uid, context=None):
        _, menu_id = self.pool.get('ir.model.data').get_object_reference(cr, uid, 'base', 'menu_reporting_dashboard')
        return menu_id

    _name = "board.create"
    _description = "Board Creation"

    _columns = {
        'name': fields.char('Board Name', size=64, required=True),
        'menu_parent_id': fields.many2one('ir.ui.menu', 'Parent Menu', required=True),
    }

    _defaults = {
        'menu_parent_id': _default_menu_parent_id,
    }

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
