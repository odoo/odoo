# -*- encoding: utf-8 -*-
#
#  bvr_import.py
#  l10n_ch
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
"""Wizard that will import v11 File from your bank"""
import wizard
import pooler
import base64
import time
from tools import mod10r
import re
from tools.translate import _

ASK_FORM = """<?xml version="1.0"?>
<form string="BVR Import">
    <field name="file"/>
</form>"""

ASK_FIELDS = {
    'file': {
        'string': 'BVR file',
        'type': 'binary',
        'required': True,
    },
}

## @param cursor a psycopg cursor
## @param user res.user.id that is currently loged
## @Reference ESR/BVR reference 
## See Postfinance Manuel BVR chapter 3.5.x 
## @context context dict
## @return a list of account invoice lines
def _reconstruct_invoice_ref(cursor, user, reference, context):
    """Fetch invices line linked to the BVR/ESR references"""
    id_invoice = False
    # We first search on all invoices
    # we now search for company
    user_obj=pooler.get_pool(cursor.dbname).get('res.users')
    user_current=user_obj.browse(cursor, user, user)
    cursor.execute("SELECT inv.id,inv.number from account_invoice AS \
        inv where inv.company_id = " + str(user_current.company_id.id))
    result_invoice = cursor.fetchall()
    
    for inv_id,inv_name in result_invoice:
        inv_name =  re.sub('[^0-9]', '', str(inv_name))
        if inv_name == reference:
            id_invoice = inv_id
            break
    if  id_invoice:
        cursor.execute('SELECT l.id ' \
            'FROM account_move_line l, account_invoice i ' \
            'WHERE l.move_id = i.move_id AND l.reconcile_id is NULL  ' \
            'AND i.id in (' + ','.join([str(x) for x in [id_invoice]]) + ')')
        inv_line = []
        for id_line in cursor.fetchall():
            inv_line.append(id_line[0])
        return inv_line
    else:
        return []
    return True
    
    
