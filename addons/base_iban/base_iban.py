# -*- encoding: utf-8 -*-
##############################################################################
#
# Copyright (c) 2004-2008 TINY SPRL. (http://tiny.be) All Rights Reserved.
#
# $Id$
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

import netsvc
from osv import fields, osv

class res_partner_bank(osv.osv):
    _inherit = "res.partner.bank"
    _columns = {
        'iban': fields.char('IBAN', size=34, readonly=True, help="International Bank Account Number"),
    }

    def name_get(self, cr, uid, ids, context=None):
        res = []
        to_check_ids = []
        for id in self.browse(cr, uid, ids):
            if id.state=='iban':
                res.append((id.id,id.iban))
            else:
                to_check_ids.append(id.id)
        res += super(res_partner_bank, self).name_get(cr, uid, to_check_ids, context)
        return res

    def search(self, cr, uid, args, offset=0, limit=None, order=None,
            context=None, count=False):
        res = super(res_partner_bank,self).search(cr, uid, args, offset, limit,
                order, context=context, count=count)
        if filter(lambda x:x[0]=='acc_number' ,args):
            iban_value = filter(lambda x:x[0]=='acc_number' ,args)[0][2]
            args1 =  filter(lambda x:x[0]!='acc_number' ,args)
            args1 += [('iban','ilike',iban_value)]
            res += super(res_partner_bank,self).search(cr, uid, args1, offset, limit,
                order, context=context, count=count)
        return res

res_partner_bank()


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

