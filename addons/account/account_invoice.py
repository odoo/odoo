# -*- coding: utf-8 -*-

import itertools
import json
from lxml import etree

from openerp import api, fields, models, _
from openerp.tools import float_is_zero

from openerp.exceptions import UserError, RedirectWarning

import openerp.addons.decimal_precision as dp

# mapping invoice type to journal type
TYPE2JOURNAL = {
    'out_invoice': 'sale',
    'in_invoice': 'purchase',
    'out_refund': 'sale',
    'in_refund': 'purchase',
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
        'type': {},
        'state': {
            'account.mt_invoice_paid': lambda self, cr, uid, obj, ctx=None: obj.state == 'paid' and obj.type in ('out_invoice', 'out_refund'),
            'account.mt_invoice_validated': lambda self, cr, uid, obj, ctx=None: obj.state == 'open' and obj.type in ('out_invoice', 'out_refund'),
        },
    }

    # @api.model
    # def create(self, vals):
    #     inv = super(account_invoice, self).create(vals)
    #     inv.compute_taxes();

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
    @api.returns('account.analytic.journal', lambda r: r.id)
    def _get_journal_analytic(self, inv_type):
        """ Return the analytic journal corresponding to the given invoice type. """
        journal_type = TYPE2JOURNAL.get(inv_type, 'sale')
        journal = self.env['account.analytic.journal'].search([('type', '=', journal_type)], limit=1)
        if not journal:
            raise UserError(_("You must define an analytic journal of type '%s'!") % (journal_type,))
        return journal

    @api.model
    def _get_reference_type(self):
        return [('none', _('Free Reference'))]

    @api.one
    @api.depends(
        'state', 'currency_id', 'invoice_line.price_subtotal',
        'move_id.line_id.amount_residual',
        'move_id.line_id.currency_id')
    def _compute_residual(self):
        residual = 0.0
        for line in self.sudo().move_id.line_id:
            if line.account_id.internal_type in ('receivable', 'payable'):
                if line.currency_id == self.currency_id:
                    residual += line.currency_id and line.amount_residual_currency or line.amount_residual
                else:
                    from_currency = (line.currency_id and line.currency_id.with_context(date=line.date)) or line.company_id.currency_id.with_context(date=line.date)
                    residual += from_currency.compute(line.amount_residual, self.currency_id)
        self.residual = max(residual, 0.0)
        self.reconciled = residual == 0.0

    @api.one
    def _get_outstanding_info_JSON(self):
        self.outstanding_credits_debits_widget = json.dumps(False)
        if self.state == 'open':
            domain = [('journal_id.type', 'in', ('bank','cash')),('account_id', '=', self.account_id.id),('partner_id', '=', self.partner_id.id),('reconciled', '=', False),('amount_residual', '!=', 0.0)]
            if self.type in ('out_invoice', 'in_refund'):
                domain.extend([('credit', '>', 0), ('debit', '=', 0)])
                type_payment = 'Outstanding credit'
            elif self.type in ('in_invoice', 'out_refund'):
                domain.extend([('credit', '=', 0), ('debit', '>', 0)])
                type_payment = 'Outstanding debit'
            info = {'title': '', 'outstanding': True, 'content': [], 'invoice_id': self.id}
            lines = self.env['account.move.line'].search(domain)
            if len(lines) != 0:
                for line in lines:
                    line_currency = line.currency_id or line.company_id.currency_id
                    info['content'].append({
                        'ref': line.ref or line.move_id.name,
                        'amount': line_currency.compute(abs(line.amount_residual),self.currency_id) if line_currency != self.currency_id else abs(line.amount_residual_currency),
                        'currency': self.currency_id.symbol,
                        'id': line.id,
                        'position': self.currency_id.position,
                        'digits': [69, self.currency_id.decimal_places],
                    })
                info['title'] = type_payment + ' from ' + line.partner_id.name
                self.outstanding_credits_debits_widget = json.dumps(info)

    @api.one
    def _get_payment_info_JSON(self):
        self.payments_widget = json.dumps(False)
        if self.payment_ids:
            info = {'title': 'Less Payment', 'outstanding': False, 'content': []}
            for payment in self.payment_ids:
                if self.type in ('out_invoice', 'in_refund'):
                    amount = sum([p.amount for p in payment.matched_debit_ids if p.debit_move_id in self.move_id.line_id])
                    amount_currency = sum([p.amount_currency for p in payment.matched_debit_ids if p.debit_move_id in self.move_id.line_id])
                elif self.type in ('in_invoice', 'out_refund'):
                    amount = sum([p.amount for p in payment.matched_credit_ids if p.credit_move_id in self.move_id.line_id])
                    amount_currency = sum([p.amount_currency for p in payment.matched_credit_ids if p.credit_move_id in self.move_id.line_id])
                if payment.currency_id and float_is_zero(amount_currency, precision_digits=payment.currency_id.decimal_places):
                    continue
                payment_currency = payment.currency_id or payment.company_id.currency_id
                info['content'].append({
                    'name': payment.name,
                    'ref': payment.journal_id.name,
                    'amount': payment_currency.compute(-amount,self.currency_id) if payment_currency != self.currency_id else -amount_currency,
                    'currency': self.currency_id.symbol,
                    'digits': [69, self.currency_id.decimal_places],
                    'position': self.currency_id.position,
                    'date': payment.date,
                })
            self.payments_widget = json.dumps(info)

    @api.one
    @api.depends('move_id.line_id.amount_residual')
    def _compute_payments(self):
        payment_lines = []
        for line in self.move_id.line_id:
            payment_lines.extend([rp.credit_move_id.id for rp in line.matched_credit_ids])
            payment_lines.extend([rp.debit_move_id.id for rp in line.matched_debit_ids])
        self.payment_ids = self.env['account.move.line'].browse(payment_lines).sorted()

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
             " * The 'Pro-forma' when invoice is in Pro-forma status, invoice does not have an invoice number.\n"
             " * The 'Open' status is used when user create invoice, an invoice number is generated. Its in open status till user does not pay invoice.\n"
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
    date = fields.Date(string='Valuation Date',
        copy=False,
        help="Keep empty to use the date of the validation(invoice) date.",
        readonly=True, states={'draft': [('readonly', False)]})

    account_id = fields.Many2one('account.account', string='Account',
        required=True, readonly=True, states={'draft': [('readonly', False)]},
        domain=[('deprecated', '=', False)], help="The partner account used for this invoice.")
    invoice_line = fields.One2many('account.invoice.line', 'invoice_id', string='Invoice Lines',
        readonly=True, states={'draft': [('readonly', False)]}, copy=True)
    tax_line = fields.One2many('account.invoice.tax', 'invoice_id', string='Tax Lines',
        readonly=True, states={'draft': [('readonly', False)]}, copy=True)
    move_id = fields.Many2one('account.move', string='Journal Entry',
        readonly=True, index=True, ondelete='restrict', copy=False,
        help="Link to the automatically generated Journal Items.")

    amount_untaxed = fields.Float(string='Subtotal', digits=0,
        store=True, readonly=True, compute='_compute_amount', track_visibility='always')
    amount_tax = fields.Float(string='Tax', digits=0,
        store=True, readonly=True, compute='_compute_amount')
    amount_total = fields.Float(string='Total', digits=0,
        store=True, readonly=True, compute='_compute_amount')

    currency_id = fields.Many2one('res.currency', string='Currency',
        required=True, readonly=True, states={'draft': [('readonly', False)]},
        default=_default_currency, track_visibility='always')
    journal_id = fields.Many2one('account.journal', string='Journal',
        required=True, readonly=True, states={'draft': [('readonly', False)]},
        default=_default_journal,
        domain="[('type', 'in', {'out_invoice': ['sale'], 'out_refund': ['sale'], 'in_refund': ['purchase'], 'in_invoice': ['purchase']}.get(type, [])), ('company_id', '=', company_id)]")
    company_id = fields.Many2one('res.company', string='Company', change_default=True,
        required=True, readonly=True, states={'draft': [('readonly', False)]},
        default=lambda self: self.env['res.company']._company_default_get('account.invoice'))
    check_total = fields.Float(string='Verification Total', digits=0,
        readonly=True, states={'draft': [('readonly', False)]}, default=0.0)

    reconciled = fields.Boolean(string='Paid/Reconciled', store=True, readonly=True, compute='_compute_residual',
        help="It indicates that the invoice has been paid and the journal entry of the invoice has been reconciled with one or several journal entries of payment.")
    partner_bank_id = fields.Many2one('res.partner.bank', string='Bank Account',
        help='Bank Account Number to which the invoice will be paid. A Company bank account if this is a Customer Invoice or Supplier Refund, otherwise a Partner bank account number.',
        readonly=True, states={'draft': [('readonly', False)]})

    residual = fields.Float(string='Amount Due', digits=0,
        compute='_compute_residual', store=True, help="Remaining amount due.")
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

    outstanding_credits_debits_widget = fields.Text(compute='_get_outstanding_info_JSON')
    payments_widget = fields.Text(compute='_get_payment_info_JSON')

    _sql_constraints = [
        ('number_uniq', 'unique(number, company_id, journal_id, type)', 'Invoice Number must be unique per Company!'),
    ]

    @api.model
    def fields_view_get(self, view_id=None, view_type=False, toolbar=False, submenu=False):
        context = self._context

        def get_view_id(xid, name):
            try:
                return self.env['ir.model.data'].xmlid_to_res_id('account.' + xid, raise_if_not_found=True)
            except ValueError:
                try:
                    return self.env['ir.ui.view'].search([('name', '=', name)], limit=1).id
                except Exception:
                    return False    # view not found

        if context.get('active_model') == 'res.partner' and context.get('active_ids'):
            partner = self.env['res.partner'].browse(context['active_ids'])[0]
            if not view_type:
                view_id = get_view_id('invoice_tree', 'account.invoice.tree')
                view_type = 'tree'
            elif view_type == 'form':
                if partner.supplier and not partner.customer:
                    view_id = get_view_id('invoice_supplier_form', 'account.invoice.supplier.form')
                elif partner.customer and not partner.supplier:
                    view_id = get_view_id('invoice_form', 'account.invoice.form')

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
        ctx = dict(
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
                raise UserError(_('You cannot delete an invoice which is not draft or cancelled. You should refund it instead.'))
            elif invoice.internal_number:
                raise UserError(_('You cannot delete an invoice after it has been validated (and received a number). You can set it back to "Draft" state and modify its content, then re-confirm it.'))
        return super(account_invoice, self).unlink()

    @api.multi
    def onchange_partner_id(self, type, partner_id, date_invoice=False, payment_term=False, partner_bank_id=False, company_id=False):
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
            bank_id = p.bank_ids and p.bank_ids.ids[0] or False

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
            date_invoice = fields.Date.context_today(self)
        if not payment_term_id:
            # To make sure the invoice due date should contain due date which is
            # entered by user when there is no payment term defined
            return {'value': {'date_due': self.date_due or date_invoice}}
        pterm = self.env['account.payment.term'].browse(payment_term_id)
        pterm_list = pterm.compute(value=1, date_ref=date_invoice)[0]
        if pterm_list:
            return {'value': {'date_due': max(line[0] for line in pterm_list)}}
        else:
            raise UserError(_('The payment term of supplier does not have a payment term line.'))

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
                values = {'account_id': acc_id}

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
                            raise UserError(_("""Configuration Error!\nInvoice line account's company and invoice's company does not match."""))

        if company_id and type:
            journal_type = TYPE2JOURNAL[type]
            journals = self.env['account.journal'].search([('type', '=', journal_type), ('company_id', '=', company_id)])
            if journals:
                values['journal_id'] = journals[0].id
            journal_defaults = self.env['ir.values'].get_defaults_dict('account.invoice', 'type=%s' % type)
            if 'journal_id' in journal_defaults:
                values['journal_id'] = journal_defaults['journal_id']
            if not values.get('journal_id'):
                field_desc = journals.fields_get(['type'])
                type_label = next(t for t, label in field_desc['type']['selection'] if t == journal_type)
                action = self.env.ref('account.action_account_journal_form')
                msg = _('Cannot find any account journal of type "%s" for this company, You should create one.\n Please go to Journal Configuration') % type_label
                raise RedirectWarning(msg, action.id, _('Go to the configuration panel'))
            domain = {'journal_id': [('id', 'in', journals.ids)]}

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
    def compute_taxes(self):
        account_invoice_tax = self.env['account.invoice.tax']
        ctx = dict(self._context)
        for invoice in self:
            # Delete non-manual tax lines
            self._cr.execute("DELETE FROM account_invoice_tax WHERE invoice_id=%s AND manual is False", (invoice.id,))
            self.invalidate_cache()

            # Generate one tax line per tax, however many invoice lines it's applied to
            tax_grouped = {}
            for line in self.invoice_line:
                price_unit = line.price_unit * (1 - (line.discount or 0.0) / 100.0)
                taxes = line.invoice_line_tax_id.compute_all(price_unit, self.currency_id, line.quantity, line.product_id, self.partner_id)['taxes']
                for tax in taxes:
                    val = {
                        'invoice_id': self.id,
                        'name': tax['name'],
                        'tax_id': tax['id'],
                        'amount': tax['amount'],
                        'manual': False,
                        'sequence': tax['sequence'],
                        'account_analytic_id': line.account_analytic_id.id,
                        'account_id': self.type in ('out_invoice','in_invoice') and (tax['account_id'] or line.account_id.id) or (tax['refund_account_id'] or line.account_id.id),
                    }

                    # If the taxes generate moves on the same financial account as the invoice line
                    # and no default analytic account is defined at the tax level, propagate the
                    # analytic account from the invoice line to the tax line. This is necessary
                    # in situations were (part of) the taxes cannot be reclaimed,
                    # to ensure the tax move is allocated to the proper analytic account.
                    if not val.get('account_analytic_id') and line.account_analytic_id and val['account_id'] == line.account_id.id:
                        val['account_analytic_id'] = line.account_analytic_id.id

                    key = tax['id']
                    if key not in tax_grouped:
                        tax_grouped[key] = val
                    else:
                        tax_grouped[key]['amount'] += val['amount']

            # Create new tax lines
            for tax in tax_grouped.values():
                account_invoice_tax.create(tax)

        # dummy write on self to trigger recomputations
        ctx = dict(self._context)  # TODO : why lang in context ?
        if self[0].partner_id.lang:
            ctx['lang'] = self[0].partner_id.lang
        return self.with_context(ctx).write({'invoice_line': []})

    @api.multi
    def compute_amount(self, set_total=False):
        for invoice in self:
            if set_total:
                invoice.check_total = invoice.amount_total
        return True

    @api.one
    def register_payment(self, payment_line, writeoff_acc_id=False, writeoff_journal_id=False):
        """ Reconcile payable/receivable lines from the invoice with payment_line """
        line_to_reconcile = self.move_id.line_id.filtered(lambda r: not r.reconciled and r.account_id.internal_type in ('payable', 'receivable'))
        return (line_to_reconcile + payment_line).reconcile(writeoff_acc_id, writeoff_journal_id)

    @api.v7
    def assign_outstanding_credit(self, cr, uid, id, payment_id, context=None):
        return self.browse(cr, uid, id, context).register_payment(self.pool.get('account.move.line').browse(cr, uid, payment_id, context))

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
    def compute_invoice_totals(self, company_currency, ref, invoice_move_lines):
        total = 0
        total_currency = 0
        for line in invoice_move_lines:
            if self.currency_id != company_currency:
                currency = self.currency_id.with_context(date=self.date_invoice or fields.Date.context_today(self))
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

    @api.model
    def invoice_line_move_line_get(self):
        res = []
        for line in self.invoice_line:
            tax_ids = [(4, id, None) for id in line.invoice_line_tax_id.ids]
            move_line_dict = {
                'invl_id': line.id,
                'type': 'src',
                'name': line.name.split('\n')[0][:64],
                'price_unit': line.price_unit,
                'quantity': line.quantity,
                'price': line.price_subtotal,
                'account_id': line.account_id.id,
                'product_id': line.product_id.id,
                'uos_id': line.uos_id.id,
                'account_analytic_id': line.account_analytic_id.id,
                'tax_ids': tax_ids,
            }
            if line['account_analytic_id']:
                move_line_dict['analytic_lines'] = [(0,0, line._get_analytic_line())]
            res.append(move_line_dict)
        return res

    @api.model
    def tax_line_move_line_get(self):
        res = []
        for tax_line in self.tax_line:
            res.append({
                'tax_line_id': tax_line.tax_id.id,
                'type': 'tax',
                'name': tax_line.name,
                'price_unit': tax_line.amount,
                'quantity': 1,
                'price': tax_line.amount,
                'account_id': tax_line.account_id.id,
                # TODO : find right analytic account to use
                #'account_analytic_id': tax_line.account_analytic_id.id,
            })
        return res

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
        account_move = self.env['account.move']

        for inv in self:
            if not inv.journal_id.sequence_id:
                raise UserError(_('Please define sequence on the journal related to this invoice.'))
            if not inv.invoice_line:
                raise UserError(_('Please create some invoice lines.'))
            if inv.move_id:
                continue

            ctx = dict(self._context, lang=inv.partner_id.lang)

            if not inv.date_invoice:
                inv.with_context(ctx).write({'date_invoice': fields.Date.context_today(self)})
            date_invoice = inv.date_invoice
            company_currency = inv.company_id.currency_id

            # create move lines (one per invoice line + eventual taxes and analytic lines)
            iml = inv.invoice_line_move_line_get()
            iml += inv.tax_line_move_line_get()

            # I disabled the check_total feature
            if self.env['res.users'].has_group('account.group_supplier_inv_check_total'):
                if inv.type in ('in_invoice', 'in_refund') and abs(inv.check_total - inv.amount_total) >= (inv.currency_id.rounding / 2.0):
                    raise UserError(_('Please verify the price of the invoice!\nThe encoded total does not match the computed total.'))

            if inv.type in ('in_invoice', 'in_refund'):
                ref = inv.reference
            else:
                ref = inv.number

            diff_currency = inv.currency_id != company_currency
            # create one move line for the total and possibly adjust the other lines amount
            total, total_currency, iml = inv.with_context(ctx).compute_invoice_totals(company_currency, ref, iml)

            name = inv.name or inv.supplier_invoice_number or '/'
            if inv.payment_term:
                totlines = inv.with_context(ctx).payment_term.compute(total, date_invoice)[0]
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
                        'invoice': inv.id
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
                    'ref': ref,
                    'invoice': inv.id
                })
            date = date_invoice

            part = self.env['res.partner']._find_accounting_partner(inv.partner_id)

            line = [(0, 0, self.line_get_convert(l, part.id, date)) for l in iml]
            line = inv.group_lines(iml, line)

            journal = inv.journal_id.with_context(ctx)
            line = inv.finalize_invoice_move_lines(line)

            move_vals = {
                'ref': inv.reference or inv.name,
                'line_id': line,
                'journal_id': journal.id,
                'date': inv.date_invoice,
                'narration': inv.comment,
                'company_id': inv.company_id.id,
            }
            ctx['company_id'] = inv.company_id.id
            ctx['dont_create_taxes'] = True
            date = inv.date
            if not date:
                date = fields.Date.context_today(self)
                move_vals['date'] = date
                for i in line:
                    i[2]['date'] = date

            ctx['invoice'] = inv
            move = account_move.with_context(ctx).create(move_vals)
            # make the invoice point to that move
            vals = {
                'move_id': move.id,
                'date': date,
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
            'debit': line['price'] > 0 and line['price'],
            'credit': line['price'] < 0 and -line['price'],
            'account_id': line['account_id'],
            'analytic_lines': line.get('analytic_lines', []),
            'amount_currency': line['price'] > 0 and abs(line.get('amount_currency', False)) or -abs(line.get('amount_currency', False)),
            'currency_id': line.get('currency_id', False),
            'ref': line.get('ref', False),
            'quantity': line.get('quantity',1.00),
            'product_id': line.get('product_id', False),
            'product_uom_id': line.get('uos_id', False),
            'analytic_account_id': line.get('account_analytic_id', False),
            'invoice': line.get('invoice', False),
            'tax_ids': line.get('tax_ids', False),
            'tax_line_id': line.get('tax_line_id', False),
        }

    @api.multi
    def action_number(self):
        #TODO: not correct fix but required a fresh values before reading it.
        self.write({})

        for inv in self:
            self.write({'internal_number': inv.number})

            if inv.type in ('in_invoice', 'in_refund'):
                if not inv.reference:
                    ref = inv.number
                else:
                    ref = inv.reference
            else:
                ref = inv.number

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
                raise UserError(_('You cannot cancel an invoice which is partially paid. You need to unreconcile related payment entries first.'))

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

    @api.multi
    def name_get(self):
        TYPES = {
            'out_invoice': _('Invoice'),
            'in_invoice': _('Supplier Invoice'),
            'out_refund': _('Refund'),
            'in_refund': _('Supplier Refund'),
        }
        result = []
        for inv in self:
            result.append((inv.id, "%s %s" % (inv.number or TYPES[inv.type], inv.name or '')))
        return result

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
    def _prepare_refund(self, invoice, date_invoice=None, date=None, description=None, journal_id=None):
        """ Prepare the dict of values to create the new refund from the invoice.
            This method may be overridden to implement custom
            refund generation (making sure to call super() to establish
            a clean extension chain).

            :param record invoice: invoice to refund
            :param string date_invoice: refund creation date from the wizard
            :param integer date: force date from the wizard
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
            journal = self.env['account.journal'].search([('type', '=', 'purchase')], limit=1)
        else:
            journal = self.env['account.journal'].search([('type', '=', 'sale')], limit=1)
        values['journal_id'] = journal.id

        values['type'] = TYPE2REFUND[invoice['type']]
        values['date_invoice'] = date_invoice or fields.Date.context_today(invoice)
        values['state'] = 'draft'
        values['number'] = False

        if date:
            values['date'] = date
        if description:
            values['name'] = description
        return values

    @api.multi
    @api.returns('self')
    def refund(self, date_invoice=None, date=None, description=None, journal_id=None):
        new_invoices = self.browse()
        for invoice in self:
            # create the new invoice
            values = self._prepare_refund(invoice, date_invoice=date_invoice, date=date,
                                    description=description, journal_id=journal_id)
            new_invoices += self.create(values)
        return new_invoices

    @api.v8
    def pay_and_reconcile(self, pay_amount, pay_account_id, date, pay_journal_id,
                          writeoff_acc_id, writeoff_journal_id, name=''):
        # TODO check if we can use different period for payment and the writeoff line
        assert len(self) == 1, "Can only pay one invoice at a time."
        # Take the seq as name for move
        SIGN = {'out_invoice': -1, 'in_invoice': 1, 'out_refund': 1, 'in_refund': -1}
        direction = SIGN[self.type]
        # take the chosen date
        date = self._context.get('date_p') or fields.Date.context_today(self)

        # Take the amount in currency and the currency of the payment
        if self._context.get('amount_currency') and self._context.get('currency_id'):
            amount_currency = self._context['amount_currency']
            currency_id = self._context['currency_id']
        else:
            amount_currency = False
            currency_id = False

        if self.type in ('in_invoice', 'in_refund'):
            ref = self.reference
        else:
            ref = self.number
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
        if not round(total, self.company_id.currency_id.decimal_places) or writeoff_acc_id:
            lines2rec.reconcile(self.env['account.account'].browse(writeoff_acc_id), self.env['account.journal'].browse(writeoff_journal_id))
        else:
            code = self.currency_id.symbol
            # TODO: use currency's formatting function
            msg = _("Invoice partially paid: %s%s of %s%s (%s%s remaining).") % \
                    (pay_amount, code, self.amount_total, code, total, code)
            self.message_post(body=msg)
            #TODO check if this method is really needed, seems to only be used in test and data files
            # lines2rec.reconcile()

        # Update the stored value (fields.function), so we write to trigger recompute
        return self.write({})

    @api.v7
    def pay_and_reconcile(self, cr, uid, ids, pay_amount, pay_account_id, date, pay_journal_id,
                          writeoff_acc_id, writeoff_journal_id, context=None, name=''):
        recs = self.browse(cr, uid, ids, context)
        return recs.pay_and_reconcile(pay_amount, pay_account_id, date, pay_journal_id,
                    writeoff_acc_id, writeoff_journal_id, name=name)


class account_invoice_line(models.Model):
    _name = "account.invoice.line"
    _description = "Invoice Line"
    _order = "invoice_id,sequence,id"

    @api.multi
    def _get_analytic_line(self):
        company_currency = self.company_id.currency_id
        sign = 1 if self.type in ('out_invoice', 'in_refund') else -1
        if self.type in ('in_invoice', 'in_refund'):
            ref = self.invoice_id.reference
        else:
            ref = self.invoice_id.number
        if not self.invoice_id.journal_id.analytic_journal_id:
            raise UserError(_("No Analytic Journal! You have to define an analytic journal on the '%s' journal!") % (self.invoice_id.journal_id.name,))
        currency = self.currency_id.with_context(date=self.date_invoice)
        return {
            'name': self.name,
            'date': self.invoice_id.date_invoice,
            'account_id': self.account_analytic_id.id,
            'unit_amount': self.quantity,
            'amount': currency.compute(self.price, company_currency) * sign,
            'product_id': self.product_id.id,
            'product_uom_id': self.uos_id.id,
            'general_account_id': self.account_id.id,
            'journal_id': self.invoice_id.journal_id.analytic_journal_id.id,
            'ref': ref,
        }

    @api.one
    @api.depends('price_unit', 'discount', 'invoice_line_tax_id', 'quantity',
        'product_id', 'invoice_id.partner_id', 'invoice_id.currency_id')
    def _compute_price(self):
        currency = self.invoice_id and self.invoice_id.currency_id or None
        price = self.price_unit * (1 - (self.discount or 0.0) / 100.0)
        taxes = self.invoice_line_tax_id.compute_all(price, currency, self.quantity, product=self.product_id, partner=self.invoice_id.partner_id)
        self.price_subtotal = taxes['total_excluded']

    @api.model
    def _default_price_unit(self):
        if not self._context.get('check_total'):
            return 0
        currency = self.invoice_id and self.invoice_id.currency_id or None
        total = self._context['check_total']
        for l in self._context.get('invoice_line', []):
            if isinstance(l, (list, tuple)) and len(l) >= 3 and l[2]:
                vals = l[2]
                price = vals.get('price_unit', 0) * (1 - vals.get('discount', 0) / 100.0)
                total = total - (price * vals.get('quantity'))
                taxes = vals.get('invoice_line_tax_id')
                if taxes and len(taxes[0]) >= 3 and taxes[0][2]:
                    taxes = self.env['account.tax'].browse(taxes[0][2])
                    tax_res = taxes.compute_all(price, currency, vals.get('quantity'), vals.get('product_id'), self._context.get('partner_id'))
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
        ondelete='restrict', index=True)
    account_id = fields.Many2one('account.account', string='Account',
        required=True, domain=[('deprecated', '=', False)],
        default=_default_account,
        help="The income or expense account related to the selected product.")
    price_unit = fields.Float(string='Unit Price', required=True,
        default=_default_price_unit)
    price_subtotal = fields.Float(string='Amount', digits=0,
        store=True, readonly=True, compute='_compute_price')
    quantity = fields.Float(string='Quantity', digits= dp.get_precision('Product Unit of Measure'),
        required=True, default=1)
    discount = fields.Float(string='Discount (%)', digits= dp.get_precision('Discount'),
        default=0.0)
    invoice_line_tax_id = fields.Many2many('account.tax',
        'account_invoice_line_tax', 'invoice_line_id', 'tax_id',
        string='Taxes', domain=[('type_tax_use','!=','none')])
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

    @api.v8
    def get_invoice_line_account(self, product, fpos):
        accounts = product.get_product_accounts(fpos)
        if self.invoice_id.type in ('out_invoice', 'out_refund'):
            return accounts['income']
        return accounts['expense']

    @api.multi
    def product_id_change(self, product, uom_id, qty=0, name='', type='out_invoice',
            partner_id=False, fposition_id=False, price_unit=False, currency_id=False,
            company_id=None):
        context = self._context
        company_id = company_id if company_id is not None else context.get('company_id', False)
        self = self.with_context(company_id=company_id, force_company=company_id)

        if not partner_id:
            raise UserError(_("You must first select a partner!"))
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
        account = self.get_invoice_line_account(product, fpos)
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
            fposition_id=False, price_unit=False, currency_id=False, company_id=None):
        context = self._context
        company_id = company_id if company_id is not None else context.get('company_id', False)
        self = self.with_context(company_id=company_id)

        result = self.product_id_change(
            product, uom, qty, name, type, partner_id, fposition_id, price_unit,
            currency_id, company_id=company_id,
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

    @api.multi
    def onchange_account_id(self, product_id, partner_id, inv_type, fposition_id, account_id):
        """ Set the tax field according to the account and the fiscal position """
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

    invoice_id = fields.Many2one('account.invoice', string='Invoice', ondelete='cascade', index=True)
    name = fields.Char(string='Tax Description', required=True)
    tax_id = fields.Many2one('account.tax', string='Tax')
    account_id = fields.Many2one('account.account', string='Tax Account', required=True, domain=[('deprecated', '=', False)])
    account_analytic_id = fields.Many2one('account.analytic.account', string='Analytic account')
    amount = fields.Float(string='Amount', digits=0)
    manual = fields.Boolean(string='Manual', default=True)
    sequence = fields.Integer(string='Sequence', help="Gives the sequence order when displaying a list of invoice tax.")
    company_id = fields.Many2one('res.company', string='Company', related='account_id.company_id', store=True, readonly=True)


class res_partner(models.Model):
    # Inherits partner and adds invoice information in the partner form
    _inherit = 'res.partner'

    invoice_ids = fields.One2many('account.invoice', 'partner_id', string='Invoices',
        readonly=True, copy=False)

    def _find_accounting_partner(self, partner):
        ''' Find the partner for which the accounting entries will be created '''
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
            invoice.write({'sent': True})
            invoice.message_post(body=_("Invoice sent"))
        return super(mail_compose_message, self).send_mail()
