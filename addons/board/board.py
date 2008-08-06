# -*- encoding: utf-8 -*-
##############################################################################
#
# Copyright (c) 2004-2008 TINY SPRL. (http://tiny.be) All Rights Reserved.
#
# $Id$
#
# WARNING: This program as such is intended to be used by professional
# programmers who take the whole responsability of assessing all potential
# consequences resulting from its eventual inadequacies and bugs
# End users who are looking for a ready-to-use solution with commercial
# garantees and support are strongly adviced to contract a Free Software
# Service Company
#
# This program is Free Software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.
#
##############################################################################

import time
from osv import fields,osv

class board_board(osv.osv):
    _name = 'board.board'
    
    def create_view(self, cr, uid, ids, context):
        
        board = self.pool.get('board.board').browse(cr, uid, ids, context)
        left = []
        right = []
        for line in board.line_ids:
            linestr = '<action string="%s" name="%d" colspan="4"' % (line.name, line.action_id.id)
            if line.height:
                linestr+=(' height="%d"' % (line.height,))
            if line.width:
                linestr+=(' width="%d"' % (line.width,))
            linestr += '/>'
            if line.position=='left':
                left.append(linestr)
            else:
                right.append(linestr)
        arch = """<?xml version="1.0"?>
            <form string="My Board">
            <hpaned>
                <child1>
                    %s
                </child1>
                <child2>
                    %s
                </child2>
            </hpaned>
            </form>""" % ('\n'.join(left), '\n'.join(right))
        
        return arch

    def write(self, cr, uid, ids, vals, context={}):
        result = super(board_board, self).write(cr, uid, ids, vals, context)
        cr.commit()
        
        board = self.pool.get('board.board').read(cr, uid, ids)[0]
        
        view = self.create_view(cr, uid, ids[0], context)
        id = board['view_id'][0]
        
        cr.execute("update ir_ui_view set arch='%s' where id=%d" % (view, id))
        cr.commit()
        
        #self.pool.get('ir.ui.view').write(cr, uid, [], view, {'tiny':'base'})
        
        return result
    
    def create(self, cr, user, vals, context=None):
        if not 'name' in vals:
            return False
        id = super(board_board, self).create(cr, user, vals, context)
        view_id = self.pool.get('ir.ui.view').create(cr, user, {
            'name': vals['name'],
            'model':'board.board',
            'priority':16,
            'type': 'form',
            'arch': self.create_view(cr, user, id, context),
        })
        self.pool.get('board.board').write(cr, user, [id], {'view_id':view_id})
        return id
    
    def fields_view_get(self, cr, user, view_id=None, view_type='form', context=None, toolbar=False):
        res = {}
        vids = self.pool.get('ir.ui.view').search(cr, user, [('user_id','=',user), ('ref_id','=',view_id)])
        if vids:
            view_id = vids[0]
        res = super(board_board, self).fields_view_get(cr, user, view_id, view_type, context, toolbar)
        res['toolbar'] = {'print':[],'action':[],'relate':[]}
        return res
    
    _columns = {
        'name': fields.char('Dashboard', size=64, required=True),
        'view_id': fields.many2one('ir.ui.view', 'Board View'),
        'line_ids': fields.one2many('board.board.line', 'board_id', 'Action Views')
    }
board_board()

class board_line(osv.osv):
    _name = 'board.board.line'
    _order = 'position,sequence'
    _columns = {
        'name': fields.char('Title', size=64, required=True),
        'sequence': fields.integer('Sequence'),
        'height': fields.integer('Height'),
        'width': fields.integer('Width'),
        'board_id': fields.many2one('board.board', 'Dashboard', required=True, ondelete='cascade'),
        'action_id': fields.many2one('ir.actions.act_window', 'Action', required=True),
        'position': fields.selection([('left','Left'),('right','Right')], 'Position', required=True)
    }
    _defaults = {
        'position': lambda *args: 'left'
    }
board_line()

class board_note_type(osv.osv):
    _name = 'board.note.type'
    _columns = {
        'name': fields.char('Note Type', size=64, required=True),
    }
board_note_type()

def _type_get(self, cr, uid, context={}):
    obj = self.pool.get('board.note.type')
    ids = obj.search(cr, uid, [])
    res = obj.read(cr, uid, ids, ['name'], context)
    res = [(r['name'], r['name']) for r in res]
    return res

class board_note(osv.osv):
    _name = 'board.note'
    _columns = {
        'name': fields.char('Subject', size=128, required=True),
        'note': fields.text('Note'),
        'user_id': fields.many2one('res.users', 'Author', size=64),
        'date': fields.date('Date', size=64, required=True),
        'type': fields.selection(_type_get, 'Note type', size=64),
    }
    _defaults = {
        'user_id': lambda object,cr,uid,context: uid,
        'date': lambda object,cr,uid,context: time.strftime('%Y-%m-%d'),
    }
board_note()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

