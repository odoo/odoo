# -*- encoding: utf-8 -*-
#
#  l10_ch
#  invoice.py
#
#  Created by Nicolas Bessi based on Credric Krier contribution
#
#  Copyright (c) 2010 CamptoCamp. All rights reserved.
##############################################################################
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
from osv import fields, osv
from tools import mod10r
from mx import DateTime


class AccountInvoice(osv.osv):
    """Inherit account.invoice in order to add bvr
    printing functionnalites. BVR is a Swiss payment vector"""
    _inherit = "account.invoice"
    
    ## @param self The object pointer.
    ## @param cursor a psycopg cursor
    ## @param user res.user.id that is currently loged
    ## @parma context a standard dict 
    ## @return a list of tuple (name,value)
    def _get_reference_type(self, cursor, user, context=None):
        """Function use by the function field reference_type in order 
        to initalise available BVR Reference Types"""
        res = super(AccountInvoice, self)._get_reference_type(cursor, user,
                context=context)
        res.append(('bvr', 'BVR'))
        return res
    
    ## @param self The object pointer.
    ## @param cursor a psycopg cursor
    ## @param user res.user.id that is currently loged
    ## @parma context a standard dict
    ## @param name of the files 
    ## @param args a list of diverse argument 
    ## @parma context a standard dict 
    ## @return a  dict (invoice id,amount to pay)
    def _amount_to_pay(self, cursor, user, ids, name, args, context=None):
        '''Return the amount still to pay regarding all the payment orders'''
        if not ids:
            return {}
        res = {}
        for invoice in self.browse(cursor, user, ids, context=context):
            res[invoice.id] = 0.0
            if invoice.move_id:
                for line in invoice.move_id.line_id:
                    if not line.date_maturity or \
                            DateTime.strptime(line.date_maturity, '%Y-%m-%d') \
                            < DateTime.now():
                        res[invoice.id] += line.amount_to_pay
        return res

    _columns = {
        ### BVR reference type BVR or FREE
        'reference_type': fields.selection(_get_reference_type,
            'Reference Type', required=True),
        ### Partner bank link between bank and partner id   
        'partner_bank': fields.many2one('res.partner.bank', 'Bank Account',
            help='The partner bank account to pay\n \
            Keep empty to use the default'
            ),
        ### Amount to pay
        'amount_to_pay': fields.function(_amount_to_pay, method=True,
            type='float', string='Amount to be paid',
            help='The amount which should be paid at the current date\n' \
                    'minus the amount which is already in payment order'),
    }
    
    ## @param self The object pointer.
    ## @param cursor a psycopg cursor
    ## @param user res.user.id that is currently loged
    ## @parma ids invoices id
    ## @return a boolean True if valid False if invalid 
    def _check_bvr(self, cursor, uid, ids):
        """
        Function to validate a bvr reference like :
        0100054150009>132000000000000000000000014+ 1300132412>
        The validation is based on l10n_ch
        """
        invoices = self.browse(cursor, uid, ids)
        for invoice in invoices:
            if invoice.reference_type == 'bvr':
                if not invoice.reference:
                    return False
                ## 
                # <010001000060190> 052550152684006+ 43435>
                # This references type are no longer supported by PostFinance
                #
                if mod10r(invoice.reference[:-1]) != invoice.reference and \
                    len(invoice.reference) == 15:
                    return True
                #
                if mod10r(invoice.reference[:-1]) != invoice.reference:
                    return False
        return True
    ## @param self The object pointer.
    ## @param cursor a psycopg cursor
    ## @param user res.user.id that is currently loged
    ## @parma ids invoices id
    ## @return a boolean True if valid False if invalid 
    def _check_reference_type(self, cursor, user, ids):
        """Check the customer invoice reference type depending 
        on the BVR reference type and the invoice partner bank type"""
        for invoice in self.browse(cursor, user, ids):
            if invoice.type in 'in_invoice':
                if invoice.partner_bank and \
                        invoice.partner_bank.state in \
                        ('bvrbank', 'bvrpost') and \
                        invoice.reference_type != 'bvr':
                    return False
        return True

    _constraints = [
        (_check_bvr, 'Error: Invalid Bvr Number (wrong checksum).',
            ['reference']),
        (_check_reference_type, 'Error: BVR reference is required.',
            ['reference_type']),
    ]

        
    ## @param self The object pointer.
    ## @param cursor a psycopg cursor
    ## @param user res.user.id that is currently loged
    ## @parma ids invoices id
    ## @param partner_bank_id the partner linked invoice bank
    ## @return the dict of values with the reference type  value updated 
    def onchange_partner_bank(self, cursor, user, ids, partner_bank_id):
        """update the reference type depending of the partner bank"""
        res = {'value': {}}
        partner_bank_obj = self.pool.get('res.partner.bank')
        if partner_bank_id:
            partner_bank = partner_bank_obj.browse(
                                                    cursor, 
                                                    user, 
                                                    partner_bank_id
                                                  )
            if partner_bank.state in ('bvrbank', 'bvrpost'):
                res['value']['reference_type'] = 'bvr'
        return res

AccountInvoice()

class AccountTaxCode(osv.osv):
    """Inherit account tax code in order
    to add a Case code"""
    _name = 'account.tax.code'
    _inherit = "account.tax.code"
    _columns = {
        ### The case code of the taxt code
        'code': fields.char('Case Code', size=512),
    }
AccountTaxCode()
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
