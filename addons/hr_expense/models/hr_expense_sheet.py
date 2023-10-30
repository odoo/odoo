# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, Command, models, _
from odoo.exceptions import UserError, ValidationError, RedirectWarning
from odoo.tools.misc import clean_context


class HrExpenseSheet(models.Model):
    """
        Here are the rights associated with the expense flow

        Action       Group                   Restriction
        =================================================================================
        Submit      Employee                Only his own
                    Officer                 If he is expense manager of the employee, manager of the employee
                                             or the employee is in the department managed by the officer
                    Manager                 Always
        Approve     Officer                 Not his own and he is expense manager of the employee, manager of the employee
                                             or the employee is in the department managed by the officer
                    Manager                 Always
        Post        Anybody                 State = approve and journal_id defined
        Done        Anybody                 State = approve and journal_id defined
        Cancel      Officer                 Not his own and he is expense manager of the employee, manager of the employee
                                             or the employee is in the department managed by the officer
                    Manager                 Always
        =================================================================================
    """
    _name = "hr.expense.sheet"
    _inherit = ['mail.thread.main.attachment', 'mail.activity.mixin']
    _description = "Expense Report"
    _order = "accounting_date desc, id desc"
    _check_company_auto = True

    @api.model
    def _default_employee_id(self):
        return self.env.user.employee_id

    @api.model
    def _default_journal_id(self):
        """
             The journal is determining the company of the accounting entries generated from expense.
             We need to force journal company and expense sheet company to be the same.
        """
        company_journal_id = self.env.company.expense_journal_id
        if company_journal_id:
            return company_journal_id.id
        default_company_id = self.default_get(['company_id'])['company_id']
        journal = self.env['account.journal'].search([
            *self.env['account.journal']._check_company_domain(default_company_id),
            ('type', '=', 'purchase'),
        ], limit=1)
        return journal.id

    name = fields.Char(string="Expense Report Summary", required=True, tracking=True)
    expense_line_ids = fields.One2many(
        comodel_name='hr.expense', inverse_name='sheet_id',
        string="Expense Lines",
        copy=False,
    )
    nb_expense = fields.Integer(compute='_compute_nb_expense', string="Number of Expenses")
    state = fields.Selection(
        selection=[
            ('draft', 'To Submit'),
            ('submit', 'Submitted'),
            ('approve', 'Approved'),
            ('post', 'Posted'),
            ('done', 'Done'),
            ('cancel', 'Refused')
        ],
        string="Status",
        compute='_compute_state', store=True, readonly=True,
        index=True,
        required=True,
        default='draft',
        tracking=True,
        copy=False,
    )
    approval_state = fields.Selection(
        selection=[
            ('submit', 'Submitted'),
            ('approve', 'Approved'),
            ('cancel', 'Refused'),
        ],
        copy=False,
    )
    approval_date = fields.Datetime(string="Approval Date", readonly=True)
    company_id = fields.Many2one(
        comodel_name='res.company',
        string="Company",
        required=True,
        readonly=True,
        default=lambda self: self.env.company,
    )
    employee_id = fields.Many2one(
        comodel_name='hr.employee',
        string="Employee",
        required=True,
        readonly=True,
        default=_default_employee_id,
        domain=[('filter_for_expense', '=', True)],
        check_company=True,
        tracking=True,
    )

    department_id = fields.Many2one(
        comodel_name='hr.department',
        related='employee_id.department_id',
        string="Department",
        store=True,
        copy=False,
    )
    user_id = fields.Many2one(
        comodel_name='res.users',
        string="Manager",
        compute='_compute_from_employee_id', store=True, readonly=True,
        domain=lambda self: [('groups_id', 'in', self.env.ref('hr_expense.group_hr_expense_team_approver').id)],
        copy=False,
        tracking=True,
    )
    product_ids = fields.Many2many(
        comodel_name='product.product',
        string="Categories",
        compute='_compute_product_ids',
        search='_search_product_ids',
        check_company=True,
    )

    # === Amount fields === #
    total_amount = fields.Monetary(
        string="Total",
        currency_field='company_currency_id',
        compute='_compute_amount', store=True, readonly=True,
        tracking=True,
    )
    untaxed_amount = fields.Monetary(
        string="Untaxed Amount",
        currency_field='company_currency_id',
        compute='_compute_amount', store=True, readonly=True,
    )
    total_tax_amount = fields.Monetary(
        string="Taxes",
        currency_field='company_currency_id',
        compute='_compute_amount', store=True, readonly=True,
    )
    amount_residual = fields.Monetary(
        string="Amount Due",
        currency_field='company_currency_id',
        compute='_compute_from_account_move_ids', store=True, readonly=True,
    )
    currency_id = fields.Many2one(
        comodel_name='res.currency',
        string="Currency",
        compute='_compute_currency_id', store=True, readonly=True,
    )
    company_currency_id = fields.Many2one(
        comodel_name='res.currency',
        related='company_id.currency_id',
        string="Report Company Currency"
    )
    is_multiple_currency = fields.Boolean(
        string="Handle lines with different currencies",
        compute='_compute_is_multiple_currency',
    )

    # === Account fields === #
    payment_state = fields.Selection(
        selection=lambda self: self.env["account.move"]._fields["payment_state"]._description_selection(self.env),
        string="Payment Status",
        compute='_compute_from_account_move_ids', store=True, readonly=True,
        copy=False,
        tracking=True,
    )
    payment_mode = fields.Selection(
        related='expense_line_ids.payment_mode',
        string="Paid By",
        tracking=True,
        readonly=True,
    )
    employee_journal_id = fields.Many2one(
        comodel_name='account.journal',
        string="Journal",
        default=_default_journal_id,
        check_company=True,
        domain=[('type', '=', 'purchase')],
        help="The journal used when the expense is paid by employee.",
    )
    selectable_payment_method_line_ids = fields.Many2many(
        comodel_name='account.payment.method.line',
        compute='_compute_selectable_payment_method_line_ids',
    )
    payment_method_line_id = fields.Many2one(
        comodel_name='account.payment.method.line',
        string="Payment Method",
        compute='_compute_payment_method_line_id', store=True, readonly=False,
        domain="[('id', 'in', selectable_payment_method_line_ids)]",
        help="The payment method used when the expense is paid by the company.",
    )
    accounting_date = fields.Date(string="Accounting Date", compute='_compute_accounting_date', store=True)
    account_move_ids = fields.One2many(
        string="Journal Entries",
        comodel_name='account.move', inverse_name='expense_sheet_id', readonly=True,
    )
    nb_account_move = fields.Integer(string="Number of Journal Entries", compute='_compute_nb_account_move')
    journal_id = fields.Many2one(
        comodel_name='account.journal',
        string="Expense Journal",
        compute='_compute_journal_id', store=True,
        check_company=True,
    )

    # === Security fields === #
    can_reset = fields.Boolean(string='Can Reset', compute='_compute_can_reset')
    can_approve = fields.Boolean(string='Can Approve', compute='_compute_can_approve')
    cannot_approve_reason = fields.Char(string='Cannot Approve Reason', compute='_compute_can_approve')
    is_editable = fields.Boolean(string="Expense Lines Are Editable By Current User", compute='_compute_is_editable')

    _sql_constraints = [(
        'journal_id_required_posted',
        "CHECK((state IN ('post', 'done') AND journal_id IS NOT NULL) OR (state NOT IN ('post', 'done')))",
        'The journal must be set on posted expense'
    )]

    @api.depends('expense_line_ids.total_amount', 'expense_line_ids.tax_amount')
    def _compute_amount(self):
        for sheet in self:
            sheet.total_amount = sum(sheet.expense_line_ids.mapped('total_amount'))
            sheet.total_tax_amount = sum(sheet.expense_line_ids.mapped('tax_amount'))
            sheet.untaxed_amount = sheet.total_amount - sheet.total_tax_amount

    @api.depends('account_move_ids.payment_state', 'account_move_ids.amount_residual')
    def _compute_from_account_move_ids(self):
        for sheet in self:
            if sheet.payment_mode == 'company_account':
                if sheet.account_move_ids:
                    # when the sheet is paid by the company, the state/amount of the related account_move_ids are not relevant
                    # unless all moves have been reversed
                    sheet.amount_residual = 0.
                    if sheet.account_move_ids - sheet.account_move_ids.filtered('reversal_move_id'):
                        sheet.payment_state = 'paid'
                    else:
                        sheet.payment_state = 'reversed'
                else:
                    sheet.amount_residual = sum(sheet.account_move_ids.mapped('amount_residual'))
                    payment_states = set(sheet.account_move_ids.mapped('payment_state'))
                    if len(payment_states) <= 1:  # If only 1 move or only one state
                        sheet.payment_state = payment_states.pop() if payment_states else 'not_paid'
                    elif 'partial' in payment_states or 'paid' in payment_states:  # else if any are (partially) paid
                        sheet.payment_state = 'partial'
                    else:
                        sheet.payment_state = 'not_paid'
            else:
                # Only one move is created when the expenses are paid by the employee
                if sheet.account_move_ids:
                    sheet.amount_residual = sum(sheet.account_move_ids.mapped('amount_residual'))
                    sheet.payment_state = sheet.account_move_ids[:1].payment_state
                else:
                    sheet.amount_residual = 0.0
                    sheet.payment_state = 'not_paid'

    @api.depends('selectable_payment_method_line_ids')
    def _compute_payment_method_line_id(self):
        for sheet in self:
            sheet.payment_method_line_id = sheet.selectable_payment_method_line_ids[:1]

    @api.depends('employee_journal_id', 'payment_method_line_id')
    def _compute_journal_id(self):
        for sheet in self:
            if sheet.payment_mode == 'company_account':
                sheet.journal_id = sheet.payment_method_line_id.journal_id
            else:
                sheet.journal_id = sheet.employee_journal_id

    @api.depends('company_id')
    def _compute_selectable_payment_method_line_ids(self):
        for sheet in self:
            allowed_method_line_ids = sheet.company_id.company_expense_allowed_payment_method_line_ids
            if allowed_method_line_ids:
                sheet.selectable_payment_method_line_ids = allowed_method_line_ids
            else:
                sheet.selectable_payment_method_line_ids = self.env['account.payment.method.line'].search([
                    ('payment_type', '=', 'outbound'),
                    ('company_id', '=', sheet.company_id.id)
                ])

    @api.depends('account_move_ids', 'payment_state', 'approval_state')
    def _compute_state(self):
        for sheet in self:
            if sheet.payment_state != 'not_paid':
                sheet.state = 'done'
            elif sheet.account_move_ids:
                sheet.state = 'post'
            elif sheet.approval_state:
                sheet.state = sheet.approval_state
            else:
                sheet.state = 'draft'

    @api.depends('expense_line_ids.currency_id', 'company_currency_id')
    def _compute_currency_id(self):
        for sheet in self:
            if not sheet.expense_line_ids or sheet.is_multiple_currency or sheet.payment_mode == 'own_account':
                sheet.currency_id = sheet.company_currency_id
            else:
                sheet.currency_id = sheet.expense_line_ids[:1].currency_id

    @api.depends('expense_line_ids.currency_id')
    def _compute_is_multiple_currency(self):
        for sheet in self:
            sheet.is_multiple_currency = any(sheet.expense_line_ids.mapped('is_multiple_currency')) \
                                         or len(sheet.expense_line_ids.mapped('currency_id')) > 1

    @api.depends('employee_id')
    def _compute_can_reset(self):
        is_expense_user = self.user_has_groups('hr_expense.group_hr_expense_team_approver')
        for sheet in self:
            sheet.can_reset = is_expense_user if is_expense_user else sheet.employee_id.user_id == self.env.user

    @api.depends_context('uid')
    @api.depends('employee_id')
    def _compute_can_approve(self):
        is_team_approver = self.user_has_groups('hr_expense.group_hr_expense_team_approver')
        is_approver = self.user_has_groups('hr_expense.group_hr_expense_user')
        is_hr_admin = self.user_has_groups('hr_expense.group_hr_expense_manager')

        for sheet in self:
            reason = False
            if not is_team_approver:
                reason = _("%s: Your are not a Manager or HR Officer", sheet.name)

            elif not is_hr_admin:
                sheet_employee = sheet.employee_id
                current_managers = sheet_employee.expense_manager_id \
                                   | sheet_employee.parent_id.user_id \
                                   | sheet_employee.department_id.manager_id.user_id \
                                   | sheet.user_id

                if sheet_employee.user_id == self.env.user:
                    reason = _("%s: It is your own expense", sheet.name)

                elif self.env.user not in current_managers and not is_approver and sheet_employee.expense_manager_id.id != self.env.user.id:
                    reason = _("%s: It is not from your department", sheet.name)

            sheet.can_approve = not reason
            sheet.cannot_approve_reason = reason

    @api.depends('expense_line_ids')
    def _compute_nb_expense(self):
        for sheet in self:
            sheet.nb_expense = len(sheet.expense_line_ids)

    @api.depends('account_move_ids')
    def _compute_nb_account_move(self):
        for sheet in self:
            sheet.nb_account_move = len(sheet.account_move_ids)

    @api.depends('account_move_ids.date')
    def _compute_accounting_date(self):
        for sheet in self.filtered('account_move_ids'):
            sheet.accounting_date = sheet.account_move_ids[:1].date

    @api.depends('employee_id', 'employee_id.department_id')
    def _compute_from_employee_id(self):
        for sheet in self:
            sheet.department_id = sheet.employee_id.department_id
            sheet.user_id = sheet.employee_id.expense_manager_id or sheet.employee_id.parent_id.user_id

    @api.depends_context('uid')
    @api.depends('employee_id', 'user_id', 'state')
    def _compute_is_editable(self):
        is_hr_admin = self.user_has_groups('hr_expense.group_hr_expense_manager')
        is_approver = self.user_has_groups('hr_expense.group_hr_expense_user')
        for sheet in self:
            if sheet.state not in {'draft', 'submit', 'approve'}:
                # Not editable
                sheet.is_editable = False
                continue

            employee = sheet.employee_id

            is_own_sheet = employee.user_id == self.env.user
            if is_own_sheet and sheet.state == 'draft':
                # Anyone can edit their own draft sheet
                sheet.is_editable = True
                continue

            managers = employee.expense_manager_id | employee.parent_id.user_id | employee.department_id.manager_id.user_id
            if is_approver:
                managers |= self.env.user
            if not is_own_sheet and self.env.user in managers:
                # If Approver-level or designated manager, can edit other people sheet
                sheet.is_editable = True
                continue

            if is_hr_admin and sheet.state in {'draft', 'submit', 'approve'}:
                # Administrator-level users are not restricted
                sheet.is_editable = True
                continue
            sheet.is_editable = False

    @api.constrains('expense_line_ids')
    def _check_payment_mode(self):
        for sheet in self:
            expense_lines = sheet.mapped('expense_line_ids')
            if expense_lines and any(expense.payment_mode != expense_lines[:1].payment_mode for expense in expense_lines):
                raise ValidationError(_("All expenses in an expense report must have the same \"paid by\" criteria."))

    @api.depends('expense_line_ids')
    def _compute_product_ids(self):
        for sheet in self:
            sheet.product_ids = sheet.expense_line_ids.mapped('product_id')

    @api.constrains('expense_line_ids', 'employee_id')
    def _check_employee(self):
        for sheet in self:
            if sheet.expense_line_ids.employee_id - sheet.employee_id:
                raise ValidationError(_('You cannot add expenses of another employee.'))

    @api.constrains('expense_line_ids', 'company_id')
    def _check_expense_lines_company(self):
        for sheet in self:
            if sheet.expense_line_ids.company_id - sheet.company_id:
                raise ValidationError(_('An expense report must contain only lines from the same company.'))

    @api.model
    def _search_product_ids(self, operator, value):
        if operator == 'in' and not isinstance(value, list):
            value = [value]
        return [('expense_line_ids.product_id', operator, value)]

    # ----------------------------------------
    # ORM Overrides
    # ----------------------------------------

    def _read_format(self, fnames, load='_classic_read'):
        # setting the context in the field on the view is not enough
        self = self.with_context(show_payment_journal_id=True)
        return super()._read_format(fnames, load)

    @api.model_create_multi
    def create(self, vals_list):
        context = clean_context(self.env.context)
        context.update({
            'mail_create_nosubscribe': True,
            'mail_auto_subscribe_no_notify': True,
        })
        sheets = super(HrExpenseSheet, self.with_context(context)).create(vals_list)
        sheets.activity_update()
        return sheets

    @api.ondelete(at_uninstall=False)
    def _unlink_except_posted_or_paid(self):
        for expense in self:
            if expense.state in {'post', 'done'}:
                raise UserError(_('You cannot delete a posted or paid expense.'))

    # --------------------------------------------
    # Mail Thread
    # --------------------------------------------

    def _get_mail_thread_data_attachments(self):
        """
            In order to see in the sheet attachment preview the corresponding
            expenses' attachments, the latter attachments are added to the fetched data for the sheet record.
        """
        self.ensure_one()
        res = super()._get_mail_thread_data_attachments()
        expense_attachments = self.env['ir.attachment'].search(
            [('res_id', 'in', self.expense_line_ids.ids), ('res_model', '=', 'hr.expense')],
            order='id desc',
        )
        return res | expense_attachments

    def _track_subtype(self, init_values):
        self.ensure_one()
        if 'state' in init_values and self.state == 'draft':
            return self.env.ref('hr_expense.mt_expense_reset')
        if 'state' in init_values and self.state == 'approve':
            if init_values['state'] in {'post', 'done'}:
                return self.env.ref('hr_expense.mt_expense_entry_delete')
            return self.env.ref('hr_expense.mt_expense_approved')
        if 'state' in init_values and self.state == 'cancel':
            return self.env.ref('hr_expense.mt_expense_refused')
        if 'state' in init_values and self.state == 'done':
            return self.env.ref('hr_expense.mt_expense_paid')
        return super()._track_subtype(init_values)

    def _message_auto_subscribe_followers(self, updated_values, subtype_ids):
        res = super()._message_auto_subscribe_followers(updated_values, subtype_ids)
        if updated_values.get('employee_id'):
            employee_user = self.env['hr.employee'].browse(updated_values['employee_id']).user_id
            if employee_user:
                res.append((employee_user.partner_id.id, subtype_ids, False))
        return res

    def activity_update(self):
        reports_requiring_feedback = self.env['hr.expense.sheet']
        reports_activity_unlink = self.env['hr.expense.sheet']
        for expense_report in self:
            if expense_report.state == 'submit':
                expense_report.activity_schedule(
                    'hr_expense.mail_act_expense_approval',
                    user_id=expense_report.sudo()._get_responsible_for_approval().id or self.env.user.id)
            elif expense_report.state == 'approve':
                reports_requiring_feedback |= expense_report
            elif expense_report.state in {'draft', 'cancel'}:
                reports_activity_unlink |= expense_report
        if reports_requiring_feedback:
            reports_requiring_feedback.activity_feedback(['hr_expense.mail_act_expense_approval'])
        if reports_activity_unlink:
            reports_activity_unlink.activity_unlink(['hr_expense.mail_act_expense_approval'])

    # --------------------------------------------
    # Actions
    # --------------------------------------------

    def action_submit_sheet(self):
        self._do_submit()

    def action_approve_expense_sheets(self):
        self._check_can_approve()
        self._validate_analytic_distribution()
        duplicates = self.expense_line_ids.duplicate_expense_ids.filtered(lambda exp: exp.state in {'approved', 'done'})
        if duplicates:
            action = self.env["ir.actions.act_window"]._for_xml_id('hr_expense.hr_expense_approve_duplicate_action')
            action['context'] = {'default_sheet_ids': self.ids, 'default_expense_ids': duplicates.ids}
            return action
        self._do_approve()

    def action_refuse_expense_sheets(self):
        self._check_can_refuse()
        return self.env["ir.actions.act_window"]._for_xml_id('hr_expense.hr_expense_refuse_wizard_action')

    def action_reset_approval_expense_sheets(self):
        self._check_can_reset_approval()
        self._do_reset_approval()

    def action_sheet_move_create(self):
        self._check_can_create_move()
        self._do_create_moves()

    def action_reset_expense_sheets(self):
        self._do_reverse_moves()
        self._do_reset_approval()

    def action_register_payment(self):
        ''' Open the account.payment.register wizard to pay the selected journal entries.
        There can be more than one bank_account_id in the expense sheet when registering payment for multiple expenses.
        The default_partner_bank_id is set only if there is one available, if more than one the field is left empty.
        :return: An action opening the account.payment.register wizard.
        '''
        return self.account_move_ids.with_context(default_partner_bank_id=(
            self.employee_id.sudo().bank_account_id.id if len(self.employee_id.sudo().bank_account_id.ids) <= 1 else None
        )).action_register_payment()

    def action_open_expense_view(self):
        self.ensure_one()
        if self.nb_expense == 1:
            return {
                'type': 'ir.actions.act_window',
                'view_mode': 'form',
                'res_model': 'hr.expense',
                'res_id': self.expense_line_ids.id,
            }
        return {
            'name': _('Expenses'),
            'type': 'ir.actions.act_window',
            'view_mode': 'list,form',
            'views': [[False, "list"], [False, "form"]],
            'res_model': 'hr.expense',
            'domain': [('id', 'in', self.expense_line_ids.ids)],
        }

    def action_open_account_moves(self):
        self.ensure_one()
        if self.payment_mode == 'own_account':
            res_model = 'account.move'
            record_ids = self.account_move_ids
        else:
            res_model = 'account.payment'
            record_ids = self.account_move_ids.mapped('payment_id')

        action = {'type': 'ir.actions.act_window', 'res_model': res_model}
        if len(self.account_move_ids) == 1:
            action.update({
                'name': record_ids.name,
                'view_mode': 'form',
                'res_id': record_ids.id,
                'views': [(False, 'form')],
            })
        else:
            action.update({
                'name': _("Journal entries"),
                'view_mode': 'list',
                'domain': [('id', 'in', record_ids.ids)],
                'views': [(False, 'list'), (False, 'form')],
            })
        return action

    # --------------------------------------------
    # Business
    # --------------------------------------------

    def set_to_paid(self):
        # hook used in other modules to bypass payment registration
        self.write({'state': 'done'})

    def set_to_posted(self):
        # hook used in other modules to bypass move creation
        self.write({'state': 'post'})

    def _check_can_approve(self):
        if not all(self.mapped('can_approve')):
            reasons = _("You cannot approve:\n %s", "\n".join(self.mapped('cannot_approve_reason')))
            raise UserError(reasons)

    def _check_can_refuse(self):
        if not all(self.mapped('can_approve')):
            reasons = _("You cannot refuse:\n %s", "\n".join(self.mapped('cannot_approve_reason')))
            raise UserError(reasons)

    def _check_can_reset_approval(self):
        if not all(self.mapped('can_reset')):
            raise UserError(_("Only HR Officers or the concerned employee can reset to draft."))

    def _check_can_create_move(self):
        if any(sheet.state != 'approve' for sheet in self):
            raise UserError(_("You can only generate accounting entry for approved expense(s)."))

        if any(not sheet.journal_id for sheet in self):
            raise UserError(_("Specify expense journal to generate accounting entries."))

        missing_email_employees = self.filtered(lambda sheet: not sheet.employee_id.work_email).employee_id
        if missing_email_employees:
            action = self.env['ir.actions.actions']._for_xml_id('hr.open_view_employee_tree')
            action['domain'] = [('id', 'in', missing_email_employees.ids)]
            raise RedirectWarning(_("The work email of some employees is missing. Please add it on the employee form"), action, _("Show missing work email employees"))

    def _do_submit(self):
        self.write({'approval_state': 'submit'})
        self.sudo().activity_update()

    def _do_approve(self):
        for sheet in self.filtered(lambda s: s.state in {'submit', 'draft'}):
            sheet.write({
                'approval_state': 'approve',
                'user_id': sheet.user_id.id or self.env.user.id,
                'approval_date': fields.Date.context_today(sheet),
            })
        self.activity_update()

    def _do_reset_approval(self):
        self.sudo().write({'approval_state': False})
        self.activity_update()

    def _do_refuse(self, reason):
        self.write({'state': 'cancel'})
        subtype_id = self.env['ir.model.data']._xmlid_to_res_id('mail.mt_comment')
        for sheet in self:
            sheet.message_post_with_source(
                'hr_expense.hr_expense_template_refuse_reason',
                subtype_id=subtype_id,
                render_values={'reason': reason, 'name': sheet.name},
            )
        self.activity_update()

    def _do_create_moves(self):
        self = self.with_context(clean_context(self.env.context))  # remove default_*
        skip_context = {
            'skip_invoice_sync': True,
            'skip_invoice_line_sync': True,
            'skip_account_move_synchronization': True,
            'check_move_validity': False,
        }
        own_account_sheets = self.filtered(lambda sheet: sheet.payment_mode == 'own_account')
        company_account_sheets = self - own_account_sheets

        moves = self.env['account.move'].create([sheet._prepare_bills_vals() for sheet in own_account_sheets])
        payments = self.env['account.payment'].with_context(**skip_context).create([
            expense._prepare_payments_vals() for expense in company_account_sheets.expense_line_ids
        ])
        moves |= payments.move_id
        moves.action_post()
        self.activity_update()

        return moves

    def _do_reverse_moves(self):
        self = self.with_context(clean_context(self.env.context))
        moves = self.account_move_ids
        draft_moves = moves.filtered(lambda m: m.state == 'draft')
        non_draft_moves = moves - draft_moves
        non_draft_moves._reverse_moves(
            default_values_list=[{'invoice_date': fields.Date.context_today(move), 'ref': False} for move in non_draft_moves],
            cancel=True
        )
        draft_moves.unlink()

    def _prepare_bills_vals(self):
        self.ensure_one()
        return {
            **self._prepare_move_vals(),
            'invoice_date': self.accounting_date or fields.Date.context_today(self),
            'journal_id': self.journal_id.id,
            'ref': self.name,
            'move_type': 'in_invoice',
            'partner_id': self.employee_id.sudo().work_contact_id.id,
            'currency_id': self.currency_id.id,
            'line_ids': [Command.create(expense._prepare_move_lines_vals()) for expense in self.expense_line_ids],
            'attachment_ids': [
                Command.create(attachment.copy_data({'res_model': 'account.move', 'res_id': False, 'raw': attachment.raw})[0])
                for attachment in self.expense_line_ids.message_main_attachment_id
            ],
        }

    def _prepare_move_vals(self):
        self.ensure_one()
        return {
            # force the name to the default value, to avoid an eventual 'default_name' in the context
            # to set it to '' which cause no number to be given to the account.move when posted.
            'name': '/',
            'date': self.accounting_date or max(self.expense_line_ids.mapped('date')) or fields.Date.context_today(self),
            'expense_sheet_id': self.id,
        }

    def _validate_analytic_distribution(self):
        for line in self.expense_line_ids:
            line._validate_distribution(account=line.account_id.id, business_domain='expense', company_id=line.company_id.id)

    def _get_responsible_for_approval(self):
        if self.user_id:
            return self.user_id
        if self.employee_id.parent_id.user_id:
            return self.employee_id.parent_id.user_id
        if self.employee_id.department_id.manager_id.user_id:
            return self.employee_id.department_id.manager_id.user_id
        return self.env['res.users']

    def _get_expense_account_destination(self):
        self.ensure_one()
        if self.payment_mode == 'company_account':
            journal = self.payment_method_line_id.journal_id
            account_dest = (
                journal.outbound_payment_method_line_ids[:1].payment_account_id
                or journal.company_id.account_journal_payment_credit_account_id
            )
        else:
            if not self.employee_id.sudo().work_contact_id:
                raise UserError(_("No work contact found for the employee %s, please configure one.", self.employee_id.name))
            partner = self.employee_id.sudo().work_contact_id.with_company(self.company_id)
            account_dest = partner.property_account_payable_id or partner.parent_id.property_account_payable_id
        return account_dest.id
