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

import itertools
from lxml import etree

from openerp import models, fields, api, _
from openerp.exceptions import except_orm, Warning, RedirectWarning
import openerp.addons.decimal_precision as dp

# mapping invoice type to journal type
TYPE2JOURNAL = {
    'out_invoice': 'sale',
    'in_invoice': 'purchase',
    'out_refund': 'sale_refund',
    'in_refund': 'purchase_refund',
}

# mapping invoice type to refund type
TYPE2REFUND = {
    'out_invoice': 'out_refund',        # Customer Invoice
    'in_invoice': 'in_refund',          # Supplier Invoice
    'out_refund': 'out_invoice',        # Customer Refund
    'in_refund': 'in_invoice',          # Supplier Refund
}

MAGIC_COLUMNS = ('id', 'create_uid', 'create_date', 'write_uid', 'write_date')


class account_invoice(models.Model):
    _name = "account.invoice"
    _inherit = ['mail.thread']
    _description = "Invoice"
    _order = "number desc, id desc"
    _track = {
        'type': {
        },
        'state': {
            'account.mt_invoice_paid': lambda self, cr, uid, obj, ctx=None: obj.state == 'paid' and obj.type in ('out_invoice', 'out_refund'),
            'account.mt_invoice_validated': lambda self, cr, uid, obj, ctx=None: obj.state == 'open' and obj.type in ('out_invoice', 'out_refund'),
        },
    }

    @api.one
    @api.depends('invoice_line.price_subtotal', 'tax_line.amount')
    def _compute_amount(self):
        self.amount_untaxed = sum(line.price_subtotal for line in self.invoice_line)
        self.amount_tax = sum(line.amount for line in self.tax_line)
        self.amount_total = self.amount_untaxed + self.amount_tax

    @api.model
    def _default_journal(self):
        inv_type = self._context.get('type', 'out_invoice')
        inv_types = inv_type if isinstance(inv_type, list) else [inv_type]
        company_id = self._context.get('company_id', self.env.user.company_id.id)
        domain = [
            ('type', 'in', filter(None, map(TYPE2JOURNAL.get, inv_types))),
            ('company_id', '=', company_id),
        ]
        return self.env['account.journal'].search(domain, limit=1)

    @api.model
    def _default_currency(self):
        journal = self._default_journal()
        return journal.currency or journal.company_id.currency_id

    @api.model
    @api.returns('account.analytic.journal')
    def _get_journal_analytic(self, inv_type):
        """ Return the analytic journal corresponding to the given invoice type. """
        journal_type = TYPE2JOURNAL.get(inv_type, 'sale')
        journal = self.env['account.analytic.journal'].search([('type', '=', journal_type)], limit=1)
        if not journal:
            raise except_orm(_('No Analytic Journal!'),
                _("You must define an analytic journal of type '%s'!") % (journal_type,))
        return journal

    @api.one
    @api.depends('account_id', 'move_id.line_id.account_id', 'move_id.line_id.reconcile_id')
    def _compute_reconciled(self):
        self.reconciled = self.test_paid()
        if not self.reconciled and self.state == 'paid':
            self.signal_open_test()

    @api.model
    def _get_reference_type(self):
        return [('none', _('Free Reference'))]

    @api.one
    @api.depends(
        'state', 'currency_id', 'invoice_line.price_subtotal',
        'move_id.line_id.account_id.type',
        'move_id.line_id.amount_residual',
        'move_id.line_id.amount_residual_currency',
        'move_id.line_id.currency_id',
        'move_id.line_id.reconcile_partial_id.line_partial_ids.invoice.type',
    )
    def _compute_residual(self):
        nb_inv_in_partial_rec = max_invoice_id = 0
        self.residual = 0.0
        for line in self.move_id.line_id:
            if line.account_id.type in ('receivable', 'payable'):
                if line.currency_id == self.currency_id:
                    self.residual += line.amount_residual_currency
                else:
                    # ahem, shouldn't we use line.currency_id here?
                    from_currency = line.company_id.currency_id.with_context(date=line.date)
                    self.residual += from_currency.compute(line.amount_residual, self.currency_id)
                # we check if the invoice is partially reconciled and if there
                # are other invoices involved in this partial reconciliation
                for pline in line.reconcile_partial_id.line_partial_ids:
                    if pline.invoice and self.type == pline.invoice.type:
                        nb_inv_in_partial_rec += 1
                        # store the max invoice id as for this invoice we will
                        # make a balance instead of a simple division
                        max_invoice_id = max(max_invoice_id, pline.invoice.id)
        if nb_inv_in_partial_rec:
            # if there are several invoices in a partial reconciliation, we
            # split the residual by the number of invoices to have a sum of
            # residual amounts that matches the partner balance
            new_value = self.currency_id.round(self.residual / nb_inv_in_partial_rec)
            if self.id == max_invoice_id:
                # if it's the last the invoice of the bunch of invoices
                # partially reconciled together, we make a balance to avoid
                # rounding errors
                self.residual = self.residual - ((nb_inv_in_partial_rec - 1) * new_value)
            else:
                self.residual = new_value
        # prevent the residual amount on the invoice to be less than 0
        self.residual = max(self.residual, 0.0)            

    @api.one
    @api.depends(
        'move_id.line_id.account_id',
        'move_id.line_id.reconcile_id.line_id',
        'move_id.line_id.reconcile_partial_id.line_partial_ids',
    )
    def _compute_move_lines(self):
        # Give Journal Items related to the payment reconciled to this invoice.
        # Return partial and total payments related to the selected invoice.
        self.move_lines = self.env['account.move.line']
        if not self.move_id:
            return
        data_lines = self.move_id.line_id.filtered(lambda l: l.account_id == self.account_id)
        partial_lines = self.env['account.move.line']
        for data_line in data_lines:
            if data_line.reconcile_id:
                lines = data_line.reconcile_id.line_id
            elif data_line.reconcile_partial_id:
                lines = data_line.reconcile_partial_id.line_partial_ids
            else:
                lines = self.env['account_move_line']
            partial_lines += data_line
            self.move_lines = lines - partial_lines

    @api.one
    @api.depends(
        'move_id.line_id.reconcile_id.line_id',
        'move_id.line_id.reconcile_partial_id.line_partial_ids',
    )
    def _compute_payments(self):
        partial_lines = lines = self.env['account.move.line']
        for line in self.move_id.line_id:
            if line.reconcile_id:
                lines |= line.reconcile_id.line_id
            elif line.reconcile_partial_id:
                lines |= line.reconcile_partial_id.line_partial_ids
            partial_lines += line
        self.payment_ids = (lines - partial_lines).sorted()

    name = fields.Char(string='Reference/Description', index=True,
        readonly=True, states={'draft': [('readonly', False)]})
    origin = fields.Char(string='Source Document',
        help="Reference of the document that produced this invoice.",
        readonly=True, states={'draft': [('readonly', False)]})
    supplier_invoice_number = fields.Char(string='Supplier Invoice Number',
        help="The reference of this invoice as provided by the supplier.",
        readonly=True, states={'draft': [('readonly', False)]})
    type = fields.Selection([
            ('out_invoice','Customer Invoice'),
            ('in_invoice','Supplier Invoice'),
            ('out_refund','Customer Refund'),
            ('in_refund','Supplier Refund'),
        ], string='Type', readonly=True, index=True, change_default=True,
        default=lambda self: self._context.get('type', 'out_invoice'),
        track_visibility='always')

    number = fields.Char(related='move_id.name', store=True, readonly=True, copy=False)
    internal_number = fields.Char(string='Invoice Number', readonly=True,
        default=False, copy=False,
        help="Unique number of the invoice, computed automatically when the invoice is created.")
    reference = fields.Char(string='Invoice Reference',
        help="The partner reference of this invoice.")
    reference_type = fields.Selection('_get_reference_type', string='Payment Reference',
        required=True, readonly=True, states={'draft': [('readonly', False)]},
        default='none')
    comment = fields.Text('Additional Information')

    state = fields.Selection([
            ('draft','Draft'),
            ('proforma','Pro-forma'),
            ('proforma2','Pro-forma'),
            ('open','Open'),
            ('paid','Paid'),
            ('cancel','Cancelled'),
        ], string='Status', index=True, readonly=True, default='draft',
        track_visibility='onchange', copy=False,
        help=" * The 'Draft' status is used when a user is encoding a new and unconfirmed Invoice.\n"
             " * The 'Pro-forma' when invoice is in Pro-forma status,invoice does not have an invoice number.\n"
             " * The 'Open' status is used when user create invoice,a invoice number is generated.Its in open status till user does not pay invoice.\n"
             " * The 'Paid' status is set automatically when the invoice is paid. Its related journal entries may or may not be reconciled.\n"
             " * The 'Cancelled' status is used when user cancel invoice.")
    sent = fields.Boolean(readonly=True, default=False, copy=False,
        help="It indicates that the invoice has been sent.")
    date_invoice = fields.Date(string='Invoice Date',
        readonly=True, states={'draft': [('readonly', False)]}, index=True,
        help="Keep empty to use the current date", copy=False)
    date_due = fields.Date(string='Due Date',
        readonly=True, states={'draft': [('readonly', False)]}, index=True, copy=False,
        help="If you use payment terms, the due date will be computed automatically at the generation "
             "of accounting entries. The payment term may compute several due dates, for example 50% "
             "now and 50% in one month, but if you want to force a due date, make sure that the payment "
             "term is not set on the invoice. If you keep the payment term and the due date empty, it "
             "means direct payment.")
    partner_id = fields.Many2one('res.partner', string='Partner', change_default=True,
        required=True, readonly=True, states={'draft': [('readonly', False)]},
        track_visibility='always')
    payment_term = fields.Many2one('account.payment.term', string='Payment Terms',
        readonly=True, states={'draft': [('readonly', False)]},
        help="If you use payment terms, the due date will be computed automatically at the generation "
             "of accounting entries. If you keep the payment term and the due date empty, it means direct payment. "
             "The payment term may compute several due dates, for example 50% now, 50% in one month.")
    period_id = fields.Many2one('account.period', string='Force Period',
        domain=[('state', '!=', 'done')], copy=False,
        help="Keep empty to use the period of the validation(invoice) date.",
        readonly=True, states={'draft': [('readonly', False)]})

    account_id = fields.Many2one('account.account', string='Account',
        required=True, readonly=True, states={'draft': [('readonly', False)]},
        help="The partner account used for this invoice.")
    invoice_line = fields.One2many('account.invoice.line', 'invoice_id', string='Invoice Lines',
        readonly=True, states={'draft': [('readonly', False)]}, copy=True)
    tax_line = fields.One2many('account.invoice.tax', 'invoice_id', string='Tax Lines',
        readonly=True, states={'draft': [('readonly', False)]}, copy=True)
    move_id = fields.Many2one('account.move', string='Journal Entry',
        readonly=True, index=True, ondelete='restrict', copy=False,
        help="Link to the automatically generated Journal Items.")

    amount_untaxed = fields.Float(string='Subtotal', digits=dp.get_precision('Account'),
        store=True, readonly=True, compute='_compute_amount', track_visibility='always')
    amount_tax = fields.Float(string='Tax', digits=dp.get_precision('Account'),
        store=True, readonly=True, compute='_compute_amount')
    amount_total = fields.Float(string='Total', digits=dp.get_precision('Account'),
        store=True, readonly=True, compute='_compute_amount')

    currency_id = fields.Many2one('res.currency', string='Currency',
        required=True, readonly=True, states={'draft': [('readonly', False)]},
        default=_default_currency, track_visibility='always')
    journal_id = fields.Many2one('account.journal', string='Journal',
        required=True, readonly=True, states={'draft': [('readonly', False)]},
        default=_default_journal,
        domain="[('type', 'in', {'out_invoice': ['sale'], 'out_refund': ['sale_refund'], 'in_refund': ['purchase_refund'], 'in_invoice': ['purchase']}.get(type, [])), ('company_id', '=', company_id)]")
    company_id = fields.Many2one('res.company', string='Company', change_default=True,
        required=True, readonly=True, states={'draft': [('readonly', False)]},
        default=lambda self: self.env['res.company']._company_default_get('account.invoice'))
    check_total = fields.Float(string='Verification Total', digits=dp.get_precision('Account'),
        readonly=True, states={'draft': [('readonly', False)]}, default=0.0)

    reconciled = fields.Boolean(string='Paid/Reconciled',
        store=True, readonly=True, compute='_compute_reconciled',
        help="It indicates that the invoice has been paid and the journal entry of the invoice has been reconciled with one or several journal entries of payment.")
    partner_bank_id = fields.Many2one('res.partner.bank', string='Bank Account',
        help='Bank Account Number to which the invoice will be paid. A Company bank account if this is a Customer Invoice or Supplier Refund, otherwise a Partner bank account number.',
        readonly=True, states={'draft': [('readonly', False)]})

    move_lines = fields.Many2many('account.move.line', string='Entry Lines',
        compute='_compute_move_lines')
    residual = fields.Float(string='Balance', digits=dp.get_precision('Account'),
        compute='_compute_residual', store=True,
        help="Remaining amount due.")
    payment_ids = fields.Many2many('account.move.line', string='Payments',
        compute='_compute_payments')
    move_name = fields.Char(string='Journal Entry', readonly=True,
        states={'draft': [('readonly', False)]}, copy=False)
    user_id = fields.Many2one('res.users', string='Salesperson', track_visibility='onchange',
        readonly=True, states={'draft': [('readonly', False)]},
        default=lambda self: self.env.user)
    fiscal_position = fields.Many2one('account.fiscal.position', string='Fiscal Position',
        readonly=True, states={'draft': [('readonly', False)]})
    commercial_partner_id = fields.Many2one('res.partner', string='Commercial Entity',
        related='partner_id.commercial_partner_id', store=True, readonly=True,
        help="The commercial entity that will be used on Journal Entries for this invoice")

    _sql_constraints = [
        ('number_uniq', 'unique(number, company_id, journal_id, type)',
            'Invoice Number must be unique per Company!'),
    ]

    @api.model
    def fields_view_get(self, view_id=None, view_type=False, toolbar=False, submenu=False):
        context = self._context
        if context.get('active_model') == 'res.partner' and context.get('active_ids'):
            partner = self.env['res.partner'].browse(context['active_ids'])[0]
            if not view_type:
                view_id = self.env['ir.ui.view'].search([('name', '=', 'account.invoice.tree')]).id
                view_type = 'tree'
            elif view_type == 'form':
                if partner.supplier and not partner.customer:
                    view_id = self.env['ir.ui.view'].search([('name', '=', 'account.invoice.supplier.form')]).id
                elif partner.customer and not partner.supplier:
                    view_id = self.env['ir.ui.view'].search([('name', '=', 'account.invoice.form')]).id

        res = super(account_invoice, self).fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar, submenu=submenu)

        # adapt selection of field journal_id
        for field in res['fields']:
            if field == 'journal_id' and type:
                journal_select = self.env['account.journal']._name_search('', [('type', '=', type)], name_get_uid=1)
                res['fields'][field]['selection'] = journal_select

        doc = etree.XML(res['arch'])

        if context.get('type'):
            for node in doc.xpath("//field[@name='partner_bank_id']"):
                if context['type'] == 'in_refund':
                    node.set('domain', "[('partner_id.ref_companies', 'in', [company_id])]")
                elif context['type'] == 'out_refund':
                    node.set('domain', "[('partner_id', '=', partner_id)]")

        if view_type == 'search':
            if context.get('type') in ('out_invoice', 'out_refund'):
                for node in doc.xpath("//group[@name='extended filter']"):
                    doc.remove(node)

        if view_type == 'tree':
            partner_string = _('Customer')
            if context.get('type') in ('in_invoice', 'in_refund'):
                partner_string = _('Supplier')
                for node in doc.xpath("//field[@name='reference']"):
                    node.set('invisible', '0')
            for node in doc.xpath("//field[@name='partner_id']"):
                node.set('string', partner_string)

        res['arch'] = etree.tostring(doc)
        return res

    @api.multi
    def invoice_print(self):
        """ Print the invoice and mark it as sent, so that we can see more
            easily the next step of the workflow
        """
        assert len(self) == 1, 'This option should only be used for a single id at a time.'
        self.sent = True
        return self.env['report'].get_action(self, 'account.report_invoice')

    @api.multi
    def action_invoice_sent(self):
        """ Open a window to compose an email, with the edi invoice template
            message loaded by default
        """
        assert len(self) == 1, 'This option should only be used for a single id at a time.'
        template = self.env.ref('account.email_template_edi_invoice', False)
        compose_form = self.env.ref('mail.email_compose_message_wizard_form', False)
        ctx = dict(self._context,
            default_model='account.invoice',
            default_res_id=self.id,
            default_use_template=bool(template),
            default_template_id=template.id,
            default_composition_mode='comment',
            mark_invoice_as_sent=True,
        )
        return {
            'name': _('Compose Email'),
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'mail.compose.message',
            'views': [(compose_form.id, 'form')],
            'view_id': compose_form.id,
            'target': 'new',
            'context': ctx,
        }

    @api.multi
    def confirm_paid(self):
        return self.write({'state': 'paid'})

    @api.multi
    def unlink(self):
        for invoice in self:
            if invoice.state not in ('draft', 'cancel'):
                raise Warning(_('You cannot delete an invoice which is not draft or cancelled. You should refund it instead.'))
            elif invoice.internal_number:
                raise Warning(_('You cannot delete an invoice after it has been validated (and received a number).  You can set it back to "Draft" state and modify its content, then re-confirm it.'))
        return super(account_invoice, self).unlink()

    @api.multi
    def onchange_partner_id(self, type, partner_id, date_invoice=False,
            payment_term=False, partner_bank_id=False, company_id=False):
        account_id = False
        payment_term_id = False
        fiscal_position = False
        bank_id = False

        if partner_id:
            p = self.env['res.partner'].browse(partner_id)
            rec_account = p.property_account_receivable
            pay_account = p.property_account_payable
            if company_id:
                if p.property_account_receivable.company_id and \
                        p.property_account_receivable.company_id.id != company_id and \
                        p.property_account_payable.company_id and \
                        p.property_account_payable.company_id.id != company_id:
                    prop = self.env['ir.property']
                    rec_dom = [('name', '=', 'property_account_receivable'), ('company_id', '=', company_id)]
                    pay_dom = [('name', '=', 'property_account_payable'), ('company_id', '=', company_id)]
                    res_dom = [('res_id', '=', 'res.partner,%s' % partner_id)]
                    rec_prop = prop.search(rec_dom + res_dom) or prop.search(rec_dom)
                    pay_prop = prop.search(pay_dom + res_dom) or prop.search(pay_dom)
                    rec_account = rec_prop.get_by_record(rec_prop)
                    pay_account = pay_prop.get_by_record(pay_prop)
                    if not rec_account and not pay_account:
                        action = self.env.ref('account.action_account_config')
                        msg = _('Cannot find a chart of accounts for this company, You should configure it. \nPlease go to Account Configuration.')
                        raise RedirectWarning(msg, action.id, _('Go to the configuration panel'))

            if type in ('out_invoice', 'out_refund'):
                account_id = rec_account.id
                payment_term_id = p.property_payment_term.id
            else:
                account_id = pay_account.id
                payment_term_id = p.property_supplier_payment_term.id
            fiscal_position = p.property_account_position.id
            bank_id = p.bank_ids.id

        result = {'value': {
            'account_id': account_id,
            'payment_term': payment_term_id,
            'fiscal_position': fiscal_position,
        }}

        if type in ('in_invoice', 'in_refund'):
            result['value']['partner_bank_id'] = bank_id

        if payment_term != payment_term_id:
            if payment_term_id:
                to_update = self.onchange_payment_term_date_invoice(payment_term_id, date_invoice)
                result['value'].update(to_update.get('value', {}))
            else:
                result['value']['date_due'] = False

        if partner_bank_id != bank_id:
            to_update = self.onchange_partner_bank(bank_id)
            result['value'].update(to_update.get('value', {}))

        return result

    @api.multi
    def onchange_journal_id(self, journal_id=False):
        if journal_id:
            journal = self.env['account.journal'].browse(journal_id)
            return {
                'value': {
                    'currency_id': journal.currency.id or journal.company_id.currency_id.id,
                    'company_id': journal.company_id.id,
                }
            }
        return {}

    @api.multi
    def onchange_payment_term_date_invoice(self, payment_term_id, date_invoice):
        if not date_invoice:
            date_invoice = fields.Date.today()
        if not payment_term_id:
            # To make sure the invoice due date should contain due date which is
            # entered by user when there is no payment term defined
            return {'value': {'date_due': self.date_due or date_invoice}}
        pterm = self.env['account.payment.term'].browse(payment_term_id)
        pterm_list = pterm.compute(value=1, date_ref=date_invoice)[0]
        if pterm_list:
            return {'value': {'date_due': max(line[0] for line in pterm_list)}}
        else:
            raise except_orm(_('Insufficient Data!'),
                _('The payment term of supplier does not have a payment term line.'))

    @api.multi
    def onchange_invoice_line(self, lines):
        return {}

    @api.multi
    def onchange_partner_bank(self, partner_bank_id=False):
        return {'value': {}}

    @api.multi
    def onchange_company_id(self, company_id, part_id, type, invoice_line, currency_id):
        # TODO: add the missing context parameter when forward-porting in trunk
        # so we can remove this hack!
        self = self.with_context(self.env['res.users'].context_get())

        values = {}
        domain = {}

        if company_id and part_id and type:
            p = self.env['res.partner'].browse(part_id)
            if p.property_account_payable and p.property_account_receivable and \
                    p.property_account_payable.company_id.id != company_id and \
                    p.property_account_receivable.company_id.id != company_id:
                prop = self.env['ir.property']
                rec_dom = [('name', '=', 'property_account_receivable'), ('company_id', '=', company_id)]
                pay_dom = [('name', '=', 'property_account_payable'), ('company_id', '=', company_id)]
                res_dom = [('res_id', '=', 'res.partner,%s' % part_id)]
                rec_prop = prop.search(rec_dom + res_dom) or prop.search(rec_dom)
                pay_prop = prop.search(pay_dom + res_dom) or prop.search(pay_dom)
                rec_account = rec_prop.get_by_record(rec_prop)
                pay_account = pay_prop.get_by_record(pay_prop)
                if not rec_account and not pay_account:
                    action = self.env.ref('account.action_account_config')
                    msg = _('Cannot find a chart of accounts for this company, You should configure it. \nPlease go to Account Configuration.')
                    raise RedirectWarning(msg, action.id, _('Go to the configuration panel'))

                if type in ('out_invoice', 'out_refund'):
                    acc_id = rec_account.id
                else:
                    acc_id = pay_account.id
                values= {'account_id': acc_id}

            if self:
                if company_id:
                    for line in self.invoice_line:
                        if not line.account_id:
                            continue
                        if line.account_id.company_id.id == company_id:
                            continue
                        accounts = self.env['account.account'].search([('name', '=', line.account_id.name), ('company_id', '=', company_id)])
                        if not accounts:
                            action = self.env.ref('account.action_account_config')
                            msg = _('Cannot find a chart of accounts for this company, You should configure it. \nPlease go to Account Configuration.')
                            raise RedirectWarning(msg, action.id, _('Go to the configuration panel'))
                        line.write({'account_id': accounts[-1].id})
            else:
                for line_cmd in invoice_line or []:
                    if len(line_cmd) >= 3 and isinstance(line_cmd[2], dict):
                        line = self.env['account.account'].browse(line_cmd[2]['account_id'])
                        if line.company_id.id != company_id:
                            raise except_orm(
                                _('Configuration Error!'),
                                _("Invoice line account's company and invoice's company does not match.")
                            )

        if company_id and type:
            journal_type = TYPE2JOURNAL[type]
            journals = self.env['account.journal'].search([('type', '=', journal_type), ('company_id', '=', company_id)])
            if journals:
                values['journal_id'] = journals[0].id
            journal_defaults = self.env['ir.values'].get_defaults_dict('account.invoice', 'type=%s' % type)
            if 'journal_id' in journal_defaults:
                values['journal_id'] = journal_defaults['journal_id']
            if not values.get('journal_id'):
                field_desc = journals.fields_get(['journal_id'])
                type_label = next(t for t, label in field_desc['journal_id']['selection'] if t == journal_type)
                action = self.env.ref('account.action_account_journal_form')
                msg = _('Cannot find any account journal of type "%s" for this company, You should create one.\n Please go to Journal Configuration') % type_label
                raise RedirectWarning(msg, action.id, _('Go to the configuration panel'))
            domain = {'journal_id':  [('id', 'in', journals.ids)]}

        return {'value': values, 'domain': domain}

    @api.multi
    def action_cancel_draft(self):
        # go from canceled state to draft state
        self.write({'state': 'draft'})
        self.delete_workflow()
        self.create_workflow()
        return True

    @api.one
    @api.returns('ir.ui.view')
    def get_formview_id(self):
        """ Update form view id of action to open the invoice """
        if self.type == 'in_invoice':
            return self.env.ref('account.invoice_supplier_form')
        else:
            return self.env.ref('account.invoice_form')

    @api.multi
    def move_line_id_payment_get(self):
        # return the move line ids with the same account as the invoice self
        if not self.id:
            return []
        query = """ SELECT l.id
                    FROM account_move_line l, account_invoice i
                    WHERE i.id = %s AND l.move_id = i.move_id AND l.account_id = i.account_id
                """
        self._cr.execute(query, (self.id,))
        return [row[0] for row in self._cr.fetchall()]

    @api.multi
    def test_paid(self):
        # check whether all corresponding account move lines are reconciled
        line_ids = self.move_line_id_payment_get()
        if not line_ids:
            return False
        query = "SELECT reconcile_id FROM account_move_line WHERE id IN %s"
        self._cr.execute(query, (tuple(line_ids),))
        return all(row[0] for row in self._cr.fetchall())

    @api.multi
    def button_reset_taxes(self):
        account_invoice_tax = self.env['account.invoice.tax']
        ctx = dict(self._context)
        for invoice in self:
            self._cr.execute("DELETE FROM account_invoice_tax WHERE invoice_id=%s AND manual is False", (invoice.id,))
            self.invalidate_cache()
            partner = invoice.partner_id
            if partner.lang:
                ctx['lang'] = partner.lang
            for taxe in account_invoice_tax.compute(invoice).values():
                account_invoice_tax.create(taxe)
        # dummy write on self to trigger recomputations
        return self.with_context(ctx).write({'invoice_line': []})

    @api.multi
    def button_compute(self, set_total=False):
        self.button_reset_taxes()
        for invoice in self:
            if set_total:
                invoice.check_total = invoice.amount_total
        return True

    @staticmethod
    def _convert_ref(ref):
        return (ref or '').replace('/','')

    @api.multi
    def _get_analytic_lines(self):
        """ Return a list of dict for creating analytic lines for self[0] """
        company_currency = self.company_id.currency_id
        sign = 1 if self.type in ('out_invoice', 'in_refund') else -1

        iml = self.env['account.invoice.line'].move_line_get(self.id)
        for il in iml:
            if il['account_analytic_id']:
                if self.type in ('in_invoice', 'in_refund'):
                    ref = self.reference
                else:
                    ref = self._convert_ref(self.number)
                if not self.journal_id.analytic_journal_id:
                    raise except_orm(_('No Analytic Journal!'),
                        _("You have to define an analytic journal on the '%s' journal!") % (self.journal_id.name,))
                currency = self.currency_id.with_context(date=self.date_invoice)
                il['analytic_lines'] = [(0,0, {
                    'name': il['name'],
                    'date': self.date_invoice,
                    'account_id': il['account_analytic_id'],
                    'unit_amount': il['quantity'],
                    'amount': currency.compute(il['price'], company_currency) * sign,
                    'product_id': il['product_id'],
                    'product_uom_id': il['uos_id'],
                    'general_account_id': il['account_id'],
                    'journal_id': self.journal_id.analytic_journal_id.id,
                    'ref': ref,
                })]
        return iml

    @api.multi
    def action_date_assign(self):
        for inv in self:
            res = inv.onchange_payment_term_date_invoice(inv.payment_term.id, inv.date_invoice)
            if res and res.get('value'):
                inv.write(res['value'])
        return True

    @api.multi
    def finalize_invoice_move_lines(self, move_lines):
        """ finalize_invoice_move_lines(move_lines) -> move_lines

            Hook method to be overridden in additional modules to verify and
            possibly alter the move lines to be created by an invoice, for
            special cases.
            :param move_lines: list of dictionaries with the account.move.lines (as for create())
            :return: the (possibly updated) final move_lines to create for this invoice
        """
        return move_lines

    @api.multi
    def check_tax_lines(self, compute_taxes):
        account_invoice_tax = self.env['account.invoice.tax']
        company_currency = self.company_id.currency_id
        if not self.tax_line:
            for tax in compute_taxes.values():
                account_invoice_tax.create(tax)
        else:
            tax_key = []
            for tax in self.tax_line:
                if tax.manual:
                    continue
                key = (tax.tax_code_id.id, tax.base_code_id.id, tax.account_id.id, tax.account_analytic_id.id)
                tax_key.append(key)
                if key not in compute_taxes:
                    raise except_orm(_('Warning!'), _('Global taxes defined, but they are not in invoice lines !'))
                base = compute_taxes[key]['base']
                if abs(base - tax.base) > company_currency.rounding:
                    raise except_orm(_('Warning!'), _('Tax base different!\nClick on compute to update the tax base.'))
            for key in compute_taxes:
                if key not in tax_key:
                    raise except_orm(_('Warning!'), _('Taxes are missing!\nClick on compute button.'))

    @api.multi
    def compute_invoice_totals(self, company_currency, ref, invoice_move_lines):
        total = 0
        total_currency = 0
        for line in invoice_move_lines:
            if self.currency_id != company_currency:
                currency = self.currency_id.with_context(date=self.date_invoice or fields.Date.today())
                line['currency_id'] = currency.id
                line['amount_currency'] = line['price']
                line['price'] = currency.compute(line['price'], company_currency)
            else:
                line['currency_id'] = False
                line['amount_currency'] = False
            line['ref'] = ref
            if self.type in ('out_invoice','in_refund'):
                total += line['price']
                total_currency += line['amount_currency'] or line['price']
                line['price'] = - line['price']
            else:
                total -= line['price']
                total_currency -= line['amount_currency'] or line['price']
        return total, total_currency, invoice_move_lines

    def inv_line_characteristic_hashcode(self, invoice_line):
        """Overridable hashcode generation for invoice lines. Lines having the same hashcode
        will be grouped together if the journal has the 'group line' option. Of course a module
        can add fields to invoice lines that would need to be tested too before merging lines
        or not."""
        return "%s-%s-%s-%s-%s" % (
            invoice_line['account_id'],
            invoice_line.get('tax_code_id', 'False'),
            invoice_line.get('product_id', 'False'),
            invoice_line.get('analytic_account_id', 'False'),
            invoice_line.get('date_maturity', 'False'),
        )

    def group_lines(self, iml, line):
        """Merge account move lines (and hence analytic lines) if invoice line hashcodes are equals"""
        if self.journal_id.group_invoice_lines:
            line2 = {}
            for x, y, l in line:
                tmp = self.inv_line_characteristic_hashcode(l)
                if tmp in line2:
                    am = line2[tmp]['debit'] - line2[tmp]['credit'] + (l['debit'] - l['credit'])
                    line2[tmp]['debit'] = (am > 0) and am or 0.0
                    line2[tmp]['credit'] = (am < 0) and -am or 0.0
                    line2[tmp]['tax_amount'] += l['tax_amount']
                    line2[tmp]['analytic_lines'] += l['analytic_lines']
                else:
                    line2[tmp] = l
            line = []
            for key, val in line2.items():
                line.append((0,0,val))
        return line

    @api.multi
    def action_move_create(self):
        """ Creates invoice related analytics and financial move lines """
        account_invoice_tax = self.env['account.invoice.tax']
        account_move = self.env['account.move']

        for inv in self:
            if not inv.journal_id.sequence_id:
                raise except_orm(_('Error!'), _('Please define sequence on the journal related to this invoice.'))
            if not inv.invoice_line:
                raise except_orm(_('No Invoice Lines!'), _('Please create some invoice lines.'))
            if inv.move_id:
                continue

            ctx = dict(self._context, lang=inv.partner_id.lang)
            date_invoice = inv.date_invoice or fields.Date.context_today(self)

            company_currency = inv.company_id.currency_id
            # create the analytical lines, one move line per invoice line
            iml = inv._get_analytic_lines()
            # check if taxes are all computed
            compute_taxes = account_invoice_tax.compute(inv)
            inv.check_tax_lines(compute_taxes)

            # I disabled the check_total feature
            group_check_total = self.env.ref('account.group_supplier_inv_check_total')
            if self.env.user in group_check_total.users:
                if inv.type in ('in_invoice', 'in_refund') and abs(inv.check_total - inv.amount_total) >= (inv.currency_id.rounding / 2.0):
                    raise except_orm(_('Bad Total!'), _('Please verify the price of the invoice!\nThe encoded total does not match the computed total.'))

            if inv.payment_term:
                total_fixed = total_percent = 0
                for line in inv.payment_term.line_ids:
                    if line.value == 'fixed':
                        total_fixed += line.value_amount
                    if line.value == 'procent':
                        total_percent += line.value_amount
                total_fixed = (total_fixed * 100) / (inv.amount_total or 1.0)
                if (total_fixed + total_percent) > 100:
                    raise except_orm(_('Error!'), _("Cannot create the invoice.\nThe related payment term is probably misconfigured as it gives a computed amount greater than the total invoiced amount. In order to avoid rounding issues, the latest line of your payment term must be of type 'balance'."))

            # one move line per tax line
            iml += account_invoice_tax.move_line_get(inv.id)

            if inv.type in ('in_invoice', 'in_refund'):
                ref = inv.reference
            else:
                ref = self._convert_ref(inv.number)

            diff_currency = inv.currency_id != company_currency
            # create one move line for the total and possibly adjust the other lines amount
            total, total_currency, iml = inv.with_context(ctx).compute_invoice_totals(company_currency, ref, iml)

            name = inv.name or inv.supplier_invoice_number or '/'
            totlines = []
            if inv.payment_term:
                totlines = inv.with_context(ctx).payment_term.compute(total, date_invoice)[0]
            if totlines:
                res_amount_currency = total_currency
                ctx['date'] = date_invoice
                for i, t in enumerate(totlines):
                    if inv.currency_id != company_currency:
                        amount_currency = company_currency.with_context(ctx).compute(t[1], inv.currency_id)
                    else:
                        amount_currency = False

                    # last line: add the diff
                    res_amount_currency -= amount_currency or 0
                    if i + 1 == len(totlines):
                        amount_currency += res_amount_currency

                    iml.append({
                        'type': 'dest',
                        'name': name,
                        'price': t[1],
                        'account_id': inv.account_id.id,
                        'date_maturity': t[0],
                        'amount_currency': diff_currency and amount_currency,
                        'currency_id': diff_currency and inv.currency_id.id,
                        'ref': ref,
                    })
            else:
                iml.append({
                    'type': 'dest',
                    'name': name,
                    'price': total,
                    'account_id': inv.account_id.id,
                    'date_maturity': inv.date_due,
                    'amount_currency': diff_currency and total_currency,
                    'currency_id': diff_currency and inv.currency_id.id,
                    'ref': ref
                })

            date = date_invoice

            part = self.env['res.partner']._find_accounting_partner(inv.partner_id)

            line = [(0, 0, self.line_get_convert(l, part.id, date)) for l in iml]
            line = inv.group_lines(iml, line)

            journal = inv.journal_id.with_context(ctx)
            if journal.centralisation:
                raise except_orm(_('User Error!'),
                        _('You cannot create an invoice on a centralized journal. Uncheck the centralized counterpart box in the related journal from the configuration menu.'))

            line = inv.finalize_invoice_move_lines(line)

            move_vals = {
                'ref': inv.reference or inv.name,
                'line_id': line,
                'journal_id': journal.id,
                'date': date,
                'narration': inv.comment,
                'company_id': inv.company_id.id,
            }
            ctx['company_id'] = inv.company_id.id
            period = inv.period_id
            if not period:
                period = period.with_context(ctx).find(date_invoice)[:1]
            if period:
                move_vals['period_id'] = period.id
                for i in line:
                    i[2]['period_id'] = period.id

            ctx['invoice'] = inv
            move = account_move.with_context(ctx).create(move_vals)
            # make the invoice point to that move
            vals = {
                'date_invoice': date_invoice,
                'move_id': move.id,
                'period_id': period.id,
                'move_name': move.name,
            }
            inv.with_context(ctx).write(vals)
            # Pass invoice in context in method post: used if you want to get the same
            # account move reference when creating the same invoice after a cancelled one:
            move.post()
        self._log_event()
        return True

    @api.multi
    def invoice_validate(self):
        return self.write({'state': 'open'})

    @api.model
    def line_get_convert(self, line, part, date):
        return {
            'date_maturity': line.get('date_maturity', False),
            'partner_id': part,
            'name': line['name'][:64],
            'date': date,
            'debit': line['price']>0 and line['price'],
            'credit': line['price']<0 and -line['price'],
            'account_id': line['account_id'],
            'analytic_lines': line.get('analytic_lines', []),
            'amount_currency': line['price']>0 and abs(line.get('amount_currency', False)) or -abs(line.get('amount_currency', False)),
            'currency_id': line.get('currency_id', False),
            'tax_code_id': line.get('tax_code_id', False),
            'tax_amount': line.get('tax_amount', False),
            'ref': line.get('ref', False),
            'quantity': line.get('quantity',1.00),
            'product_id': line.get('product_id', False),
            'product_uom_id': line.get('uos_id', False),
            'analytic_account_id': line.get('account_analytic_id', False),
        }

    @api.multi
    def action_number(self):
        #TODO: not correct fix but required a fresh values before reading it.
        self.write({})

        for inv in self:
            self.write({'internal_number': inv.number})

            if inv.type in ('in_invoice', 'in_refund'):
                if not inv.reference:
                    ref = self._convert_ref(inv.number)
                else:
                    ref = inv.reference
            else:
                ref = self._convert_ref(inv.number)

            self._cr.execute(""" UPDATE account_move SET ref=%s
                           WHERE id=%s AND (ref IS NULL OR ref = '')""",
                        (ref, inv.move_id.id))
            self._cr.execute(""" UPDATE account_move_line SET ref=%s
                           WHERE move_id=%s AND (ref IS NULL OR ref = '')""",
                        (ref, inv.move_id.id))
            self._cr.execute(""" UPDATE account_analytic_line SET ref=%s
                           FROM account_move_line
                           WHERE account_move_line.move_id = %s AND
                                 account_analytic_line.move_id = account_move_line.id""",
                        (ref, inv.move_id.id))
            self.invalidate_cache()

        return True

    @api.multi
    def action_cancel(self):
        moves = self.env['account.move']
        for inv in self:
            if inv.move_id:
                moves += inv.move_id
            if inv.payment_ids:
                for move_line in inv.payment_ids:
                    if move_line.reconcile_partial_id.line_partial_ids:
                        raise except_orm(_('Error!'), _('You cannot cancel an invoice which is partially paid. You need to unreconcile related payment entries first.'))

        # First, set the invoices as cancelled and detach the move ids
        self.write({'state': 'cancel', 'move_id': False})
        if moves:
            # second, invalidate the move(s)
            moves.button_cancel()
            # delete the move this invoice was pointing to
            # Note that the corresponding move_lines and move_reconciles
            # will be automatically deleted too
            moves.unlink()
        self._log_event(-1.0, 'Cancel Invoice')
        return True

    ###################

    @api.multi
    def _log_event(self, factor=1.0, name='Open Invoice'):
        #TODO: implement messages system
        return True

    @api.one
    def _compute_display_name(self):
        TYPES = {
            'out_invoice': _('Invoice'),
            'in_invoice': _('Supplier Invoice'),
            'out_refund': _('Refund'),
            'in_refund': _('Supplier Refund'),
        }
        self.display_name = "%s %s" % (self.number or TYPES[self.type], self.name or '')

    @api.model
    def name_search(self, name, args=None, operator='ilike', limit=100):
        args = args or []
        recs = self.browse()
        if name:
            recs = self.search([('number', '=', name)] + args, limit=limit)
        if not recs:
            recs = self.search([('name', operator, name)] + args, limit=limit)
        return recs.name_get()

    @api.model
    def _refund_cleanup_lines(self, lines):
        """ Convert records to dict of values suitable for one2many line creation

            :param recordset lines: records to convert
            :return: list of command tuple for one2many line creation [(0, 0, dict of valueis), ...]
        """
        result = []
        for line in lines:
            values = {}
            for name, field in line._fields.iteritems():
                if name in MAGIC_COLUMNS:
                    continue
                elif field.type == 'many2one':
                    values[name] = line[name].id
                elif field.type not in ['many2many', 'one2many']:
                    values[name] = line[name]
                elif name == 'invoice_line_tax_id':
                    values[name] = [(6, 0, line[name].ids)]
            result.append((0, 0, values))
        return result

    @api.model
    def _prepare_refund(self, invoice, date=None, period_id=None, description=None, journal_id=None):
        """ Prepare the dict of values to create the new refund from the invoice.
            This method may be overridden to implement custom
            refund generation (making sure to call super() to establish
            a clean extension chain).

            :param record invoice: invoice to refund
            :param string date: refund creation date from the wizard
            :param integer period_id: force account.period from the wizard
            :param string description: description of the refund from the wizard
            :param integer journal_id: account.journal from the wizard
            :return: dict of value to create() the refund
        """
        values = {}
        for field in ['name', 'reference', 'comment', 'date_due', 'partner_id', 'company_id',
                'account_id', 'currency_id', 'payment_term', 'user_id', 'fiscal_position']:
            if invoice._fields[field].type == 'many2one':
                values[field] = invoice[field].id
            else:
                values[field] = invoice[field] or False

        values['invoice_line'] = self._refund_cleanup_lines(invoice.invoice_line)

        tax_lines = filter(lambda l: l.manual, invoice.tax_line)
        values['tax_line'] = self._refund_cleanup_lines(tax_lines)

        if journal_id:
            journal = self.env['account.journal'].browse(journal_id)
        elif invoice['type'] == 'in_invoice':
            journal = self.env['account.journal'].search([('type', '=', 'purchase_refund')], limit=1)
        else:
            journal = self.env['account.journal'].search([('type', '=', 'sale_refund')], limit=1)
        values['journal_id'] = journal.id

        values['type'] = TYPE2REFUND[invoice['type']]
        values['date_invoice'] = date or fields.Date.today()
        values['state'] = 'draft'
        values['number'] = False

        if period_id:
            values['period_id'] = period_id
        if description:
            values['name'] = description
        return values

    @api.multi
    @api.returns('self')
    def refund(self, date=None, period_id=None, description=None, journal_id=None):
        new_invoices = self.browse()
        for invoice in self:
            # create the new invoice
            values = self._prepare_refund(invoice, date=date, period_id=period_id,
                                    description=description, journal_id=journal_id)
            new_invoices += self.create(values)
        return new_invoices

    @api.v8
    def pay_and_reconcile(self, pay_amount, pay_account_id, period_id, pay_journal_id,
                          writeoff_acc_id, writeoff_period_id, writeoff_journal_id, name=''):
        # TODO check if we can use different period for payment and the writeoff line
        assert len(self)==1, "Can only pay one invoice at a time."
        # Take the seq as name for move
        SIGN = {'out_invoice': -1, 'in_invoice': 1, 'out_refund': 1, 'in_refund': -1}
        direction = SIGN[self.type]
        # take the chosen date
        date = self._context.get('date_p') or fields.Date.today()

        # Take the amount in currency and the currency of the payment
        if self._context.get('amount_currency') and self._context.get('currency_id'):
            amount_currency = self._context['amount_currency']
            currency_id = self._context['currency_id']
        else:
            amount_currency = False
            currency_id = False

        pay_journal = self.env['account.journal'].browse(pay_journal_id)
        if self.type in ('in_invoice', 'in_refund'):
            ref = self.reference
        else:
            ref = self._convert_ref(self.number)
        partner = self.partner_id._find_accounting_partner(self.partner_id)
        name = name or self.invoice_line.name or self.number
        # Pay attention to the sign for both debit/credit AND amount_currency
        l1 = {
            'name': name,
            'debit': direction * pay_amount > 0 and direction * pay_amount,
            'credit': direction * pay_amount < 0 and -direction * pay_amount,
            'account_id': self.account_id.id,
            'partner_id': partner.id,
            'ref': ref,
            'date': date,
            'currency_id': currency_id,
            'amount_currency': direction * (amount_currency or 0.0),
            'company_id': self.company_id.id,
        }
        l2 = {
            'name': name,
            'debit': direction * pay_amount < 0 and -direction * pay_amount,
            'credit': direction * pay_amount > 0 and direction * pay_amount,
            'account_id': pay_account_id,
            'partner_id': partner.id,
            'ref': ref,
            'date': date,
            'currency_id': currency_id,
            'amount_currency': -direction * (amount_currency or 0.0),
            'company_id': self.company_id.id,
        }
        move = self.env['account.move'].create({
            'ref': ref,
            'line_id': [(0, 0, l1), (0, 0, l2)],
            'journal_id': pay_journal_id,
            'period_id': period_id,
            'date': date,
        })

        move_ids = (move | self.move_id).ids
        self._cr.execute("SELECT id FROM account_move_line WHERE move_id IN %s",
                         (tuple(move_ids),))
        lines = self.env['account.move.line'].browse([r[0] for r in self._cr.fetchall()])
        lines2rec = lines.browse()
        total = 0.0
        for line in itertools.chain(lines, self.payment_ids):
            if line.account_id == self.account_id:
                lines2rec += line
                total += (line.debit or 0.0) - (line.credit or 0.0)

        inv_id, name = self.name_get()[0]
        if not round(total, self.env['decimal.precision'].precision_get('Account')) or writeoff_acc_id:
            lines2rec.reconcile('manual', writeoff_acc_id, writeoff_period_id, writeoff_journal_id)
        else:
            code = self.currency_id.symbol
            # TODO: use currency's formatting function
            msg = _("Invoice partially paid: %s%s of %s%s (%s%s remaining).") % \
                    (pay_amount, code, self.amount_total, code, total, code)
            self.message_post(body=msg)
            lines2rec.reconcile_partial('manual')

        # Update the stored value (fields.function), so we write to trigger recompute
        return self.write({})

    @api.v7
    def pay_and_reconcile(self, cr, uid, ids, pay_amount, pay_account_id, period_id, pay_journal_id,
                          writeoff_acc_id, writeoff_period_id, writeoff_journal_id, context=None, name=''):
        recs = self.browse(cr, uid, ids, context)
        return recs.pay_and_reconcile(pay_amount, pay_account_id, period_id, pay_journal_id,
                    writeoff_acc_id, writeoff_period_id, writeoff_journal_id, name=name)

