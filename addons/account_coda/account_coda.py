# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>).
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

import time

from osv import osv,fields
from tools.translate import _

class account_coda(osv.osv):
    _name = "account.coda"
    _description = "coda for an Account"
    _columns = {
        'name': fields.binary('Coda file', readonly=True, help="Store the detail of bank statements"),
        'statement_ids': fields.one2many('account.bank.statement', 'coda_id', 'Generated Bank Statements', readonly=True),
        'note': fields.text('Import log', readonly=True),
        'journal_id': fields.many2one('account.journal', 'Journal', readonly=True, select=True, help="Bank Journal"),
        'date': fields.date('Date', readonly=True, select=True, help="Import Date"),
        'user_id': fields.many2one('res.users', 'User', readonly=True, select=True),
        'company_id': fields.many2one('res.company', 'Company', readonly=True)
    }
    _defaults = {
        'date': lambda *a: time.strftime('%Y-%m-%d'),
        'user_id': lambda self,cr,uid,context: uid,
        'company_id': lambda s,cr,uid,c: s.pool.get('res.company')._company_default_get(cr, uid, 'account.coda', context=c),
    }

    def search(self, cr, user, args, offset=0, limit=None, order=None, context=None, count=False):
        if context is None: 
            context = {}
        res = super(account_coda, self).search(cr, user, args=args, offset=offset, limit=limit, order=order,
                context=context, count=count)
        if context.get('bank_statement', False) and not res:
            raise osv.except_osv('Error', _('Coda file not found for bank statement !!'))
        return res

account_coda()

class account_bank_statement(osv.osv):
    _inherit = "account.bank.statement"
    _columns = {
        'coda_id':fields.many2one('account.coda', 'Coda'),
    }

account_bank_statement()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: