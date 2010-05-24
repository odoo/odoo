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

class account_coda(osv.osv):
    _name = "account.coda"
    _description = "coda for an Account"
    _columns = {
        'name': fields.binary('Coda file', readonly=True),
        'statement_ids': fields.one2many('account.bank.statement','coda_id','Generated Bank Statement', readonly=True),
        'note': fields.text('Import log', readonly=True),
        'journal_id': fields.many2one('account.journal','Bank Journal', readonly=True,select=True),
        'date': fields.date('Import Date', readonly=True,select=True),
        'user_id': fields.many2one('res.users','User', readonly=True, select=True),
    }
    _defaults = {
        'date': lambda *a: time.strftime('%Y-%m-%d'),
        'user_id': lambda self,cr,uid,context: uid,
    }
account_coda()

class account_bank_statement(osv.osv):
    _inherit = "account.bank.statement"
    _columns = {
        'coda_id':fields.many2one('account.coda','Coda'),
    }
account_bank_statement()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

