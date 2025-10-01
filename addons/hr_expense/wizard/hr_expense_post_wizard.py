from odoo import _, api, fields, models
from odoo.exceptions import UserError


class HrExpensePostWizard(models.TransientModel):
    _name = 'hr.expense.post.wizard'
    _description = 'Expense Posting Wizard'

    @api.model
    def _default_employee_paid_expense_journal_id(self):
        """
         The journal is determining the company of the accounting entries generated from expense.
         We need to force journal company and expense company to be the same.
        """
        company_journal_id = self.env.company.employee_paid_expense_journal_id
        if company_journal_id:
            return company_journal_id.id
        closest_parent_company_journal = self.env.company.parent_ids[::-1].employee_paid_expense_journal_id[:1]
        if closest_parent_company_journal:
            return closest_parent_company_journal.id

        journal = self.env['account.journal'].search([
            *self.env['account.journal']._check_company_domain(self.env.company.id),
            ('type', '=', 'purchase'),
        ], limit=1)
        return journal.id

    @api.model
    def _default_company_paid_expense_journal_id(self):
        company_journal_id = self.env.company.company_paid_expense_journal_id
        if company_journal_id:
            return company_journal_id.id
        closest_parent_company_journal = self.env.company.parent_ids[::-1].company_paid_expense_journal_id[:1]
        if closest_parent_company_journal:
            return closest_parent_company_journal.id

        journal = self.env['account.journal'].search([
            *self.env['account.journal']._check_company_domain(self.env.company.id),
            ('type', '=', 'bank'),
        ], limit=1)
        return journal.id

    company_id = fields.Many2one(comodel_name='res.company', default=lambda self: self.env.company, string='Company', readonly=True)

    accounting_date = fields.Date(  # The date used for the accounting entries or the one we'd like to use if not yet posted
        string="Accounting Date",
        default=fields.Date.context_today,
        help="Specify the bill date of the related vendor bill."
    )
    employee_paid_expense_journal_id = fields.Many2one(
        comodel_name='account.journal',
        string="Employee Expense Journal",
        default=_default_employee_paid_expense_journal_id,
        check_company=True,
        domain=[('type', '=', 'purchase')],
    )
    company_paid_expense_journal_id = fields.Many2one(
        comodel_name='account.journal',
        string="Company Expense Journal",
        default=_default_company_paid_expense_journal_id,
        check_company=True,
        domain="[('type', 'in', ('bank', 'cash', 'credit'))]",
    )
    expense_ids = fields.Many2many(comodel_name='hr.expense')
    is_company_paid = fields.Boolean(
        compute='_compute_payment_mode',
    )
    is_employee_paid = fields.Boolean(
        compute='_compute_payment_mode',
    )

    @api.depends('expense_ids')
    def _compute_payment_mode(self):
        self.is_company_paid = self.expense_ids.filtered(lambda expense: expense.payment_mode == 'company_account')
        self.is_employee_paid = self.expense_ids.filtered(lambda expense: expense.payment_mode == 'own_account')

    def action_post_entry(self):
        """
        Post the expense, following one of those two options:
            - Company-paid expenses: Create and post a payment, with an accounting entry
            - Employee-paid expenses: Through a wizard, create and post a bill
        """
        expenses = self.env['hr.expense'].browse(self.env.context['active_ids'])
        if not self.env['account.move'].has_access('create'):
            raise UserError(_("You don't have the rights to create accounting entries."))

        company_paid_expenses = expenses.filtered(lambda expense: expense.payment_mode == 'company_account')
        employee_paid_expenses = expenses - company_paid_expenses

        if company_paid_expenses:
            company_paid_expenses.journal_id = self.company_paid_expense_journal_id
            company_paid_expenses._create_company_paid_moves()
            # Post the company-paid expense through the payment, to post both at the same time
            company_paid_expenses.account_move_id.origin_payment_id.action_post()

        expense_receipt_vals_list = [
            {
                **new_receipt_vals,
                'journal_id': self.employee_paid_expense_journal_id.id,
                'invoice_date': self.accounting_date,
            }
            for new_receipt_vals in employee_paid_expenses._prepare_receipts_vals()
        ]
        moves = self.env['account.move'].sudo().create(expense_receipt_vals_list)
        for move in moves:
            move._message_set_main_attachment_id(move.attachment_ids, force=True, filter_xml=False)
        moves.action_post()

        # Sets the default ones if not specified
        if not self.company_id.employee_paid_expense_journal_id:
            self.sudo().company_id.employee_paid_expense_journal_id = self.employee_paid_expense_journal_id.id
        if not self.company_id.company_paid_expense_journal_id:
            self.sudo().company_id.company_paid_expense_journal_id = self.company_paid_expense_journal_id.id

        # Add the company_paid ids to the redirect
        moves_ids = moves.ids + company_paid_expenses.account_move_id.ids

        action = {
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
        }
        if len(moves_ids) == 1:
            action.update({
                'name': moves.ref,
                'view_mode': 'form',
                'res_id': moves_ids[0],
            })
        else:
            list_view = self.env.ref('hr_expense.view_move_list_expense', raise_if_not_found=False)
            action.update({
                'name': _("New expense entries"),
                'view_mode': 'list,form',
                'views': [(list_view and list_view.id, 'list'), (False, 'form')],
                'domain': [('id', 'in', moves_ids)],
            })
        return action
