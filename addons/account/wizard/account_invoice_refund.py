# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
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
from osv import fields, osv
from tools.translate import _
import netsvc

class account_invoice_refund(osv.osv_memory):

    """Refunds invoice."""

    _name = "account.invoice.refund"
    _description = "Invoice Refund"
    _columns = {
       'date': fields.date('Operation date', required=False),
       'period': fields.many2one('account.period', 'Force period', required=False),
       'description': fields.char('Description', size=150, required=True),
                }

    def compute_refund(self, cr, uid, ids, mode, context=None):
        """
        @param cr: the current row, from the database cursor,
        @param uid: the current user’s ID for security checks,
        @param ids: the account invoice refund’s ID or list of IDs

        """
        inv_obj = self.pool.get('account.invoice')
        reconcile_obj = self.pool.get('account.move.reconcile')
        account_m_line_obj = self.pool.get('account.move.line')
        mod_obj = self.pool.get('ir.model.data')
        act_obj = self.pool.get('ir.actions.act_window')

        if context is None:
            context = {}

        for form in  self.read(cr, uid, ids, context=context):
            created_inv = []
            date = False
            period = False
            description = False
            for inv in inv_obj.browse(cr, uid, context['active_ids'],context=context):
                if inv.state in ['draft', 'proforma2', 'cancel']:
                    raise osv.except_osv(_('Error !'), _('Can not %s draft/proforma/cancel invoice.') % (mode))
                if form['period'] :
                    period = form['period']
                else:
                    period = inv.period_id and inv.period_id.id or False

                if form['date'] :
                    date = form['date']
                    if not form['period'] :
                            cr.execute("select name from ir_model_fields \
                                            where model = 'account.period' \
                                            and name = 'company_id'")
                            result_query = cr.fetchone()
                            if result_query:
                                cr.execute("""SELECT id
                                          from account_period where date('%s')
                                          between date_start AND  date_stop \
                                          and company_id = %s limit 1 """,
                                          (form['date'], self.pool.get('res.users').browse(cr, uid, uid,context=context).company_id.id,))
                            else:
                                cr.execute("""SELECT id
                                        from account_period where date('%s')
                                        between date_start AND  date_stop  \
                                        limit 1 """, (form['date'],))
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
                    raise osv.except_osv(_('Data Insufficient !'), \
                                            _('No Period found on Invoice!'))

                refund_id = inv_obj.refund(cr, uid, [inv.id], date, period, description)
                refund = inv_obj.browse(cr, uid, refund_id[0],context=context)
                inv_obj.write(cr, uid, [refund.id], {'date_due': date,
                                                'check_total': inv.check_total})
                inv_obj.button_compute(cr, uid, refund_id)

                created_inv.append(refund_id[0])
                if mode in ('cancel', 'modify'):
                    movelines = inv.move_id.line_id
                    to_reconcile_ids = {}
                    for line in movelines :
                        if line.account_id.id == inv.account_id.id :
                            to_reconcile_ids[line.account_id.id] = [line.id]
                        if type(line.reconcile_id) != osv.orm.browse_null :
                            reconcile_obj.unlink(cr, uid, line.reconcile_id.id)
                    wf_service = netsvc.LocalService('workflow')
                    wf_service.trg_validate(uid, 'account.invoice', \
                                        refund.id, 'invoice_open', cr)
                    refund = inv_obj.browse(cr, uid, refund_id[0],context=context)
                    for tmpline in  refund.move_id.line_id :
                        if tmpline.account_id.id == inv.account_id.id :
                            to_reconcile_ids[tmpline.account_id.id].append(tmpline.id)
                    for account in to_reconcile_ids :
                        account_m_line_obj.reconcile(cr, uid, to_reconcile_ids[account],
                                        writeoff_period_id=period,
                                        writeoff_journal_id=inv.journal_id.id,
                                        writeoff_acc_id=inv.account_id.id
                                        )
                    if mode == 'modify' :
                        invoice = inv_obj.read(cr, uid, [inv.id],
                                    ['name', 'type', 'number', 'reference',
                                    'comment', 'date_due', 'partner_id',
                                    'address_contact_id', 'address_invoice_id',
                                    'partner_insite', 'partner_contact',
                                    'partner_ref', 'payment_term', 'account_id',
                                    'currency_id', 'invoice_line', 'tax_line',
                                    'journal_id', 'period_id'],context=context)
                        invoice = invoice[0]
                        del invoice['id']
                        invoice_lines = self.pool.get('account.invoice.line').read(cr, uid, invoice['invoice_line'],context=context)
                        invoice_lines = inv_obj._refund_cleanup_lines(cr, uid, invoice_lines)
                        tax_lines = self.pool.get('account.invoice.tax').read(
                                                        cr, uid, invoice['tax_line'],context=context)
                        tax_lines = inv_obj._refund_cleanup_lines(cr, uid, tax_lines)

                        invoice.update({
                            'type': inv.type,
                            'date_invoice': date,
                            'state': 'draft',
                            'number': False,
                            'invoice_line': invoice_lines,
                            'tax_line': tax_lines,
                            'period_id': period,
                            'name': description
                            })

                        for field in ('address_contact_id', 'address_invoice_id', 'partner_id',
                                'account_id', 'currency_id', 'payment_term', 'journal_id'):
                                invoice[field] = invoice[field] and invoice[field][0]

                        inv_id = inv_obj.create(cr, uid, invoice, {})
                        if inv.payment_term.id:
                            data = inv_obj.onchange_payment_term_date_invoice(cr, uid, [inv_id], inv.payment_term.id, date)
                            if 'value' in data and data['value']:
                                inv_obj.write(cr, uid, [inv_id], data['value'])
                        created_inv.append(inv_id)

            if inv.type == 'out_invoice':
                xml_id = 'action_invoice_tree1'
            elif inv.type == 'in_invoice':
                xml_id = 'action_invoice_tree2'
            elif inv.type == 'out_refund':
                xml_id = 'action_invoice_tree3'
            else:
                xml_id = 'action_invoice_tree4'
            result = mod_obj._get_id(cr, uid, 'account', xml_id)
            id = mod_obj.read(cr, uid, result, ['res_id'],context=context)['res_id']
            result = act_obj.read(cr, uid, id,context=context)
            result['res_id'] = created_inv
            return result

    def invoice_refund(self, cr, uid, ids, context={}):
        return self.compute_refund(cr, uid, ids, 'refund', context=context)

    def invoice_cancel(self, cr, uid, ids, context={}):
        return self.compute_refund(cr, uid, ids, 'cancel', context=context)

    def invoice_modify(self, cr, uid, ids, context={}):
        return self.compute_refund(cr, uid, ids, 'modify', context=context)

account_invoice_refund()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: