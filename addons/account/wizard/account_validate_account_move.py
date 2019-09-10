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
from openerp.osv import fields, osv
from openerp.tools.translate import _

class validate_account_move(osv.osv_memory):
    _name = "validate.account.move"
    _description = "Validate Account Move"
    _columns = {
        'journal_ids': fields.many2many('account.journal', 'wizard_validate_account_move_journal', 'wizard_id', 'journal_id', 'Journal', required=True),
        'period_ids': fields.many2many('account.period', 'wizard_validate_account_move_period', 'wizard_id', 'period_id', 'Period', required=True, domain=[('state','<>','done')]),
    }

    def validate_move(self, cr, uid, ids, context=None):
        obj_move = self.pool.get('account.move')
        if context is None:
            context = {}
        data = self.read(cr, uid, ids[0], context=context)
        ids_move = obj_move.search(cr, uid, [('state','=','draft'),('journal_id','in',tuple(data['journal_ids'])),('period_id','in',tuple(data['period_ids']))], order='date')
        if not ids_move:
            raise osv.except_osv(_('Warning!'), _('Specified journals do not have any account move entries in draft state for the specified periods.'))
        obj_move.button_validate(cr, uid, ids_move, context=context)
        return {'type': 'ir.actions.act_window_close'}


class validate_account_move_lines(osv.osv_memory):
    _name = "validate.account.move.lines"
    _description = "Validate Account Move Lines"

    def validate_move_lines(self, cr, uid, ids, context=None):
        obj_move_line = self.pool.get('account.move.line')
        obj_move = self.pool.get('account.move')
        move_ids = []
        if context is None:
            context = {}
        data_line = obj_move_line.browse(cr, uid, context['active_ids'], context)
        for line in data_line:
            if line.move_id.state=='draft':
                move_ids.append(line.move_id.id)
        move_ids = list(set(move_ids))
        if not move_ids:
            raise osv.except_osv(_('Warning!'), _('Selected Entry Lines does not have any account move entries in draft state.'))
        obj_move.button_validate(cr, uid, move_ids, context)
        return {'type': 'ir.actions.act_window_close'}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

