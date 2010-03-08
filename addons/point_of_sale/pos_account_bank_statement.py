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

from osv import osv, fields
import time
import netsvc


class account_bank_statement(osv.osv):
    _inherit = 'account.bank.statement'
    _columns = {
        'company_id':fields.many2one('res.company', 'Company', required=True),
    }
    _defaults = {
        'company_id': lambda self,cr,uid,c: self.pool.get('res.users').browse(cr, uid, uid, c).company_id.id,
    }
account_bank_statement()

class account_bank_statement_line(osv.osv):
    def _default_company(self, cr, uid, context={}):
        user = self.pool.get('res.users').browse(cr, uid, uid, context=context)
        if user.company_id:
            return user.company_id.id
        return self.pool.get('res.company').search(cr, uid, [('parent_id', '=', False)])[0]
    _inherit = 'account.bank.statement.line'
    _columns = {
        'company_id':fields.many2one('res.company', 'Company', required=True),
    }
    _defaults = {
        'company_id': lambda self,cr,uid,c: self.pool.get('res.users').browse(cr, uid, uid, c).company_id.id,
    }
account_bank_statement_line()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

