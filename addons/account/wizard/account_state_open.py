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
from openerp.osv import osv

from openerp.tools.translate import _

class account_state_open(osv.osv_memory):
    _name = 'account.state.open'
    _description = 'Account State Open'

    def change_inv_state(self, cr, uid, ids, context=None):
        proxy = self.pool.get('account.invoice')
        if context is None:
            context = {}

        active_ids = context.get('active_ids')
        if isinstance(active_ids, list):
            invoice = proxy.browse(cr, uid, active_ids[0], context=context)
            if invoice.reconciled:
                raise osv.except_osv(_('Warning!'), _('Invoice is already reconciled.'))
            invoice.signal_workflow('open_test')
        return {'type': 'ir.actions.act_window_close'}


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
