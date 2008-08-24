# -*- encoding: utf-8 -*-
##############################################################################
#
# Copyright (c) 2004-2006 TINY SPRL. (http://tiny.be) All Rights Reserved.
#
# $Id: account.py 1005 2005-07-25 08:41:42Z nicoe $
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
import netsvc
from osv import fields, osv
import ir
from mx import DateTime
from tools import config

class sale_order_line(osv.osv):
    _name='sale.order.line'
    _inherit='sale.order.line'
    _columns = {
        'analytics_id':fields.many2one('account.analytic.plan.instance','Analytic Distribution'),
    }
    def invoice_line_create(self, cr, uid, ids, context={}):
        create_ids=super(sale_order_line,self).invoice_line_create(cr, uid, ids, context)
        i=0
        for line in self.browse(cr, uid, ids, context):
            self.pool.get('account.invoice.line').write(cr,uid,[create_ids[i]],{'analytics_id':line.analytics_id.id})
            i=i+1
        return create_ids
sale_order_line()
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

