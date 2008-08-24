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

from osv import fields
from osv import osv
import time
import netsvc

import ir
from mx import DateTime
import pooler
from tools import config

class purchase_order_line(osv.osv):
    _name='purchase.order.line'
    _inherit='purchase.order.line'
    _columns = {
        'analytics_id':fields.many2one('account.analytic.plan.instance','Analytic Distribution'),
    }

purchase_order_line()

class purchase_order(osv.osv):
    _name='purchase.order'
    _inherit='purchase.order'

    def inv_line_create(self,a,ol):
        res=super(purchase_order,self).inv_line_create(a,ol)
        res[2]['analytics_id']=ol.analytics_id.id
        return res

purchase_order()
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

