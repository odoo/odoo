# -*- coding: utf-8 -*-
import time

from openerp import models, fields, api, _
from openerp.exceptions import Warning

class account_invoice_refund(models.TransientModel):

    """Refunds invoice"""

    _name = "account.invoice.refund"
    _description = "Invoice Refund"

    date = fields.Date(string='Date', help='This date will be used as the invoice date for credit note and period will be chosen accordingly!',
        default=lambda *a: time.strftime('%Y-%m-%d'))
    period = fields.Many2one('account.period', string='Force period')
    journal_id = fields.Many2one('account.journal', string='Refund Journal', default=lambda self: self._get_journal(),
        help='You can select here the journal to use for the credit note that will be created. If you leave that field empty, it will use the same journal as the current invoice.')
    description = fields.Char(string='Reason', required=True, default=lambda self: self._get_reason())
    filter_refund = fields.Selection([('refund', 'Create a draft refund'), ('cancel', 'Cancel: create refund and reconcile'), ('modify', 'Modify: create refund, reconcile and create a new draft invoice')],
        default='refund', string='Refund Method', required=True, help='Refund base on this type. You can not Modify and Cancel if the invoice is already reconciled')

    @api.model
    def _get_journal(self):
        context = dict(self._context or {})
        inv_type = context.get('type', 'out_invoice')
        type = (inv_type == 'out_invoice') and 'sale_refund' or \
               (inv_type == 'out_refund') and 'sale' or \
               (inv_type == 'in_invoice') and 'purchase_refund' or \
               (inv_type == 'in_refund') and 'purchase'
        journal = self.env['account.journal'].search([('type', '=', type), ('company_id', '=', self.env.user.company_id.id)], limit=1)
        return journal

    @api.model
    def _get_reason(self):
        context = dict(self._context or {})
        active_id = context.get('active_id', False)
        if active_id:
            inv = self.env['account.invoice'].browse(active_id)
            return inv.name
        else:
            return ''

    @api.model
    def fields_view_get(self, view_id=None, view_type=False, toolbar=False, submenu=False):
        journal_obj = self.env['account.journal']
        # remove the entry with key 'form_view_ref', otherwise fields_view_get crashes
        context = dict(self._context or {})
        context.pop('form_view_ref', None)
        res = super(account_invoice_refund, self).fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar, submenu=submenu)
        type = context.get('type', 'out_invoice')
        company_id = self.env.user.company_id.id
        journal_type = (type == 'out_invoice') and 'sale_refund' or \
                       (type == 'out_refund') and 'sale' or \
                       (type == 'in_invoice') and 'purchase_refund' or \
                       (type == 'in_refund') and 'purchase'
        for field in res['fields']:
            if field == 'journal_id':
                journal_select = journal_obj._name_search('', [('type', '=', journal_type), ('company_id', 'child_of', [company_id])])
                res['fields'][field]['selection'] = journal_select
        return res

    @api.multi
    def compute_refund(self, mode='refund'):
        inv_obj = self.env['account.invoice']
        account_m_line_obj = self.env['account.move.line']
        act_obj = self.env['ir.actions.act_window']
        inv_tax_obj = self.env['account.invoice.tax']
        inv_line_obj = self.env['account.invoice.line']
        context = dict(self._context or {})
        cr = self._cr

        for form in self:
            created_inv = []
            date = False
            period = False
            description = False
            company = self.env.user.company_id
            journal_id = form.journal_id.id
            for inv in inv_obj.browse(context.get('active_ids')):
                if inv.state in ['draft', 'proforma2', 'cancel']:
                    raise Warning(_('Cannot %s draft/proforma/cancel invoice.') % (mode))
                if inv.reconciled and mode in ('cancel', 'modify'):
                    raise Warning(_('Cannot %s invoice which is already reconciled, invoice should be unreconciled first. You can only refund this invoice.') % (mode))
                if form.period.id:
                    period = form.period.id
                else:
                    period = inv.period_id and inv.period_id.id or False

                if not journal_id:
                    journal_id = inv.journal_id.id

                if form.date:
                    date = form.date
                    if not form.period.id:
                            cr.execute("select name from ir_model_fields \
                                            where model = 'account.period' \
                                            and name = 'company_id'")
                            result_query = cr.fetchone()
                            if result_query:
                                cr.execute("""select p.id from account_fiscalyear y, account_period p where y.id=p.fiscalyear_id \
                                    and date(%s) between p.date_start AND p.date_stop and y.company_id = %s limit 1""", (date, company.id,))
                            else:
                                cr.execute("""SELECT id
                                        from account_period where date(%s)
                                        between date_start AND  date_stop  \
                                        limit 1 """, (date,))
                            res = cr.fetchone()
                            if res:
                                period = res[0]
                else:
                    date = inv.date_invoice
                if form.description:
                    description = form.description
                else:
                    description = inv.name

                if not period:
                    raise Warning(_('No period found on the invoice.'))

                refund = inv.refund(date, period, description, journal_id)
                refund.write({'date_due': date, 'check_total': inv.check_total})
                refund.button_compute()

                created_inv.append(refund.id)
                if mode in ('cancel', 'modify'):
                    movelines = inv.move_id.line_id
                    to_reconcile_ids = {}
                    for line in movelines:
                        if line.account_id.id == inv.account_id.id:
                            to_reconcile_ids.setdefault(line.account_id.id, []).append(line.id)
                        if line.reconcile_id:
                            line.reconcile_id.unlink()
                    refund.signal_workflow('invoice_open')
                    for tmpline in  refund.move_id.line_id:
                        if tmpline.account_id.id == inv.account_id.id:
                            to_reconcile_ids[tmpline.account_id.id].append(tmpline.id)
                    for account in to_reconcile_ids:
                        account_m_line_obj.reconcile(cr, uid, to_reconcile_ids[account],
                                        writeoff_period_id=period,
                                        writeoff_journal_id = inv.journal_id.id,
                                        writeoff_acc_id=inv.account_id.id
                                        )
                    if mode == 'modify':
                        invoice = inv.read(
                                    ['name', 'type', 'number', 'reference',
                                    'comment', 'date_due', 'partner_id',
                                    'partner_insite', 'partner_contact',
                                    'partner_ref', 'payment_term', 'account_id',
                                    'currency_id', 'invoice_line', 'tax_line',
                                    'journal_id', 'period_id'], context=context)
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
                            'period_id': period,
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
            result = self.env.ref('account.%s' %(xml_id))

            result = result.read()[0]
            invoice_domain = eval(result['domain'])
            invoice_domain.append(('id', 'in', created_inv))
            result['domain'] = invoice_domain
            return result

    @api.multi
    def invoice_refund(self):
        data_refund = self.read(['filter_refund'])[0]['filter_refund']
        return self.compute_refund(data_refund)
