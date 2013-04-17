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

from openerp.tools.translate import _
from openerp.osv import osv

class Invoice(osv.osv):
    _inherit = 'account.invoice'

    # Forbid to cancel an invoice if the related move lines have already been
    # used in a payment order. The risk is that importing the payment line
    # in the bank statement will result in a crash cause no more move will
    # be found in the payment line
    def action_cancel(self, cr, uid, ids, context=None):
        payment_line_obj = self.pool.get('payment.line')
        for inv in self.browse(cr, uid, ids, context=context):
            pl_line_ids = []
            if inv.move_id and inv.move_id.line_id:
                inv_mv_lines = [x.id for x in inv.move_id.line_id]
                pl_line_ids = payment_line_obj.search(cr, uid, [('move_line_id','in',inv_mv_lines)], context=context)
            if pl_line_ids:
                pay_line = payment_line_obj.browse(cr, uid, pl_line_ids, context=context)
                payment_order_name = ','.join(map(lambda x: x.order_id.reference, pay_line))
                raise osv.except_osv(_('Error!'), _("You cannot cancel an invoice which has already been imported in a payment order. Remove it from the following payment order : %s."%(payment_order_name)))
        return super(Invoice, self).action_cancel(cr, uid, ids, context=context)


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
