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

class account_invoice_confirm(osv.osv_memory):
    """
    This wizard will confirm the all the selected draft invoices
    """

    _name = "account.invoice.confirm"
    _description = "Confirm the selected invoices"

    def invoice_confirm(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        account_invoice_obj = self.pool['account.invoice']
        data_inv = account_invoice_obj.read(cr, uid, context['active_ids'], ['state'], context=context)
        for record in data_inv:
            if record['state'] not in ('draft','proforma','proforma2'):
                raise osv.except_osv(_('Warning!'), _("Selected invoice(s) cannot be confirmed as they are not in 'Draft' or 'Pro-Forma' state."))
            account_invoice_obj.signal_invoice_open(cr, uid, [ record['id'] ])
            
        return {'type': 'ir.actions.act_window_close'}


class account_invoice_cancel(osv.osv_memory):
    """
    This wizard will cancel the all the selected invoices.
    If in the journal, the option allow cancelling entry is not selected then it will give warning message.
    """

    _name = "account.invoice.cancel"
    _description = "Cancel the Selected Invoices"

    def invoice_cancel(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        account_invoice_obj = self.pool['account.invoice']
        data_inv = account_invoice_obj.read(cr, uid, context['active_ids'], ['state'], context=context)
        for record in data_inv:
            if record['state'] in ('cancel','paid'):
                raise osv.except_osv(_('Warning!'), _("Selected invoice(s) cannot be cancelled as they are already in 'Cancelled' or 'Done' state."))
            account_invoice_obj.signal_invoice_cancel(cr , uid, [record['id']])
        return {'type': 'ir.actions.act_window_close'}


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
