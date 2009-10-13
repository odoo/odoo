# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution	
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>). All Rights Reserved
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

