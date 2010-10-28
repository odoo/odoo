# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution	
#    Copyright (C) 2004-2008 Tiny SPRL (<http://tiny.be>). All Rights Reserved
#    $Id$
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from osv import fields, osv

class account_invoice(osv.osv):
    _inherit = "account.invoice"
    _columns = {
        # states={'open':[('readonly',False)]}
        'fiscalgr_print': fields.many2one('account.fiscalgr.print','Fiscal print', readonly=True, ),
        }
    def copy(self, cr, uid, id, default=None, context=None):
        if default is None:
            default = {}
        default = default.copy()
        default.update({'fiscalgr_print':None,})
        return super(account_invoice, self).copy(cr, uid, id, default, context)

    def action_cancel(self, cr, uid, ids, *args):
        #account_move_obj = self.pool.get('account.move')
        invoices = self.read(cr, uid, ids, ['fiscalgr_print'])
        for i in invoices:
            if i['fiscalgr_print']:
	    	raise osv.except_osv(_('Invalid action !'), _('Cannot cancel invoice(s) which are already printed !'))
        return super(account_invoice,self).action_cancel(cr,uid,ids,args)

account_invoice()
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