class account_invoice_line(models.Model):
    _name = "account.invoice.line"
    _description = "Invoice Line"
    _order = "invoice_id,sequence,id"

    @api.one
    @api.depends('price_unit', 'discount', 'invoice_line_tax_id', 'quantity',
        'product_id', 'invoice_id.partner_id', 'invoice_id.currency_id')
    def _compute_price(self):
        price = self.price_unit * (1 - (self.discount or 0.0) / 100.0)
        taxes = self.invoice_line_tax_id.compute_all(price, self.quantity, product=self.product_id, partner=self.invoice_id.partner_id)
        self.price_subtotal = taxes['total']
        if self.invoice_id:
            self.price_subtotal = self.invoice_id.currency_id.round(self.price_subtotal)

    @api.model
    def _default_price_unit(self):
        if not self._context.get('check_total'):
            return 0
        total = self._context['check_total']
        for l in self._context.get('invoice_line', []):
            if isinstance(l, (list, tuple)) and len(l) >= 3 and l[2]:
                vals = l[2]
                price = vals.get('price_unit', 0) * (1 - vals.get('discount', 0) / 100.0)
                total = total - (price * vals.get('quantity'))
                taxes = vals.get('invoice_line_tax_id')
                if taxes and len(taxes[0]) >= 3 and taxes[0][2]:
                    taxes = self.env['account.tax'].browse(taxes[0][2])
                    tax_res = taxes.compute_all(price, vals.get('quantity'),
                        product=vals.get('product_id'), partner=self._context.get('partner_id'))
                    for tax in tax_res['taxes']:
                        total = total - tax['amount']
        return total

    @api.model
    def _default_account(self):
        # XXX this gets the default account for the user's company,
        # it should get the default account for the invoice's company
        # however, the invoice's company does not reach this point
        if self._context.get('type') in ('out_invoice', 'out_refund'):
            return self.env['ir.property'].get('property_account_income_categ', 'product.category')
        else:
            return self.env['ir.property'].get('property_account_expense_categ', 'product.category')

    name = fields.Text(string='Description', required=True)
    origin = fields.Char(string='Source Document',
        help="Reference of the document that produced this invoice.")
    sequence = fields.Integer(string='Sequence', default=10,
        help="Gives the sequence of this line when displaying the invoice.")
    invoice_id = fields.Many2one('account.invoice', string='Invoice Reference',
        ondelete='cascade', index=True)
    uos_id = fields.Many2one('product.uom', string='Unit of Measure',
        ondelete='set null', index=True)
    product_id = fields.Many2one('product.product', string='Product',
        ondelete='set null', index=True)
    account_id = fields.Many2one('account.account', string='Account',
        required=True, domain=[('type', 'not in', ['view', 'closed'])],
        default=_default_account,
        help="The income or expense account related to the selected product.")
    price_unit = fields.Float(string='Unit Price', required=True,
        digits= dp.get_precision('Product Price'),
        default=_default_price_unit)
    price_subtotal = fields.Float(string='Amount', digits= dp.get_precision('Account'),
        store=True, readonly=True, compute='_compute_price')
    quantity = fields.Float(string='Quantity', digits= dp.get_precision('Product Unit of Measure'),
        required=True, default=1)
    discount = fields.Float(string='Discount (%)', digits= dp.get_precision('Discount'),
        default=0.0)
    invoice_line_tax_id = fields.Many2many('account.tax',
        'account_invoice_line_tax', 'invoice_line_id', 'tax_id',
        string='Taxes', domain=[('parent_id', '=', False)])
    account_analytic_id = fields.Many2one('account.analytic.account',
        string='Analytic Account')
    company_id = fields.Many2one('res.company', string='Company',
        related='invoice_id.company_id', store=True, readonly=True)
    partner_id = fields.Many2one('res.partner', string='Partner',
        related='invoice_id.partner_id', store=True, readonly=True)

    @api.model
    def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
        res = super(account_invoice_line, self).fields_view_get(
            view_id=view_id, view_type=view_type, toolbar=toolbar, submenu=submenu)
        if self._context.get('type'):
            doc = etree.XML(res['arch'])
            for node in doc.xpath("//field[@name='product_id']"):
                if self._context['type'] in ('in_invoice', 'in_refund'):
                    node.set('domain', "[('purchase_ok', '=', True)]")
                else:
                    node.set('domain', "[('sale_ok', '=', True)]")
            res['arch'] = etree.tostring(doc)
        return res

    @api.multi
    def product_id_change(self, product, uom_id, qty=0, name='', type='out_invoice',
            partner_id=False, fposition_id=False, price_unit=False, currency_id=False,
            context=None, company_id=None):
        context = context or {}
        company_id = company_id if company_id is not None else context.get('company_id', False)
        self = self.with_context(company_id=company_id, force_company=company_id)

        if not partner_id:
            raise except_orm(_('No Partner Defined!'), _("You must first select a partner!"))
        if not product:
            if type in ('in_invoice', 'in_refund'):
                return {'value': {}, 'domain': {'product_uom': []}}
            else:
                return {'value': {'price_unit': 0.0}, 'domain': {'product_uom': []}}

        values = {}

        part = self.env['res.partner'].browse(partner_id)
        fpos = self.env['account.fiscal.position'].browse(fposition_id)

        if part.lang:
            self = self.with_context(lang=part.lang)
        product = self.env['product.product'].browse(product)

        values['name'] = product.partner_ref
        if type in ('out_invoice', 'out_refund'):
            account = product.property_account_income or product.categ_id.property_account_income_categ
        else:
            account = product.property_account_expense or product.categ_id.property_account_expense_categ
        account = fpos.map_account(account)
        if account:
            values['account_id'] = account.id

        if type in ('out_invoice', 'out_refund'):
            taxes = product.taxes_id or account.tax_ids
            if product.description_sale:
                values['name'] += '\n' + product.description_sale
        else:
            taxes = product.supplier_taxes_id or account.tax_ids
            if product.description_purchase:
                values['name'] += '\n' + product.description_purchase

        taxes = fpos.map_tax(taxes)
        values['invoice_line_tax_id'] = taxes.ids

        if type in ('in_invoice', 'in_refund'):
            values['price_unit'] = price_unit or product.standard_price
        else:
            values['price_unit'] = product.list_price

        values['uos_id'] = uom_id or product.uom_id.id
        domain = {'uos_id': [('category_id', '=', product.uom_id.category_id.id)]}

        company = self.env['res.company'].browse(company_id)
        currency = self.env['res.currency'].browse(currency_id)

        if company and currency:
            if company.currency_id != currency:
                if type in ('in_invoice', 'in_refund'):
                    values['price_unit'] = product.standard_price
                values['price_unit'] = values['price_unit'] * currency.rate

            if values['uos_id'] and values['uos_id'] != product.uom_id.id:
                values['price_unit'] = self.env['product.uom']._compute_price(
                    product.uom_id.id, values['price_unit'], values['uos_id'])

        return {'value': values, 'domain': domain}

    @api.multi
    def uos_id_change(self, product, uom, qty=0, name='', type='out_invoice', partner_id=False,
            fposition_id=False, price_unit=False, currency_id=False, context=None, company_id=None):
        context = context or {}
        company_id = company_id if company_id != None else context.get('company_id', False)
        self = self.with_context(company_id=company_id)

        result = self.product_id_change(
            product, uom, qty, name, type, partner_id, fposition_id, price_unit,
            currency_id, context=context, company_id=company_id,
        )
        warning = {}
        if not uom:
            result['value']['price_unit'] = 0.0
        if product and uom:
            prod = self.env['product.product'].browse(product)
            prod_uom = self.env['product.uom'].browse(uom)
            if prod.uom_id.category_id != prod_uom.category_id:
                warning = {
                    'title': _('Warning!'),
                    'message': _('The selected unit of measure is not compatible with the unit of measure of the product.'),
                }
                result['value']['uos_id'] = prod.uom_id.id
        if warning:
            result['warning'] = warning
        return result

    @api.model
    def move_line_get(self, invoice_id):
        inv = self.env['account.invoice'].browse(invoice_id)
        currency = inv.currency_id.with_context(date=inv.date_invoice)
        company_currency = inv.company_id.currency_id

        res = []
        for line in inv.invoice_line:
            mres = self.move_line_get_item(line)
            if not mres:
                continue
            res.append(mres)
            tax_code_found = False
            taxes = line.invoice_line_tax_id.compute_all(
                (line.price_unit * (1.0 - (line.discount or 0.0) / 100.0)),
                line.quantity, line.product_id, inv.partner_id)['taxes']
            for tax in taxes:
                if inv.type in ('out_invoice', 'in_invoice'):
                    tax_code_id = tax['base_code_id']
                    tax_amount = line.price_subtotal * tax['base_sign']
                else:
                    tax_code_id = tax['ref_base_code_id']
                    tax_amount = line.price_subtotal * tax['ref_base_sign']

                if tax_code_found:
                    if not tax_code_id:
                        continue
                    res.append(dict(mres))
                    res[-1]['price'] = 0.0
                    res[-1]['account_analytic_id'] = False
                elif not tax_code_id:
                    continue
                tax_code_found = True

                res[-1]['tax_code_id'] = tax_code_id
                res[-1]['tax_amount'] = currency.compute(tax_amount, company_currency)

        return res

    @api.model
    def move_line_get_item(self, line):
        return {
            'type': 'src',
            'name': line.name.split('\n')[0][:64],
            'price_unit': line.price_unit,
            'quantity': line.quantity,
            'price': line.price_subtotal,
            'account_id': line.account_id.id,
            'product_id': line.product_id.id,
            'uos_id': line.uos_id.id,
            'account_analytic_id': line.account_analytic_id.id,
            'taxes': line.invoice_line_tax_id,
        }

    #
    # Set the tax field according to the account and the fiscal position
    #
    @api.multi
    def onchange_account_id(self, product_id, partner_id, inv_type, fposition_id, account_id):
        if not account_id:
            return {}
        unique_tax_ids = []
        account = self.env['account.account'].browse(account_id)
        if not product_id:
            fpos = self.env['account.fiscal.position'].browse(fposition_id)
            unique_tax_ids = fpos.map_tax(account.tax_ids).ids
        else:
            product_change_result = self.product_id_change(product_id, False, type=inv_type,
                partner_id=partner_id, fposition_id=fposition_id, company_id=account.company_id.id)
            if 'invoice_line_tax_id' in product_change_result.get('value', {}):
                unique_tax_ids = product_change_result['value']['invoice_line_tax_id']
        return {'value': {'invoice_line_tax_id': unique_tax_ids}}


