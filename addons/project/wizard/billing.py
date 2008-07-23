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

import wizard
import ir
from mx.DateTime import now
import pooler
import netsvc

bill_form = """<?xml version="1.0" ?>
<form string="Billing wizard">
    <field name="journal_id"/>
    <field name="sale_account_id"/>
    <newline/>
    <field name="task_total"/>
    <field name="task_invoice"/>
    <field name="invoice_num"/>
    <field name="total"/>
</form>"""

bill_fields = {
    'journal_id':{'string':'Journal', 'type':'many2one', 'relation':'account.journal', 'required': 'True'},
    'sale_account_id':{'string':'Income account', 'type':'many2one', 'relation':'account.account', 'required': 'True'},
    'invoice_num' : {'string':'Generated invoices', 'type': 'integer', 'readonly': 'True'},
    'task_total' : {'string':'Number of tasks', 'type': 'integer', 'readonly': 'True'},
    'task_invoice' : {'string':'Tasks to invoice', 'type': 'integer', 'readonly': 'True'},
    'total' : {'string':'Total Price', 'type': 'float', 'readonly': 'True'},
}

ack_form = """<?xml version="1.0" ?>
<form string="Billing wizard">
    <separator string="The orders were successfully generated" />
</form>"""

ack_fields = {}

def _compute_orders(self, cr, uid, data, context):
    tasks = pooler.get_pool(cr.dbname).get('project.task').browse(cr, uid, data['ids'])
    projects = {}
    tot = 0.0
    task_tot = 0
    task_inv = 0
    for task in tasks:
        project = task.project_id
        if not task.invoice_id and task.billable:
            if project.mode == 'project':
                tot += project.tariff
            elif project.mode == 'effective':
                tot += project.tariff * task.effective_hours
            elif project.mode == 'hour':
                tot += project.tariff * task.planned_hours
            task_inv += 1
            projects[project.id] = projects.get(project.id, []) + [task.id]
        task_tot += 1
    res = {'invoice_num': len(projects), 'total': tot, 'task_total': task_tot, 'task_invoice':task_inv}
    return res

def _do_orders(self, cr, uid, data, context):
    tasks = pooler.get_pool(cr.dbname).get('project.task').browse(cr, uid, data['ids'])
    invoiceline = pooler.get_pool(cr.dbname).get('account.invoice.line')
    customers = {}
    for task in filter(lambda t: t.billable and not t.invoice_id, tasks):
        if not task.project_id.id in customers:
            partner = task.partner_id or task.project_id.partner_id
            if not partner.id:
                raise wizard.except_wizard(_('Error !'), _('No partner defined for the task or project.'))
            if not task.project_id.pricelist_id.id:
                raise wizard.except_wizard(_('Error !'), _('No pricelist defined in the project definition.'))
            adr = pooler.get_pool(cr.dbname).get('res.partner').address_get(cr, uid, [partner.id], ['default','invoice','shipping'])

            a = partner.property_account_receivable.id
            if partner.property_payment_term:
                pay_term = partner.property_payment_term.id
            else:
                pay_term = False

            oid = pooler.get_pool(cr.dbname).get('account.invoice').create(cr, uid, {
                'name': task.project_id.name,
                'origin': 'Task:'+str(task.id),
                'state': 'draft',
                'partner_id': partner.id,
                'address_contact_id': adr['default'],
                'address_invoice_id': adr['invoice'],
                'account_id': a,
                'type': 'out_invoice',
                'currency_id': task.project_id.pricelist_id.currency_id.id,
                'payment_term': pay_term,
                'journal_id': data['form']['journal_id'],
            })
            customers[task.project_id.id] = oid
        else:
            oid = customers[task.project_id.id]

        if task.project_id.mode == 'project':
            qty = 1
        elif task.project_id.mode == 'effective':
            qty = task.effective_hours
        else:
            qty = task.planned_hours

        invoiceline.create(cr, uid, {
            'invoice_id': oid,
            'name': task.name,
            'account_id': data['form']['sale_account_id'],
            'price_unit': task.project_id.tariff,
            'quantity': qty,
            'invoice_line_tax_id': [(6,0, [t.id for t in task.project_id.tax_ids])],
            'account_analytic_id': task.project_id.category_id.id,
        })
        #pooler.get_pool(cr.dbname).get('project.task').write(cr, uid, [task.id], {'invoice_id':oid})
    return {
        'domain': "[('id','in', ["+','.join(map(str,customers.values()))+"])]",
        'name': 'Invoices',
        'view_type': 'form',
        'view_mode': 'tree,form',
        'res_model': 'account.invoice',
        'view_id': False,
        'context': "{'type':'out_invoice'}",
        'type': 'ir.actions.act_window'
    }


class wiz_bill(wizard.interface):
    states = {
        'init':{
            'actions': [_compute_orders],
            'result': {'type':'form', 'arch':bill_form, 'fields':bill_fields, 'state':[('end', 'Cancel'), ('bill', 'Ok')] },
        },
        'bill':{
            'actions': [],
            'result': {'type':'action', 'action':_do_orders, 'state':'end' },
        },
    }
wiz_bill('project.wiz_bill')


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

