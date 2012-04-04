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
import time
import tools

class board_board(osv.osv):
    """
    Board
    """
    _name = 'board.board'
    _description = "Board"

    def create_view(self, cr, uid, ids, context=None):
        """
        Create  view
        @param cr: the current row, from the database cursor,
        @param uid: the current user’s ID for security checks,
        @param ids: List of Board's IDs
        @return: arch of xml view.
        """
        board = self.pool.get('board.board').browse(cr, uid, ids, context=context)
        left = []
        right = []
        #start Loop
        for line in board.line_ids:
            linestr = '<action string="%s" name="%d"' % (line.name, line.action_id.id)
            linestr += '/>'
            if line.position == 'left':
                left.append(linestr)
            else:
                right.append(linestr)
        #End Loop
        arch = """<?xml version="1.0"?>
            <form string="My Board">
            <board style="1-1">
                <column>
                    %s
                </column>
                <column>
                    %s
                </column>
            </board>
            </form>""" % ('\n'.join(left), '\n'.join(right))

        return arch

    def write(self, cr, uid, ids, vals, context=None):

        """
        Writes values in one or several fields.
        @param cr: the current row, from the database cursor,
        @param uid: the current user’s ID for security checks,
        @param ids: List of Board's IDs
        @param vals: dictionary with values to update.
                     dictionary must be with the form: {‘name_of_the_field’: value, ...}.
        @return: True
        """
        result = super(board_board, self).write(cr, uid, ids, vals, context=context)

        board = self.pool.get('board.board').browse(cr, uid, ids[0], context=context)
        view = self.create_view(cr, uid, ids[0], context=context)
        id = board.view_id.id
        cr.execute("update ir_ui_view set arch=%s where id=%s", (view, id))
        return result

    def create(self, cr, user, vals, context=None):
        """
        create new record.
        @param cr: the current row, from the database cursor,
        @param uid: the current user’s ID for security checks,
        @param vals: dictionary of values for every field.
                      dictionary must use this form: {‘name_of_the_field’: value, ...}
        @return: id of new created record of board.board.
        """


        if not 'name' in vals:
            return False
        id = super(board_board, self).create(cr, user, vals, context=context)
        view_id = self.pool.get('ir.ui.view').create(cr, user, {
            'name': vals['name'],
            'model': 'board.board',
            'priority': 16,
            'type': 'form',
            'arch': self.create_view(cr, user, id, context=context),
        })

        super(board_board, self).write(cr, user, [id], {'view_id': view_id}, context)

        return id

    def fields_view_get(self, cr, user, view_id=None, view_type='form', context=None,\
                         toolbar=False, submenu=False):
        """
        Overrides orm field_view_get.
        @return: Dictionary of Fields, arch and toolbar.
        """

        res = {}
        res = super(board_board, self).fields_view_get(cr, user, view_id, view_type,\
                                 context, toolbar=toolbar, submenu=submenu)

        vids = self.pool.get('ir.ui.view.custom').search(cr, user,\
                     [('user_id', '=', user), ('ref_id' ,'=', view_id)])
        if vids:
            view_id = vids[0]
            arch = self.pool.get('ir.ui.view.custom').browse(cr, user, view_id, context=context)
            res['custom_view_id'] = view_id
            res['arch'] = arch.arch
        res['arch'] = self._arch_preprocessing(cr, user, res['arch'], context=context)
        res['toolbar'] = {'print': [], 'action': [], 'relate': []}
        return res


    def _arch_preprocessing(self, cr, user, arch, context=None):
        from lxml import etree
        def remove_unauthorized_children(node):
            for child in node.iterchildren():
                if child.tag=='action' and child.get('invisible'):
                    node.remove(child)
                else:
                    child=remove_unauthorized_children(child)
            return node

        def encode(s):
            if isinstance(s, unicode):
                return s.encode('utf8')
            return s

        archnode = etree.fromstring(encode(arch))
        return etree.tostring(remove_unauthorized_children(archnode),pretty_print=True)




    _columns = {
        'name': fields.char('Dashboard', size=64, required=True),
        'view_id': fields.many2one('ir.ui.view', 'Board View'),
        'line_ids': fields.one2many('board.board.line', 'board_id', 'Action Views')
    }

    # the following lines added to let the button on dashboard work.
    _defaults = {
        'name':lambda *args:  'Dashboard'
    }

class board_line(osv.osv):
    """
    Board Line
    """
    _name = 'board.board.line'
    _description = "Board Line"
    _order = 'position,sequence'
    _columns = {
        'name': fields.char('Title', size=64, required=True),
        'sequence': fields.integer('Sequence', help="Gives the sequence order\
                         when displaying a list of board lines.", select=True),
        'height': fields.integer('Height'),
        'width': fields.integer('Width'),
        'board_id': fields.many2one('board.board', 'Dashboard', required=True, ondelete='cascade'),
        'action_id': fields.many2one('ir.actions.act_window', 'Action', required=True),
        'position': fields.selection([('left','Left'),
                                      ('right','Right')], 'Position', required=True, select=True)
    }
    _defaults = {
        'position': lambda *args: 'left'
    }

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