class account_invoice_tax(models.Model):
    _name = "account.invoice.tax"
    _description = "Invoice Tax"
    _order = 'sequence'

    @api.one
    @api.depends('base', 'base_amount', 'amount', 'tax_amount')
    def _compute_factors(self):
        self.factor_base = self.base_amount / self.base if self.base else 1.0
        self.factor_tax = self.tax_amount / self.amount if self.amount else 1.0

    invoice_id = fields.Many2one('account.invoice', string='Invoice Line',
        ondelete='cascade', index=True)
    name = fields.Char(string='Tax Description',
        required=True)
    account_id = fields.Many2one('account.account', string='Tax Account',
        required=True, domain=[('type', 'not in', ['view', 'income', 'closed'])])
    account_analytic_id = fields.Many2one('account.analytic.account', string='Analytic account')
    base = fields.Float(string='Base', digits=dp.get_precision('Account'))
    amount = fields.Float(string='Amount', digits=dp.get_precision('Account'))
    manual = fields.Boolean(string='Manual', default=True)
    sequence = fields.Integer(string='Sequence',
        help="Gives the sequence order when displaying a list of invoice tax.")
    base_code_id = fields.Many2one('account.tax.code', string='Base Code',
        help="The account basis of the tax declaration.")
    base_amount = fields.Float(string='Base Code Amount', digits=dp.get_precision('Account'),
        default=0.0)
    tax_code_id = fields.Many2one('account.tax.code', string='Tax Code',
        help="The tax basis of the tax declaration.")
    tax_amount = fields.Float(string='Tax Code Amount', digits=dp.get_precision('Account'),
        default=0.0)

    company_id = fields.Many2one('res.company', string='Company',
        related='account_id.company_id', store=True, readonly=True)
    factor_base = fields.Float(string='Multipication factor for Base code',
        compute='_compute_factors')
    factor_tax = fields.Float(string='Multipication factor Tax code',
        compute='_compute_factors')

    @api.multi
    def base_change(self, base, currency_id=False, company_id=False, date_invoice=False):
        factor = self.factor_base if self else 1
        company = self.env['res.company'].browse(company_id)
        if currency_id and company.currency_id:
            currency = self.env['res.currency'].browse(currency_id)
            currency = currency.with_context(date=date_invoice or fields.Date.today())
            base = currency.compute(base * factor, company.currency_id, round=False)
        return {'value': {'base_amount': base}}

    @api.multi
    def amount_change(self, amount, currency_id=False, company_id=False, date_invoice=False):
        factor = self.factor_tax if self else 1
        company = self.env['res.company'].browse(company_id)
        if currency_id and company.currency_id:
            currency = self.env['res.currency'].browse(currency_id)
            currency = currency.with_context(date=date_invoice or fields.Date.today())
            amount = currency.compute(amount * factor, company.currency_id, round=False)
        return {'value': {'tax_amount': amount}}

    @api.v8
    def compute(self, invoice):
        tax_grouped = {}
        currency = invoice.currency_id.with_context(date=invoice.date_invoice or fields.Date.today())
        company_currency = invoice.company_id.currency_id
        for line in invoice.invoice_line:
            taxes = line.invoice_line_tax_id.compute_all(
                (line.price_unit * (1 - (line.discount or 0.0) / 100.0)),
                line.quantity, line.product_id, invoice.partner_id)['taxes']
            for tax in taxes:
                val = {
                    'invoice_id': invoice.id,
                    'name': tax['name'],
                    'amount': tax['amount'],
                    'manual': False,
                    'sequence': tax['sequence'],
                    'base': currency.round(tax['price_unit'] * line['quantity']),
                }
                if invoice.type in ('out_invoice','in_invoice'):
                    val['base_code_id'] = tax['base_code_id']
                    val['tax_code_id'] = tax['tax_code_id']
                    val['base_amount'] = currency.compute(val['base'] * tax['base_sign'], company_currency, round=False)
                    val['tax_amount'] = currency.compute(val['amount'] * tax['tax_sign'], company_currency, round=False)
                    val['account_id'] = tax['account_collected_id'] or line.account_id.id
                    val['account_analytic_id'] = tax['account_analytic_collected_id']
                else:
                    val['base_code_id'] = tax['ref_base_code_id']
                    val['tax_code_id'] = tax['ref_tax_code_id']
                    val['base_amount'] = currency.compute(val['base'] * tax['ref_base_sign'], company_currency, round=False)
                    val['tax_amount'] = currency.compute(val['amount'] * tax['ref_tax_sign'], company_currency, round=False)
                    val['account_id'] = tax['account_paid_id'] or line.account_id.id
                    val['account_analytic_id'] = tax['account_analytic_paid_id']

                key = (val['tax_code_id'], val['base_code_id'], val['account_id'], val['account_analytic_id'])
                if not key in tax_grouped:
                    tax_grouped[key] = val
                else:
                    tax_grouped[key]['base'] += val['base']
                    tax_grouped[key]['amount'] += val['amount']
                    tax_grouped[key]['base_amount'] += val['base_amount']
                    tax_grouped[key]['tax_amount'] += val['tax_amount']

        for t in tax_grouped.values():
            t['base'] = currency.round(t['base'])
            t['amount'] = currency.round(t['amount'])
            t['base_amount'] = currency.round(t['base_amount'])
            t['tax_amount'] = currency.round(t['tax_amount'])

        return tax_grouped

    @api.v7
    def compute(self, cr, uid, invoice_id, context=None):
        recs = self.browse(cr, uid, [], context)
        invoice = recs.env['account.invoice'].browse(invoice_id)
        return recs.compute(invoice)

    @api.model
    def move_line_get(self, invoice_id):
        res = []
        self._cr.execute(
            'SELECT * FROM account_invoice_tax WHERE invoice_id = %s',
            (invoice_id,)
        )
        for row in self._cr.dictfetchall():
            if not (row['amount'] or row['tax_code_id'] or row['tax_amount']):
                continue
            res.append({
                'type': 'tax',
                'name': row['name'],
                'price_unit': row['amount'],
                'quantity': 1,
                'price': row['amount'] or 0.0,
                'account_id': row['account_id'],
                'tax_code_id': row['tax_code_id'],
                'tax_amount': row['tax_amount'],
                'account_analytic_id': row['account_analytic_id'],
            })
        return res


class res_partner(models.Model):
    # Inherits partner and adds invoice information in the partner form
    _inherit = 'res.partner'

    invoice_ids = fields.One2many('account.invoice', 'partner_id', string='Invoices',
        readonly=True)

    def _find_accounting_partner(self, partner):
        '''
        Find the partner for which the accounting entries will be created
        '''
        return partner.commercial_partner_id

class mail_compose_message(models.Model):
    _inherit = 'mail.compose.message'

    @api.multi
    def send_mail(self):
        context = self._context
        if context.get('default_model') == 'account.invoice' and \
                context.get('default_res_id') and context.get('mark_invoice_as_sent'):
            invoice = self.env['account.invoice'].browse(context['default_res_id'])
            invoice = invoice.with_context(mail_post_autofollow=True)
            self.write({'sent': True})
            self.message_post(body=_("Invoice sent"))
        return super(mail_compose_message, self).send_mail()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
