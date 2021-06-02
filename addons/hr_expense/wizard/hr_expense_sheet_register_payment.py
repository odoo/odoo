# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from werkzeug import url_encode


class HrExpenseSheetRegisterPaymentWizard(models.TransientModel):
    _name = "hr.expense.sheet.register.payment.wizard"
    _description = "Expense Register Payment Wizard"

    @api.model
    def default_get(self, fields):
        result = super(HrExpenseSheetRegisterPaymentWizard, self).default_get(fields)

        active_model = self._context.get('active_model')
        if active_model != 'hr.expense.sheet':
            raise UserError(_('You can only apply this action from an expense report.'))

        active_id = self._context.get('active_id')
        if 'expense_sheet_id' in fields and active_id:
            result['expense_sheet_id'] = active_id

        if 'partner_id' in fields and active_id and not result.get('partner_id'):
            expense_sheet = self.env['hr.expense.sheet'].browse(active_id)
            result['partner_id'] = expense_sheet.sudo().address_id.id or expense_sheet.sudo().employee_id.id and expense_sheet.sudo().employee_id.address_home_id.id
        return result

    expense_sheet_id = fields.Many2one('hr.expense.sheet', string="Expense Report", required=True)
    partner_id = fields.Many2one('res.partner', string='Partner', required=True, domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]")
    partner_bank_account_id = fields.Many2one('res.partner.bank', string="Recipient Bank Account", domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]")
    journal_id = fields.Many2one('account.journal', string='Payment Method', required=True, domain="[('type', 'in', ('bank', 'cash')), ('company_id', '=', company_id)]")
    company_id = fields.Many2one('res.company', related='expense_sheet_id.company_id', string='Company', readonly=True)
    payment_method_id = fields.Many2one('account.payment.method', string='Payment Type', required=True)
    amount = fields.Monetary(string='Payment Amount', required=True)
    currency_id = fields.Many2one('res.currency', string='Currency', required=True, default=lambda self: self.env.company.currency_id)
    payment_date = fields.Date(string='Payment Date', default=fields.Date.context_today, required=True)
    communication = fields.Char(string='Memo')
    hide_payment_method = fields.Boolean(compute='_compute_hide_payment_method',
        help="Technical field used to hide the payment method if the selected journal has only one available which is 'manual'")
    show_partner_bank_account = fields.Boolean(compute='_compute_show_partner_bank', help='Technical field used to know whether the field `partner_bank_account_id` needs to be displayed or not in the payments form views')
    require_partner_bank_account = fields.Boolean(compute='_compute_show_partner_bank', help='Technical field used to know whether the field `partner_bank_account_id` needs to be required or not in the payments form views')

    @api.onchange('partner_id')
    def _onchange_partner_id(self):
        expense_sheet = self.expense_sheet_id
        if expense_sheet.employee_id.id and expense_sheet.employee_id.sudo().bank_account_id.id:
            self.partner_bank_account_id = expense_sheet.employee_id.sudo().bank_account_id.id
        elif self.partner_id and len(self.partner_id.bank_ids) > 0:
            self.partner_bank_account_id = self.partner_id.bank_ids[0]
        else:
            self.partner_bank_account_id = False

    @api.constrains('amount')
    def _check_amount(self):
        for wizard in self:
            if not wizard.amount > 0.0:
                raise ValidationError(_('The payment amount must be strictly positive.'))

    @api.depends('payment_method_id')
    def _compute_show_partner_bank(self):
        """ Computes if the destination bank account must be displayed in the payment form view. By default, it
        won't be displayed but some modules might change that, depending on the payment type."""
        for payment in self:
            payment.show_partner_bank_account = payment.payment_method_id.code in self.env['account.payment']._get_method_codes_using_bank_account()
            payment.require_partner_bank_account = payment.payment_method_id.code in self.env['account.payment']._get_method_codes_needing_bank_account()

    @api.depends('journal_id')
    def _compute_hide_payment_method(self):
        for wizard in self:
            if not wizard.journal_id:
                wizard.hide_payment_method = True
            else:
                journal_payment_methods = wizard.journal_id.outbound_payment_method_ids
                wizard.hide_payment_method = (len(journal_payment_methods) == 1
                    and journal_payment_methods[0].code == 'manual')

    @api.onchange('journal_id')
    def _onchange_journal(self):
        if self.journal_id:
            # Set default payment method (we consider the first to be the default one)
            payment_methods = self.journal_id.outbound_payment_method_ids
            self.payment_method_id = payment_methods and payment_methods[0] or False
            # Set payment method domain (restrict to methods enabled for the journal and to selected payment type)
            return {'domain': {'payment_method_id': [('payment_type', '=', 'outbound'), ('id', 'in', payment_methods.ids)]}}
        return {}

    def _get_payment_vals(self):
        """ Hook for extension """
        return {
            'partner_type': 'supplier',
            'payment_type': 'outbound',
            'partner_id': self.partner_id.id,
            'partner_bank_account_id': self.partner_bank_account_id.id,
            'journal_id': self.journal_id.id,
            'company_id': self.company_id.id,
            'payment_method_id': self.payment_method_id.id,
            'amount': self.amount,
            'currency_id': self.currency_id.id,
            'payment_date': self.payment_date,
            'communication': self.communication
        }

    def expense_post_payment(self):
        self.ensure_one()
        company = self.company_id
        self = self.with_context(force_company=company.id, company_id=company.id)
        context = dict(self._context or {})
        active_ids = context.get('active_ids', [])
        expense_sheet = self.env['hr.expense.sheet'].browse(active_ids)

        # Create payment and post it
        payment = self.env['account.payment'].create(self._get_payment_vals())
        payment.post()

        # Log the payment in the chatter
        body = (_("A payment of %s %s with the reference <a href='/mail/view?%s'>%s</a> related to your expense %s has been made.") % (payment.amount, payment.currency_id.symbol, url_encode({'model': 'account.payment', 'res_id': payment.id}), payment.name, expense_sheet.name))
        expense_sheet.message_post(body=body)

        # Reconcile the payment and the expense, i.e. lookup on the payable account move lines
        account_move_lines_to_reconcile = self.env['account.move.line']
        for line in payment.move_line_ids + expense_sheet.account_move_id.line_ids:
            if line.account_id.internal_type == 'payable' and not line.reconciled:
                account_move_lines_to_reconcile |= line
        account_move_lines_to_reconcile.reconcile()

        return {'type': 'ir.actions.act_window_close'}
