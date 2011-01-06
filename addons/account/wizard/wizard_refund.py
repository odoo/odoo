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
import pooler
import osv
import netsvc
import time
from tools.translate import _

sur_form = '''<?xml version="1.0"?>
<form string="Credit Note">
    <label string="Are you sure you want to refund this invoice ?" colspan="2"/>
    <newline />
    <field name="date" />
    <field name="period" />
    <field name="description" width="150" />
</form>'''

sur_fields = {
    'date': {'string':'Operation date','type':'date', 'required':'False', 'default':time.strftime('%Y-%m-%d'), 'help' : 'This date will be used as the invoice date for Refund Invoice and Period will be chosen accordingly!'},
    'period':{'string': 'Force period', 'type': 'many2one',
        'relation': 'account.period', 'required': False},
    'description':{'string':'Description', 'type':'char', 'required':'True'},
    }


class wiz_refund(wizard.interface):

    def _invoice_refund(self, cr, uid, data, context):
        return self._compute_refund(cr, uid, data, 'refund', context)

    def _invoice_cancel(self, cr, uid, data, context):
        return self._compute_refund(cr, uid, data, 'cancel', context)

    def _invoice_modify(self, cr, uid, data, context):
        return self._compute_refund(cr, uid, data, 'modify', context)

    def _compute_refund(self, cr, uid, data, mode, context):
        form = data['form']
        pool = pooler.get_pool(cr.dbname)
        reconcile_obj = pool.get('account.move.reconcile')
        account_m_line_obj = pool.get('account.move.line')
        created_inv = []
        date = False
        period = False
        description = False
        for inv in pool.get('account.invoice').browse(cr, uid, data['ids']):
            if inv.state in ['draft', 'proforma2', 'cancel']:
                raise wizard.except_wizard(_('Error !'), _('Can not %s draft/proforma/cancel invoice.') % (mode))
            if form['period'] :
                period = form['period']
            else:
                period = inv.period_id and inv.period_id.id or False

            if form['date'] :
                date = form['date']
                if not form['period'] :
                    cr.execute("select name from ir_model_fields where model='account.period' and name='company_id'")
                    result_query = cr.fetchone()
                    if result_query:
                        #in multi company mode
                        cr.execute("""SELECT id
                                      from account_period where date('%s')
                                      between date_start AND  date_stop and company_id = %s limit 1 """%(
                                      form['date'],
                                      pool.get('res.users').browse(cr,uid,uid).company_id.id
                                      ))
                    else:
                        #in mono company mode
                        cr.execute("""SELECT id
                                      from account_period where date('%s')
                                      between date_start AND  date_stop  limit 1 """%(
                                        form['date'],
                                      ))
                    res = cr.fetchone()
                    if res:
                        period = res[0]
            else:
                date = inv.date_invoice

            if form['description'] :
                description = form['description']
            else:
                description = inv.name
            
            if not period:
                raise wizard.except_wizard(_('Data Insufficient !'), _('No Period found on Invoice!'))
                
            refund_id = pool.get('account.invoice').refund(cr, uid, [inv.id],date, period, description)
            refund = pool.get('account.invoice').browse(cr, uid, refund_id[0])
            # we compute due date
            #!!!due date = date inv date on formdate
            pool.get('account.invoice').write(cr, uid, [refund.id],{'date_due':date,'check_total':inv.check_total})
            # to make the taxes calculated
            pool.get('account.invoice').button_compute(cr, uid, refund_id)
            
            created_inv.append(refund_id[0])
            #if inv is paid we unreconcile
            if mode in ('cancel','modify'):
                movelines = inv.move_id.line_id
                #we unreconcile the lines
                to_reconcile_ids = {}
                for line in movelines :
                    #if the account of the line is the as the one in the invoice
                    #we reconcile
                    if line.account_id.id == inv.account_id.id :
                        to_reconcile_ids[line.account_id.id] =[line.id]
                    if type(line.reconcile_id) != osv.orm.browse_null :
                        reconcile_obj.unlink(cr,uid, line.reconcile_id.id)
                #we advance the workflow of the refund to open
                wf_service = netsvc.LocalService('workflow')
                wf_service.trg_validate(uid, 'account.invoice', refund.id, 'invoice_open', cr)
                #we reload the browse record
                refund = pool.get('account.invoice').browse(cr, uid, refund_id[0])
                #we match the line to reconcile
                for tmpline in  refund.move_id.line_id :
                    if tmpline.account_id.id == inv.account_id.id :
                        to_reconcile_ids[tmpline.account_id.id].append(tmpline.id)
                for account in to_reconcile_ids :
                    account_m_line_obj.reconcile(cr, uid, to_reconcile_ids[account],
                        writeoff_period_id=period,
                        writeoff_journal_id=inv.journal_id.id,
                        writeoff_acc_id=inv.account_id.id
                    )
                #we create a new invoice that is the copy of the original
                if mode == 'modify' :
                    invoice = pool.get('account.invoice').read(cr, uid, [inv.id],
                        ['name', 'type', 'number', 'reference',
                            'comment', 'date_due', 'partner_id', 'address_contact_id',
                            'address_invoice_id', 'partner_insite','partner_contact',
                            'partner_ref', 'payment_term', 'account_id', 'currency_id',
                            'invoice_line', 'tax_line', 'journal_id','period_id'
                        ]
                    )
                    invoice = invoice[0]
                    del invoice['id']
                    invoice_lines = pool.get('account.invoice.line').read(cr, uid, invoice['invoice_line'])
                    invoice_lines = pool.get('account.invoice')._refund_cleanup_lines(cr, uid, invoice_lines)
                    tax_lines = pool.get('account.invoice.tax').read(
                        cr, uid, invoice['tax_line'])
                    tax_lines = pool.get('account.invoice')._refund_cleanup_lines(cr, uid, tax_lines)

                    invoice.update({
                        'type': inv.type,
                        'date_invoice': date,
                        'state': 'draft',
                        'number': False,
                        'invoice_line': invoice_lines,
                        'tax_line': tax_lines,
                        'period_id': period,
                        'name':description
                        })

                    #take the id part of the tuple returned for many2one fields
                    for field in ('address_contact_id', 'address_invoice_id', 'partner_id',
                        'account_id', 'currency_id', 'payment_term', 'journal_id'):
                        invoice[field] = invoice[field] and invoice[field][0]

                    # create the new invoice
                    inv_id = pool.get('account.invoice').create(cr, uid, invoice,{})
                    # we compute due date
                    if inv.payment_term.id:
                        data = pool.get('account.invoice').onchange_payment_term_date_invoice(cr, uid, [inv_id],inv.payment_term.id,date)
                        if 'value' in data and data['value']:
                            pool.get('account.invoice').write(cr, uid, [inv_id],data['value'])
                    created_inv.append(inv_id)

        #we get the view id
        mod_obj = pool.get('ir.model.data')
        act_obj = pool.get('ir.actions.act_window')
        if inv.type == 'out_invoice':
            xml_id = 'action_invoice_tree5'
        elif inv.type == 'in_invoice':
            xml_id = 'action_invoice_tree8'
        elif inv.type == 'out_refund':
            xml_id = 'action_invoice_tree10'
        else:
            xml_id = 'action_invoice_tree12'
        #we get the model
        result = mod_obj._get_id(cr, uid, 'account', xml_id)
        id = mod_obj.read(cr, uid, result, ['res_id'])['res_id']
        # we read the act window
        result = act_obj.read(cr, uid, id)
        result['res_id'] = created_inv

        return result

    states = {
        'init': {
            'actions': [],
            'result': {'type':'form', 'arch':sur_form, 'fields':sur_fields, 'state':[('end','Cancel'),('refund','Refund Invoice'),('cancel_invoice','Cancel Invoice'),('modify_invoice','Modify Invoice')]}
        },
        'refund': {
            'actions': [],
            'result': {'type':'action', 'action':_invoice_refund, 'state':'end'},
        },
        'cancel_invoice': {
            'actions': [],
            'result': {'type':'action', 'action':_invoice_cancel, 'state':'end'},
        },
        'modify_invoice': {
            'actions': [],
            'result': {'type':'action', 'action':_invoice_modify, 'state':'end'},
        },

    }
wiz_refund('account.invoice.refund')

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