## @obj wizard object
## @param cursor a psycopg cursor
## @param user res.user.id that is currently loged
## @data wizzard data
## @context context dict
## @return a wizzard dict    
def _import(obj, cursor, user, data, context):
    """import the recieve file in the bank statement and do the reconciliation"""

    pool = pooler.get_pool(cursor.dbname)
    statement_line_obj = pool.get('account.bank.statement.line')
    statement_reconcile_obj = pool.get('account.bank.statement.reconcile')
    move_line_obj = pool.get('account.move.line')
    property_obj = pool.get('ir.property')
    model_fields_obj = pool.get('ir.model.fields')
    attachment_obj = pool.get('ir.attachment')
    file = data['form']['file']
    statement_id = data['id']
    records = []
    total_amount = 0
    total_cost = 0
    find_total = False
    #we recieve the file in base 64 so we decode it
    for lines in base64.decodestring(file).split("\n"):
        # Manage files without carriage return
        while lines:
            (line, lines) = (lines[:128], lines[128:])
            record = {}

            if line[0:3] in ('999', '995'):
                if find_total:
                    raise wizard.except_wizard(_('Error'),
                            _('Too much total record found!'))
                find_total = True
                if lines:
                    raise wizard.except_wizard(_('Error'),
                            _('Record found after total record!'))
                amount = float(line[39:49]) + (float(line[49:51]) / 100)
                cost = float(line[69:76]) + (float(line[76:78]) / 100)
                if line[2] == '5':
                    amount *= -1
                    cost *= -1

                if round(amount - total_amount, 2) >= 0.01 \
                        or round(cost - total_cost, 2) >= 0.01:
                    raise wizard.except_wizard(_('Error'),
                            _('Total record different from the computed!'))
                if int(line[51:63]) != len(records):
                    raise wizard.except_wizard(_('Error'),
                            _('Number record different from the computed!'))
            else:
                record = {
                    'reference': line[12:39],
                    'amount': float(line[39:47]) + (float(line[47:49]) / 100),
                    'date': time.strftime('%Y-%m-%d',
                        time.strptime(line[65:71], '%y%m%d')),
                    'cost': float(line[96:98]) + (float(line[98:100]) / 100),
                }

                if record['reference'] != mod10r(record['reference'][:-1]):
                    raise wizard.except_wizard(_('Error'),
                        _('Recursive mod10 is invalid for reference: %s') % \
                                record['reference'])

                if line[2] == '5':
                    record['amount'] *= -1
                    record['cost'] *= -1
                total_amount += record['amount']
                total_cost += record['cost']
                records.append(record)

    model_fields_ids = model_fields_obj.search(
                            cursor, 
                            user, 
                            [
                                ('name', 'in', [
                                                'property_account_receivable', 
                                                'property_account_payable'
                                                ]
                                ),
                                ('model', '=', 'res.partner'),
                            ], 
                            context=context
                        )
    property_ids = property_obj.search(cursor, user, [
        ('fields_id', 'in', model_fields_ids),
        ('res_id', '=', False),
        ], context=context)

    account_receivable = False
    account_payable = False
    for property in property_obj.browse(cursor, user, 
        property_ids, context=context):
        if property.fields_id.name == 'property_account_receivable':
            account_receivable = int(property.value.split(',')[1])
        elif property.fields_id.name == 'property_account_payable':
            account_payable = int(property.value.split(',')[1])

    for record in records:
        # Remove the 11 first char because it can be adherent number
        reference = record['reference'][11:-1].lstrip('0')
        values = {
            'name': 'IN '+ reference,
            'date': record['date'],
            'amount': record['amount'],
            'ref': reference,
            'type': (record['amount'] >= 0 and 'customer') or 'supplier',
            'statement_id': statement_id,
        }
        line_ids = move_line_obj.search(cursor, user, [
            ('ref', 'like', reference),
            ('reconcile_id', '=', False),
            ('account_id.type', 'in', ['receivable', 'payable']),
            ], order='date desc', context=context)
        if not line_ids:
            line_ids = _reconstruct_invoice_ref(cursor,user,reference,None)
            
        line2reconcile = False
        partner_id = False
        account_id = False
        for line in move_line_obj.browse(cursor, user, 
            line_ids, context=context):
            if line.partner_id.id:
                partner_id = line.partner_id.id
            if record['amount'] >= 0:
                if round(record['amount'] - line.debit, 2) < 0.01:
                    line2reconcile = line.id
                    account_id = line.account_id.id
                    break
            else:
                if round(line.credit + record['amount'], 2) < 0.01:
                    line2reconcile = line.id
                    account_id = line.account_id.id
                    break
        if not account_id:
            if record['amount'] >= 0:
                account_id = account_receivable
            else:
                account_id = account_payable
        if not account_id :
            raise wizard.except_wizard(_('Error'),
                _('The properties account payable account receivable'))
        values['account_id'] = account_id
        values['partner_id'] = partner_id

        if line2reconcile:
            values['reconcile_id'] = statement_reconcile_obj.create(
                                    cursor, 
                                    user, 
                                    {
                                        'line_ids': [(6, 0, [line2reconcile])],
                                    }, 
                                    context=context
                                )

        statement_line_obj.create(cursor, user, values, context=context)
    attachment_obj.create(cursor, user, {
        'name': 'BVR',
        'datas': file,
        'datas_fname': 'BVR.txt',
        'res_model': 'account.bank.statement',
        'res_id': statement_id,
        }, context=context)
    return {}


class BVRImport(wizard.interface):
    "Wizard that will import v11 File from your bank"
    states = {
        'init': {
            'actions': [],
            'result': {
                'type': 'form',
                'arch': ASK_FORM,
                'fields': ASK_FIELDS,
                'state': [
                    ('end', 'Cancel', 'gtk-cancel'),
                    ('import', 'Import', 'gtk-ok', True),
                ],
            },
        },
        'import': {
            'actions': [],
            'result': {
                'type': 'action',
                'action': _import,
                'state': 'end',
            },
        },
    }

BVRImport('l10n_ch.bvr_import')
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
