# -*- encoding: utf-8 -*-
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


#import time
#import netsvc
#from tools.misc import UpdateableStr
#import pooler
import wizard
import pooler
from tools.translate import _

def _check(self,cr,uid,data,*a):
    pool = pooler.get_pool(cr.dbname)
    order_lst = pool.get('pos.order').browse(cr,uid,data['ids'])
    for order in order_lst:
        if order.state_2 in ('to_verify'):
            raise wizard.except_wizard('Error!', 'Can not print the receipt because of discount and/or payment ')
    return data

class print_order_receipt(wizard.interface):
        states = {
          'init': {
              'actions': [_check],
              'result': {'type':'print', 'report':'pos.receipt', 'state':'end'}
          }
      }

print_order_receipt('ord.receipt')

