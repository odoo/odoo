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
from openerp.osv import osv, fields

class account_bank_statement(osv.osv):
    _inherit = 'account.bank.statement'
    _columns = {
        'coda_note': fields.text('CODA Notes'),
    }


class account_bank_statement_line(osv.osv):
    _inherit = 'account.bank.statement.line'
    _columns = {
        'coda_account_number': fields.char('Account Number', help="The Counter Party Account Number")
    }

    def create(self, cr, uid, data, context=None):
        """
            This function creates a Bank Account Number if, for a bank statement line,
            the partner_id field and the coda_account_number field are set,
            and the account number does not exist in the database
        """
        if 'partner_id' in data and data['partner_id'] and 'coda_account_number' in data and data['coda_account_number']:
            acc_number_ids = self.pool.get('res.partner.bank').search(cr, uid, [('acc_number', '=', data['coda_account_number'])])
            if len(acc_number_ids) == 0:
                try:
                    type_model, type_id = self.pool.get('ir.model.data').get_object_reference(cr, uid, 'base', 'bank_normal')
                    type_id = self.pool.get('res.partner.bank.type').browse(cr, uid, type_id, context=context)
                    self.pool.get('res.partner.bank').create(cr, uid, {'acc_number': data['coda_account_number'], 'partner_id': data['partner_id'], 'state': type_id.code}, context=context)
                except ValueError:
                    pass
        return super(account_bank_statement_line, self).create(cr, uid, data, context=context)

    def write(self, cr, uid, ids, vals, context=None):
        super(account_bank_statement_line, self).write(cr, uid, ids, vals, context)
        """
            Same as create function above, but for write function
        """
        if 'partner_id' in vals:
            for line in self.pool.get('account.bank.statement.line').browse(cr, uid, ids, context=context):
                if line.coda_account_number:
                    acc_number_ids = self.pool.get('res.partner.bank').search(cr, uid, [('acc_number', '=', line.coda_account_number)])
                    if len(acc_number_ids) == 0:
                        try:
                            type_model, type_id = self.pool.get('ir.model.data').get_object_reference(cr, uid, 'base', 'bank_normal')
                            type_id = self.pool.get('res.partner.bank.type').browse(cr, uid, type_id, context=context)
                            self.pool.get('res.partner.bank').create(cr, uid, {'acc_number': line.coda_account_number, 'partner_id': vals['partner_id'], 'state': type_id.code}, context=context)
                        except ValueError:
                            pass
        return True


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
