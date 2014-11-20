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


class account_restart_sequence(osv.osv_memory):
    """
        Restart Sequences
    """

    def _get_journal_ids(self, cr, uid, context=None):
        return self.pool.get('account.journal').search(cr, uid, [('restart_sequence', '=', 'True')])

    _name = "account.sequence.restart"
    _description = "Restart Sequences"
    _columns = {
        'journal_ids': fields.many2many('account.journal'),
    }

    _defaults = {
        'journal_ids': _get_journal_ids,
    }

    def restart_sequences(self, cr, uid, ids, context=None):
        for form in self.read(cr, uid, ids, context=context):
            if form['journal_ids']:
                self.pool.get('account.fiscalyear').restart_sequences(cr, uid, context['active_ids'], form['journal_ids'], context=context)

        return {'type': 'ir.actions.act_window_close'}


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
