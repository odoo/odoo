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

import wizard
import netsvc
import pooler
import time
from tools.translate import _

#TODO:

# a rajouter comme questions ds le wizard:
# - account_id (et mettre wizard ds le menu et pas sur client_action_multi)
# - journal
# - compte d'ajustement
# - montant max (0,03)
    # <field name="max_amount"/>
# - libelle write-off
# - devise principale ou secondaire
    # devise secondaire = amount_currency
    # si devise: pas prendre ceux avec montant_devise = 0

# a demander à fabien:
# - checkbox (comme ds sage) "lettrage rapide des comptes soldés"?

# pr creer ecriture: creer move.line avec period et journal dans le contexte
# faire methode sur period: get_current_period

_reconcile_form = '''<?xml version="1.0"?>
<form string="Reconciliation">
    <separator string="Options" colspan="4"/>
    <field name="account_ids" colspan="4" domain="[('reconcile','=',1)]" views="account.view_account_list">
    </field>
    <field name="date1"/>
    <field name="date2"/>
    <field name="power"/>
    <separator string="Write-Off Move" colspan="4"/>
    <field name="max_amount"/>
    <field name="writeoff_acc_id"/>
    <field name="journal_id"/>
    <field name="period_id"/>
</form>'''

_reconcile_fields = {
    'account_ids': {
        'string': 'Account to reconcile',
        'type': 'many2many',
        'relation': 'account.account',
        'domain': [('reconcile','=',1)],
        'help': 'If no account is specified, the reconciliation will be made using every accounts that can be reconcilied',
    },
    'writeoff_acc_id': {
        'string': 'Account',
        'type': 'many2one',
        'relation': 'account.account',
        'required': True
    },
    'journal_id': {
        'string': 'Journal',
        'type': 'many2one',
        'relation': 'account.journal',
        'required': True
    },
    'period_id': {
        'string': 'Period',
        'type': 'many2one',
        'relation': 'account.period',
        'required': True
    },
    'max_amount': {
        'string': 'Maximum write-off amount',
        'type': 'float',
    },
    #'currency': {
    #   'string': 'Reconcile in',
    #   'type': 'selection',
    #   'selection': [('current','current currency'), ('secondary','secondary currency')],
    #   'required': True
    #},
    'power': {
        'string': 'Power',
        'type': 'selection',
        'selection': [(p,str(p)) for p in range(2, 10)],
        'required': True
    },
    'date1': {
        'string': 'Start of period',
        'type': 'date',
        'required': True,
        'default': lambda *a: time.strftime('%Y-01-01')
    },
    'date2': {
        'string': 'End of period',
        'type': 'date',
        'required': True,
        'default': lambda *a: time.strftime('%Y-%m-%d')
    },
}

_result_form = '''<?xml version="1.0"?>
<form string="Reconciliation result">
    <field name="reconciled"/>
    <newline/>
    <field name="unreconciled"/>
</form>'''

_result_fields = {
    'reconciled': {
        'string': 'Reconciled transactions',
        'type': 'integer',
        'readonly': True
    },
    'unreconciled': {
        'string': 'Not reconciled transactions',
        'type': 'integer',
        'readonly': True
    },
}

#TODO: cleanup and comment this code... For now, it is awfulllll
# (way too complex, and really slow)...
def do_reconcile(cr, uid, credits, debits, max_amount, power, writeoff_acc_id, period_id, journal_id, context={}):
    # for one value of a credit, check all debits, and combination of them
    # depending on the power. It starts with a power of one and goes up
    # to the max power allowed
    def check2(value, move_list, power):
        def check(value, move_list, power):
            for i in range(len(move_list)):
                move = move_list[i]
                if power == 1:
                    if abs(value - move[1]) <= max_amount + 0.00001:
                        return [move[0]]
                else:
                    del move_list[i]
                    res = check(value - move[1], move_list, power-1)
                    move_list[i:i] = [move]
                    if res:
                        res.append(move[0])
                        return res
            return False

        for p in range(1, power+1):
            res = check(value, move_list, p)
            if res:
                return res
        return False

    # for a list of credit and debit and a given power, check if there 
    # are matching tuples of credit and debits, check all debits, and combination of them
    # depending on the power. It starts with a power of one and goes up
    # to the max power allowed
    def check4(list1, list2, power):
        def check3(value, list1, list2, list1power, power):
            for i in range(len(list1)):
                move = list1[i]
                if list1power == 1:
                    res = check2(value + move[1], list2, power - 1)
                    if res:
                        return ([move[0]], res)
                else:
                    del list1[i]
                    res = check3(value + move[1], list1, list2, list1power-1, power-1)
                    list1[i:i] = [move]
                    if res:
                        x, y = res
                        x.append(move[0])
                        return (x, y)
            return False

        for p in range(1, power):
            res = check3(0, list1, list2, p, power)
            if res:
                return res
        return False
            
    def check5(list1, list2, max_power):
        for p in range(2, max_power+1):
            res = check4(list1, list2, p)
            if res:
                return res

    ok = True
    reconciled = 0
    move_line_obj = pooler.get_pool(cr.dbname).get('account.move.line')
    while credits and debits and ok:
        res = check5(credits, debits, power)
        if res:
            move_line_obj.reconcile(cr, uid, res[0] + res[1], 'auto', writeoff_acc_id, period_id, journal_id, context)
            reconciled += len(res[0]) + len(res[1])
            credits = [(id, credit) for (id, credit) in credits if id not in res[0]]
            debits = [(id, debit) for (id, debit) in debits if id not in res[1]]
        else:
            ok = False
    return (reconciled, len(credits)+len(debits))
                
