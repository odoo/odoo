# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from operator import itemgetter
from textwrap import dedent

from openerp import tools, SUPERUSER_ID
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
        res = super(board_board, self).fields_view_get(cr, user, view_id=view_id, view_type=view_type,
                                                       context=context, toolbar=toolbar, submenu=submenu)

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
