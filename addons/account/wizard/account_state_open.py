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

from openerp import netsvc
from openerp.tools.translate import _

class account_state_open(osv.osv_memory):
    _name = 'account.state.open'
    _description = 'Account State Open'

    def change_inv_state(self, cr, uid, ids, context=None):
        obj_invoice = self.pool.get('account.invoice')
        if context is None:
            context = {}
        if 'active_ids' in context:
            data_inv = obj_invoice.browse(cr, uid, context['active_ids'][0], context=context)
            if data_inv.reconciled:
                raise osv.except_osv(_('Warning!'), _('Invoice is already reconciled.'))
            wf_service = netsvc.LocalService("workflow")
            wf_service.trg_validate(uid, 'account.invoice', context['active_ids'][0], 'open_test', cr)
        return {'type': 'ir.actions.act_window_close'}

account_state_open()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
