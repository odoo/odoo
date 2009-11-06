# -*- coding: utf-8 -*-
#  dat.py
#  l10n_ch
#
#  Created by Nicolas Bessi based on Credric Krier contribution
#
#  Copyright (c) 2009 CamptoCamp. All rights reserved.
##############################################################################
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
from osv import osv,fields

class account_dta(osv.osv):
    """class that implements bank DTA File format, 
    used to transfert bulk batch payment instruction to a bank"""
    _name = "account.dta"
    _description = "DTA History"
    _columns = {
        ### name of the file 
        'name': fields.binary('DTA file', readonly=True),
        ### list of dta line linked to the dta order
        'dta_line_ids': fields.one2many('account.dta.line','dta_id','DTA lines', readonly=True), 
        ## textual notes
        'note': fields.text('Creation log', readonly=True, 
            help="display the problem during dta generation"),
        ### bank how will execute DTA order
        'bank': fields.many2one('res.partner.bank','Bank', readonly=True,select=True,
            help="bank how will execute DTA order"),
        ### date of DTA order generation 
        'date': fields.date('Creation Date', readonly=True,select=True,
            help="date of DTA order generation"),
        ### user how generate the DTA order
        'user_id': fields.many2one('res.users','User', readonly=True, select=True),
    }
account_dta()

class account_dta_line(osv.osv):
    """Class that represent a DTA order line, 
    each lin corressponds to a payment instruction"""
    _name = "account.dta.line"
    _description = "DTA line"
    _columns = {
        ### name of the line 
        'name' : fields.many2one('account.invoice','Invoice', required=True, size=256),
        ### partner how will receive payments
        'partner_id' : fields.many2one('res.partner','Partner',
            help="Partenr to pay"),
        ### due date of the payment
        'due_date' : fields.date('Due date'),
        ### date of the supplier invoice to pay
        'invoice_date' : fields.date('Invoice date'),
        ### cash discount date
        'cashdisc_date' : fields.date('Cash Discount date'),
        ### amount effectively paied on this line 
        'amount_to_pay' : fields.float('Amount to pay', 
            help="amount effectively paid"),
        ### amount that was on the supplier invoice
        'amount_invoice': fields.float('Invoiced Amount',
            help="amount to pay base on the supplier invoice"),
        ### Cash discount amount 
        'amount_cashdisc': fields.float('Cash Discount Amount'),
        ### Linke to the main dta order
        'dta_id': fields.many2one('account.dta','Associated DTA', required=True, ondelete='cascade'),
        ### state of the invoice Drat, Cancel, Done
        'state' : fields.selection([('draft','Draft'),('cancel','Error'),('done','Paid')],'State')
    }
    _defaults = {
        'state' : lambda *a :'draft',
    }
account_dta_line()


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