def _reconcile(self, cr, uid, data, context):
    service = netsvc.LocalService("object_proxy")
    move_line_obj = pooler.get_pool(cr.dbname).get('account.move.line')
    form = data['form']
    max_amount = form.get('max_amount', 0.0)
    power = form['power']
    reconciled = unreconciled = 0
    if not form['account_ids'][0][2]:
        raise wizard.except_wizard(_('UserError'), _('You must select accounts to reconcile'))
    for account_id in form['account_ids'][0][2]:
    
        # reconcile automatically all transactions from partners whose balance is 0
        cr.execute(
            "SELECT partner_id " \
            "FROM account_move_line " \
            "WHERE account_id=%s " \
            "AND reconcile_id IS NULL " \
            "AND state <> 'draft' " \
            "GROUP BY partner_id " \
            "HAVING ABS(SUM(debit-credit)) < %s AND count(*)>0",
            (account_id, max_amount or 0.0))
        partner_ids = [id for (id,) in cr.fetchall()]

        for partner_id in partner_ids:
            cr.execute(
                "SELECT id " \
                "FROM account_move_line " \
                "WHERE account_id=%s " \
                "AND partner_id=%s " \
                "AND state <> 'draft' " \
                "AND reconcile_id IS NULL",
                (account_id, partner_id))
            line_ids = [id for (id,) in cr.fetchall()]
            
            if len(line_ids):
                move_line_obj.reconcile(cr, uid, line_ids, 'auto', form['writeoff_acc_id'], form['period_id'], form['journal_id'], context)
                reconciled += len(line_ids)
        
        # get the list of partners who have more than one unreconciled transaction
        cr.execute(
            "SELECT partner_id " \
            "FROM account_move_line " \
            "WHERE account_id=%s " \
            "AND reconcile_id IS NULL " \
            "AND state <> 'draft' " \
            "AND partner_id IS NOT NULL " \
            "GROUP BY partner_id " \
            "HAVING count(*)>1",
            (account_id,))
        partner_ids = [id for (id,) in cr.fetchall()]
        #filter?
        for partner_id in partner_ids:
            # get the list of unreconciled 'debit transactions' for this partner
            cr.execute(
                "SELECT id, debit " \
                "FROM account_move_line " \
                "WHERE account_id=%s " \
                "AND partner_id=%s " \
                "AND reconcile_id IS NULL " \
                "AND state <> 'draft' " \
                "AND debit > 0 " \
                "ORDER BY date_maturity",
                (account_id, partner_id))
            debits = cr.fetchall()
                
            # get the list of unreconciled 'credit transactions' for this partner
            cr.execute(
                "SELECT id, credit " \
                "FROM account_move_line " \
                "WHERE account_id=%s " \
                "AND partner_id=%s " \
                "AND reconcile_id IS NULL " \
                "AND state <> 'draft' " \
                "AND credit > 0 " \
                "ORDER BY date_maturity",
                (account_id, partner_id))
            credits = cr.fetchall()
            
            (rec, unrec) = do_reconcile(cr, uid, credits, debits, max_amount, power, form['writeoff_acc_id'], form['period_id'], form['journal_id'], context)
            reconciled += rec
            unreconciled += unrec

        # add the number of transactions for partners who have only one 
        # unreconciled transactions to the unreconciled count
        partner_filter = partner_ids and 'AND partner_id not in (%s)' % ','.join(map(str, filter(None, partner_ids))) or ''
        cr.execute(
            "SELECT count(*) " \
            "FROM account_move_line " \
            "WHERE account_id=%s " \
            "AND reconcile_id IS NULL " \
            "AND state <> 'draft' " + partner_filter,
            (account_id,))
        additional_unrec = cr.fetchone()[0]
    return {'reconciled':reconciled, 'unreconciled':unreconciled+additional_unrec}

class wiz_reconcile(wizard.interface):
    states = {
        'init': {
            'actions': [],
            'result': {'type':'form', 'arch':_reconcile_form, 'fields':_reconcile_fields, 'state':[('end','Cancel'),('reconcile','Reconcile')]}
        },
        'reconcile': {
            'actions': [_reconcile],
            'result': {'type':'form', 'arch':_result_form, 'fields':_result_fields, 'state':[('end','OK')]}
        }
    }
wiz_reconcile('account.automatic.reconcile')


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

