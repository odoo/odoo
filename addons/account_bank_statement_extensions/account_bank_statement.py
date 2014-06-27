# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#
#    Copyright (c) 2011 Noviat nv/sa (www.noviat.be). All rights reserved.
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
from openerp.osv import fields, osv
import openerp.addons.decimal_precision as dp
from openerp.tools.translate import _

class account_bank_statement(osv.osv):
    _inherit = 'account.bank.statement'

    def write(self, cr, uid, ids, vals, context=None):
        if context is None:
            context = {}
        # bypass obsolete statement line resequencing
        if vals.get('line_ids', False) or context.get('ebanking_import', False):
            res = super(osv.osv, self).write(cr, uid, ids, vals, context=context)
        else:
            res = super(account_bank_statement, self).write(cr, uid, ids, vals, context=context)
        return res

    def button_confirm_bank(self, cr, uid, ids, context=None):
        super(account_bank_statement, self).button_confirm_bank(cr, uid, ids, context=context)
        for st in self.browse(cr, uid, ids, context=context):
            if st.line_ids:
                cr.execute("UPDATE account_bank_statement_line  \
                    SET state='confirm' WHERE id in %s ",
                    (tuple([x.id for x in st.line_ids]),))
        return True

    def button_cancel(self, cr, uid, ids, context=None):
        super(account_bank_statement, self).button_cancel(cr, uid, ids, context=context)
        for st in self.browse(cr, uid, ids, context=context):
            if st.line_ids:
                cr.execute("UPDATE account_bank_statement_line  \
                    SET state='draft' WHERE id in %s ",
                    (tuple([x.id for x in st.line_ids]),))
        return True


class account_bank_statement_line_global(osv.osv):
    _name = 'account.bank.statement.line.global'
    _description = 'Batch Payment Info'

    _columns = {
        'name': fields.char('OBI', required=True, help="Originator to Beneficiary Information"),
        'code': fields.char('Code', size=64, required=True),
        'parent_id': fields.many2one('account.bank.statement.line.global', 'Parent Code', ondelete='cascade'),
        'child_ids': fields.one2many('account.bank.statement.line.global', 'parent_id', 'Child Codes'),
        'type': fields.selection([
            ('iso20022', 'ISO 20022'),
            ('coda', 'CODA'),
            ('manual', 'Manual'),
            ], 'Type', required=True),
        'amount': fields.float('Amount', digits_compute=dp.get_precision('Account')),
        'bank_statement_line_ids': fields.one2many('account.bank.statement.line', 'globalisation_id', 'Bank Statement Lines'),
    }
    _rec_name = 'code'
    _defaults = {
        'code': lambda s,c,u,ctx={}: s.pool.get('ir.sequence').get(c, u, 'account.bank.statement.line.global'),
        'name': '/',
    }
    _sql_constraints = [
        ('code_uniq', 'unique (code)', 'The code must be unique !'),
    ]

    def name_search(self, cr, user, name, args=None, operator='ilike', context=None, limit=100):
        if not args:
            args = []
        ids = []
        if name:
            ids = self.search(cr, user, [('code', 'ilike', name)] + args, limit=limit)
            if not ids:
                ids = self.search(cr, user, [('name', operator, name)] + args, limit=limit)
            if not ids and len(name.split()) >= 2:
                #Separating code and name for searching
                operand1, operand2 = name.split(' ', 1) #name can contain spaces
                ids = self.search(cr, user, [('code', 'like', operand1), ('name', operator, operand2)] + args, limit=limit)
        else:
            ids = self.search(cr, user, args, context=context, limit=limit)
        return self.name_get(cr, user, ids, context=context)


class account_bank_statement_line(osv.osv):
    _inherit = 'account.bank.statement.line'
    _columns = {
        'val_date': fields.date('Value Date', states={'confirm': [('readonly', True)]}),
        'globalisation_id': fields.many2one('account.bank.statement.line.global', 'Globalisation ID',
            states={'confirm': [('readonly', True)]},
            help="Code to identify transactions belonging to the same globalisation level within a batch payment"),
        'globalisation_amount': fields.related('globalisation_id', 'amount', type='float',
            relation='account.bank.statement.line.global', string='Glob. Amount', readonly=True),
        'state': fields.selection([('draft', 'Draft'), ('confirm', 'Confirmed')],
            'Status', required=True, readonly=True),
        'counterparty_name': fields.char('Counterparty Name', size=35),
        'counterparty_bic': fields.char('Counterparty BIC', size=11),
        'counterparty_number': fields.char('Counterparty Number', size=34),
        'counterparty_currency': fields.char('Counterparty Currency', size=3),
    }
    _defaults = {
        'state': 'draft',
    }

    def unlink(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        if context.get('block_statement_line_delete', False):
            raise osv.except_osv(_('Warning!'), _('Delete operation not allowed. \
            Please go to the associated bank statement in order to delete and/or modify bank statement line.'))
        return super(account_bank_statement_line, self).unlink(cr, uid, ids, context=context)


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
