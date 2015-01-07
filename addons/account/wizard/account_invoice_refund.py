# -*- coding: utf-8 -*-
import time

from openerp import models, fields, api, _
from openerp.exceptions import Warning

class account_invoice_refund(models.TransientModel):

    """Refunds invoice"""

    _name = "account.invoice.refund"
    _description = "Invoice Refund"

    date = fields.Date(string='Account Date', default=fields.Date.context_today)
    description = fields.Char(string='Reason', required=True, default=lambda self: self._get_reason())
    filter_refund = fields.Selection([('refund', 'Create a draft refund'), ('cancel', 'Cancel: create refund and reconcile'), ('modify', 'Modify: create refund, reconcile and create a new draft invoice')],
        default='refund', string='Refund Method', required=True, help='Refund base on this type. You can not Modify and Cancel if the invoice is already reconciled')

    @api.model
    def _get_reason(self):
        context = dict(self._context or {})
        active_id = context.get('active_id', False)
        if active_id:
            inv = self.env['account.invoice'].browse(active_id)
            return inv.name
        else:
            return ''

    @api.multi
    def compute_refund(self, mode='refund'):
        inv_obj = self.env['account.invoice']
        account_m_line_obj = self.env['account.move.line']
        act_obj = self.env['ir.actions.act_window']
        inv_tax_obj = self.env['account.invoice.tax']
        inv_line_obj = self.env['account.invoice.line']
        context = dict(self._context or {})
        cr = self._cr
        xml_id = False

        for form in self:
            created_inv = []
            date = False
            description = False
            company = self.env.user.company_id
            for inv in inv_obj.browse(context.get('active_ids')):
                if inv.state in ['draft', 'proforma2', 'cancel']:
                    raise Warning(_('Cannot %s draft/proforma/cancel invoice.') % (mode))
                if inv.reconciled and mode in ('cancel', 'modify'):
                    raise Warning(_('Cannot %s invoice which is already reconciled, invoice should be unreconciled first. You can only refund this invoice.') % (mode))
                if form.date:
                    date = form.date
                else:
                    date = inv.date or False

                journal_id = inv.journal_id.id

                if form.date:
                    date = form.date
                else:
                    date = inv.date_invoice
                if form.description:
                    description = form.description
                else:
                    description = inv.name

                if not date:
                    raise Warning(_('No period date found on the invoice.'))

                refund = inv.refund(date, date, description, journal_id)
                refund.write({'date_due': date, 'check_total': inv.check_total})
                refund.compute_amount()

                created_inv.append(refund.id)
                if mode in ('cancel', 'modify'):
                    movelines = inv.move_id.line_id
                    to_reconcile_ids = {}
                    for line in movelines:
                        if line.account_id.id == inv.account_id.id:
                            to_reconcile_ids.setdefault(line.account_id.id, []).append(line.id)
                        if line.reconciled:
                            line.remove_move_reconcile()
                    refund.signal_workflow('invoice_open')
                    for tmpline in  refund.move_id.line_id:
                        if tmpline.account_id.id == inv.account_id.id:
                            tmpline.reconcile(writeoff_journal_id = inv.journal_id,
                                            writeoff_acc_id=inv.account_id
                                            )
                    if mode == 'modify':
                        invoice = inv.read(
                                    ['name', 'type', 'number', 'reference',
                                    'comment', 'date_due', 'partner_id',
                                    'partner_insite', 'partner_contact',
                                    'partner_ref', 'payment_term', 'account_id',
                                    'currency_id', 'invoice_line', 'tax_line',
                                    'journal_id', 'date'])
                        invoice = invoice[0]
                        del invoice['id']
                        invoice_lines = inv_line_obj.browse(invoice['invoice_line'])
                        invoice_lines = inv_obj._refund_cleanup_lines(invoice_lines)
                        tax_lines = inv_tax_obj.browse(invoice['tax_line'])
                        tax_lines = inv_obj._refund_cleanup_lines(tax_lines)
                        invoice.update({
                            'type': inv.type,
                            'date_invoice': date,
                            'state': 'draft',
                            'number': False,
                            'invoice_line': invoice_lines,
                            'tax_line': tax_lines,
                            'date': date,
                            'name': description
                        })
                        for field in ('partner_id', 'account_id', 'currency_id',
                                         'payment_term', 'journal_id'):
                                invoice[field] = invoice[field] and invoice[field][0]
                        inv_id = inv_obj.create(invoice)
                        if inv.payment_term.id:
                            data = inv_id.onchange_payment_term_date_invoice(inv.payment_term.id, date)
                            if 'value' in data and data['value']:
                                inv_id.write(data['value'])
                        created_inv.append(inv_id.id)
                xml_id = (inv.type == 'out_refund') and 'action_invoice_tree1' or \
                         (inv.type == 'in_refund') and 'action_invoice_tree2' or \
                         (inv.type == 'out_invoice') and 'action_invoice_tree3' or \
                         (inv.type == 'in_invoice') and 'action_invoice_tree4'
        if xml_id:
            result = self.env.ref('account.%s' % (xml_id)).read()[0]
            invoice_domain = eval(result['domain'])
            invoice_domain.append(('id', 'in', created_inv))
            result['domain'] = invoice_domain
            return result
        return True

    @api.multi
    def invoice_refund(self):
        data_refund = self.read(['filter_refund'])[0]['filter_refund']
        return self.compute_refund(data_refund)
