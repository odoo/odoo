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
import netsvc

class account_invoice(osv.osv):
    _inherit = "account.invoice"
    _columns = {
        # states={'open':[('readonly',False)]}
        'fiscalgr_print': fields.many2one('account.fiscalgr.print','Fiscal print', readonly=True, ),
	'state': fields.selection([
            ('draft','Draft'),
            ('proforma','Pro-forma'),
            ('proforma2','Pro-forma'),
            ('open','Open'),
            ('paid','Done'),
            ('cancel','Canceled'),
	    ('printed','Printed'),
        ],'State', select=True, readonly=True),
	'property_fiscalgr_invoice_report': fields.property( 'ir.actions.report.xml', type='many2one',
		relation='ir.actions.report.xml', string="Fiscal report template", method=True,
		view_load=True, group_name="Reports"),
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
	
    def action_fiscalgr_print(self, cr, uid, ids, context, *args):
	fiscalgr_obj = self.pool.get('account.fiscalgr.print')
	logger = netsvc.Logger()
        invoices = self.read(cr, uid, ids, [])
	# First, iterate once to check if the invoices are valid for printing.
        for i in invoices:
	    if not i['number']:
		raise osv.except_osv(_('Cannot print!'), _('Cannot print invoice, because it is not numbered!'))
	    if i['state'] != 'open':
		raise osv.except_osv(_('Cannot print!'), _('Cannot print invoice \"%s\" which is not open.')%i['number'])
	    if (not i['type'] or (i['type'][0:3] != 'out')):
		raise osv.except_osv(_('Cannot print!'), _('Cannot print invoice \"%s\", it is not an outgoing one.')%i['number'])
	    if not i['property_fiscalgr_invoice_report']:
		raise osv.except_osv(_('Cannot print!'), _('Cannot locate report setting for fiscal printing!'))
            if i['fiscalgr_print']:
	    	raise osv.except_osv(_('Cannot print!'), _('Cannot print invoice \"%s\" which is already printed !')%i['number'])
	    #raise osv.except_osv(_('Invalid action !'), _('Cannot print such an invoice !'))
	
	#Then, iterate again, and issue those invoices for printing
	for i in invoices:
		if fiscalgr_obj.print_invoice(cr,uid,i,self._name,i['number'], i['property_fiscalgr_invoice_report'][0],context):
			self.write(cr,uid,i['id'],{'state':'printed'})
			logger.notifyChannel("fiscalgr", netsvc.LOG_INFO, 'printed invoice ref. %s'%i['number'])
       
	return True

account_invoice()
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

