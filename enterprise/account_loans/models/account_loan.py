from dateutil.relativedelta import relativedelta

from odoo import fields, models, api, _, Command
from odoo.tools import float_compare
from odoo.tools.misc import format_date
from odoo.exceptions import UserError, ValidationError


class AccountLoan(models.Model):
    _name = 'account.loan'
    _description = 'Loan'
    _inherit = ['mail.thread']
    _order = 'date'

    @api.model
    def default_get(self, fields_list):
        values = super().default_get(fields_list)
        if all(field not in fields_list for field in ['expense_account_id', 'long_term_account_id', 'short_term_account_id', 'journal_id']):
            return values
        previous_loan = self.search([
            ('company_id', '=', self.env.company.id),
            ('expense_account_id', '!=', False),
            ('long_term_account_id', '!=', False),
            ('short_term_account_id', '!=', False),
            ('journal_id', '!=', False),
        ], limit=1)
        if previous_loan:
            values['expense_account_id'] = previous_loan.expense_account_id.id
            values['long_term_account_id'] = previous_loan.long_term_account_id.id
            values['short_term_account_id'] = previous_loan.short_term_account_id.id
            values['journal_id'] = previous_loan.journal_id.id
        return values

    name = fields.Char("Name", required=True, index="trigram", tracking=True)
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company)
    currency_id = fields.Many2one(related='company_id.currency_id')
    active = fields.Boolean(default=True)
    state = fields.Selection(
        string="Status",
        selection=[
            ('draft', 'Draft'),
            ('running', 'Running'),
            ('closed', 'Closed'),
            ('cancelled', 'Cancelled'),
        ],
        default='draft',
        required=True,
        tracking=True,
    )
    date = fields.Date('Loan Date', index="btree_not_null")
    amount_borrowed = fields.Monetary(string='Amount Borrowed', tracking=True)
    interest = fields.Monetary(string='Interest')
    duration = fields.Integer('Duration')
    skip_until_date = fields.Date(
        string='Skip until',
        help='Upon confirmation of the loan, Odoo will ignore the loan lines that are up to this date (included) and not create entries for them. '
             'This is useful if you have already manually created entries prior to the creation of this loan.'
    )

    long_term_account_id = fields.Many2one('account.account', string='Long Term Account', tracking=True)
    short_term_account_id = fields.Many2one('account.account', string='Short Term Account', tracking=True)
    expense_account_id = fields.Many2one(
        comodel_name='account.account',
        string='Expense Account',
        tracking=True,
        domain="[('account_type', 'in', ('expense', 'expense_depreciation'))]",
    )
    journal_id = fields.Many2one(
        comodel_name='account.journal',
        string='Journal',
        domain="[('type', '=', 'general')]",
    )
    asset_group_id = fields.Many2one('account.asset.group', string='Asset Group', tracking=True, index=True)
    loan_properties = fields.Properties('Properties', definition='journal_id.loan_properties_definition')

    line_ids = fields.One2many('account.loan.line', 'loan_id', string='Loan Lines')  # Amortization schedule

    # Computed fields
    display_name = fields.Char("Loan name", compute='_compute_display_name', store=True)  # stored for pivot view
    start_date = fields.Date(compute='_compute_start_end_date')
    end_date = fields.Date(compute='_compute_start_end_date')
    is_wrong_date = fields.Boolean(compute='_compute_is_wrong_date')
    amount_borrowed_difference = fields.Monetary(compute='_compute_amount_borrowed_difference')
    interest_difference = fields.Monetary(compute='_compute_interest_difference')
    duration_difference = fields.Integer(compute='_compute_duration_difference')
    outstanding_balance = fields.Monetary(string='Outstanding Balance', compute='_compute_outstanding_balance')  # Based on the posted entries
    nb_posted_entries = fields.Integer(compute='_compute_nb_posted_entries')
    linked_assets_ids = fields.One2many(
        comodel_name='account.asset',
        string="Linked Assets",
        compute='_compute_linked_assets',
    )
    count_linked_assets = fields.Integer(compute="_compute_linked_assets")

    # Constrains
    @api.constrains('amount_borrowed', 'interest', 'duration')
    def _require_positive_values(self):
        for loan in self:
            if float_compare(loan.amount_borrowed, 0.0, precision_rounding=loan.currency_id.rounding) < 0:
                raise ValidationError(_('The amount borrowed must be positive'))
            if float_compare(loan.interest, 0.0, precision_rounding=loan.currency_id.rounding) < 0:
                raise ValidationError(_('The interest must be positive'))
            if loan.duration < 0:
                raise ValidationError(_('The duration must be positive'))

    # Compute methods
    @api.depends('name', 'start_date', 'end_date')
    def _compute_display_name(self):
        for loan in self:
            if loan.name and loan.start_date and loan.end_date:
                start_date = format_date(self.env, loan.start_date, date_format='MM y')
                end_date = format_date(self.env, loan.end_date, date_format='MM y')
                loan.display_name = f"{loan.name}: {start_date} - {end_date}"
            else:
                loan.display_name = loan.name

    @api.depends('line_ids')
    def _compute_start_end_date(self):
        for loan in self:
            if loan.line_ids:
                loan.start_date = loan.line_ids[0].date
                loan.end_date = loan.line_ids[-1].date
            else:
                loan.start_date = False
                loan.end_date = False

    @api.depends('date')
    def _compute_is_wrong_date(self):
        for loan in self:
            loan.is_wrong_date = not loan.date or any(date < loan.date for date in loan.line_ids.mapped('date'))

    @api.depends('amount_borrowed', 'line_ids.principal', 'currency_id')
    def _compute_amount_borrowed_difference(self):
        for loan in self:
            if loan.currency_id:
                loan.amount_borrowed_difference = abs(loan.amount_borrowed - loan.currency_id.round(sum(loan.line_ids.mapped('principal'))))
            else:
                loan.amount_borrowed_difference = 0

    @api.depends('interest', 'line_ids.interest')
    def _compute_interest_difference(self):
        for loan in self:
            if loan.interest and loan.line_ids:
                loan.interest_difference = loan.interest - loan.currency_id.round(sum(loan.line_ids.mapped('interest')))
            else:
                loan.interest_difference = 0

    @api.depends('duration', 'line_ids')
    def _compute_duration_difference(self):
        for loan in self:
            loan.duration_difference = loan.duration - len(loan.line_ids)

    @api.depends('line_ids.generated_move_ids')
    def _compute_nb_posted_entries(self):
        for loan in self:
            loan.nb_posted_entries = len(loan.line_ids.generated_move_ids.filtered(lambda m: m.state == 'posted'))

    @api.depends('amount_borrowed', 'line_ids.principal', 'state', 'line_ids.is_payment_move_posted')
    def _compute_outstanding_balance(self):
        for loan in self:
            outstanding_balance = loan.amount_borrowed
            if loan.state == 'running':
                for line in loan.line_ids:
                    if line.is_payment_move_posted or (loan.skip_until_date and line.date < loan.skip_until_date):
                        outstanding_balance -= line.principal
            loan.outstanding_balance = outstanding_balance

    @api.depends('asset_group_id')
    def _compute_linked_assets(self):
        for loan in self:
            loan.linked_assets_ids = loan.asset_group_id.linked_asset_ids
            loan.count_linked_assets = len(loan.linked_assets_ids)

    # Action methods
    def action_confirm(self):
        for loan in self:
            # Verifications
            if not loan.name:
                raise UserError(_("The loan name should be set."))
            if loan.is_wrong_date:
                raise UserError(_("The loan date should be earlier than the loan lines date."))
            if float_compare(loan.amount_borrowed_difference, 0.0, precision_rounding=loan.currency_id.rounding) != 0:
                raise UserError(_(
                    "The loan amount %(loan_amount)s should be equal to the sum of the principals: %(principal_sum)s (difference %(principal_difference)s)",
                    loan_amount=loan.currency_id.format(loan.amount_borrowed),
                    principal_sum=loan.currency_id.format(sum(loan.line_ids.mapped('principal'))),
                    principal_difference=loan.currency_id.format(loan.amount_borrowed_difference),
                ))
            if float_compare(loan.interest_difference, 0.0, precision_rounding=loan.currency_id.rounding) != 0:
                raise UserError(_("The loan interest should be equal to the sum of the loan lines interest."))
            if loan.duration_difference != 0:
                raise UserError(_("The loan duration should be equal to the number of loan lines."))
            if not loan.long_term_account_id or not loan.short_term_account_id or not loan.expense_account_id:
                raise UserError(_("The loan accounts should be set."))
            if not loan.journal_id:
                raise UserError(_("The loan journal should be set."))

            payment_moves_values = []
            reclassification_moves_values = []
            reclassification_reversed_moves_values = []
            for i, line in enumerate(loan.line_ids):
                if loan.skip_until_date and line.date < loan.skip_until_date:
                    continue

                # Principal and interest (to match with the bank statement)
                payment_moves_values.append({
                    'company_id': loan.company_id.id,
                    'auto_post': 'at_date',
                    'generating_loan_line_id': line.id,
                    'is_loan_payment_move': True,
                    'date': line.date + relativedelta(day=31),
                    'journal_id': loan.journal_id.id,
                    'ref': f"{loan.name} - {_('Principal & Interest')} {format_date(self.env, line.date, date_format='MM/y')}",
                    'line_ids': [
                        Command.create({
                            'account_id': loan.long_term_account_id.id,
                            'debit': line.principal,
                            'name': f"{loan.name} - {_('Principal')} {format_date(self.env, line.date, date_format='MM/y')}",
                        }),
                        Command.create({
                            'account_id': loan.short_term_account_id.id,
                            'credit': line.payment,
                            'name': f"{loan.name} - {_('Due')} {format_date(self.env, line.date, date_format='MM/y')} "
                                    f"({_('Principal')} {loan.currency_id.format(line.principal)} + {_('Interest')} {loan.currency_id.format(line.interest)})",
                        }),
                        Command.create({
                            'account_id': loan.expense_account_id.id,
                            'debit': line.interest,
                            'name': f"{loan.name} - {_('Interest')} {format_date(self.env, line.date, date_format='MM/y')}",
                        }),
                    ],
                })

                # Principal reclassification Long Term - Short Term
                if line == loan.line_ids[-1]:
                    break
                next_lines = loan.line_ids[i + 1: i + 13]  # 13 = 1 (start offset) + 12 months
                from_date = format_date(self.env, next_lines[0].date, date_format='MM/y')
                to_date = format_date(self.env, next_lines[-1].date, date_format='MM/y')
                common_reclassification_values = {
                    'company_id': loan.company_id.id,
                    'auto_post': 'at_date',
                    'generating_loan_line_id': line.id,
                    'is_loan_payment_move': False,
                    'journal_id': loan.journal_id.id,
                }
                reclassification_moves_values.append({
                    **common_reclassification_values,
                    'date': line.date + relativedelta(day=31),
                    'ref': f"{loan.name} - {_('Reclassification LT - ST')} {from_date} to {to_date}",
                    'line_ids': [
                        Command.create({
                            'account_id': loan.long_term_account_id.id,
                            'debit': sum(next_lines.mapped('principal')),
                            'name': f"{loan.name} - {_('Reclassification LT - ST')} {from_date} to {to_date} (To {loan.short_term_account_id.code})",
                        }),
                        Command.create({
                            'account_id': loan.short_term_account_id.id,
                            'credit': sum(next_lines.mapped('principal')),
                            'name': f"{loan.name} - {_('Reclassification LT - ST')} {from_date} to {to_date} (From {loan.long_term_account_id.code})",
                        }),
                    ],
                })
                # Manually create the reverse (instead of using _reverse_moves()) for optimization reasons
                reclassification_reversed_moves_values.append({
                    **common_reclassification_values,
                    'date': line.date + relativedelta(day=31) + relativedelta(days=1),  # first day of next month
                    'ref': f"{loan.name} - {_('Reversal reclassification LT - ST')} {from_date} to {to_date}",
                    'line_ids': [
                        Command.create({
                            'account_id': loan.long_term_account_id.id,
                            'credit': sum(next_lines.mapped('principal')),
                            'name': f"{loan.name} - {_('Reversal reclassification LT - ST')} {from_date} to {to_date} (To {loan.short_term_account_id.code})",
                        }),
                        Command.create({
                            'account_id': loan.short_term_account_id.id,
                            'debit': sum(next_lines.mapped('principal')),
                            'name': f"{loan.name} - {_('Reversal reclassification LT - ST')} {from_date} to {to_date} (From {loan.long_term_account_id.code})",
                        }),
                    ],
                })

            def post_moves(moves):
                moves.filtered(lambda m: m.date <= fields.Date.context_today(self)).action_post()

            payment_moves = self.env['account.move'].create(payment_moves_values)
            reclassification_moves = self.env['account.move'].create(reclassification_moves_values)
            reclassification_reversed_moves = self.env['account.move'].create(reclassification_reversed_moves_values)
            post_moves(payment_moves | reclassification_moves | reclassification_reversed_moves)

            for (reclassification_move, reclassification_reversed_move) in zip(reclassification_moves, reclassification_reversed_moves):
                reclassification_reversed_move.reversed_entry_id = reclassification_move
                reclassification_reversed_move.message_post(body=_('This entry has been reversed from %s', reclassification_move._get_html_link()))

            bodies = {}
            for move, reverse in zip(reclassification_moves, reclassification_reversed_moves):
                bodies[move.id] = _('This entry has been %s', reverse._get_html_link(title=_("reversed")))
            reclassification_moves._message_log_batch(bodies=bodies)

            if any(m.state != 'posted' for m in payment_moves | reclassification_moves | reclassification_reversed_moves):
                loan.state = 'running'

    def action_upload_amortization_schedule(self, attachment_id):
        """Called when uploading an amortization schedule file"""
        attachment = self.env['ir.attachment'].browse(attachment_id)
        loan = self or self.create({
            'name': attachment.name,
        })
        loan.line_ids.unlink()
        loan.message_post(body=_('Uploaded file'), attachment_ids=[attachment.id])
        import_wizard = self.env['base_import.import'].create({
            'res_model': 'account.loan.line',
            'file': attachment.raw,
            'file_name': attachment.name,
            'file_type': attachment.mimetype,
        })
        ctx = {
            **self.env.context,
            'wizard_id': import_wizard.id,
            'default_loan_id': loan.id,
        }
        return {
            'type': 'ir.actions.client',
            'tag': 'import_loan',
            'params': {
                'model': 'account.loan.line',
                'context': ctx,
                'filename': attachment.name,
            }
        }

    def action_file_uploaded(self):
        """Called after the amortization schedule has been imported by the wizard"""
        self.ensure_one()
        action = {
            'type': 'ir.actions.act_window',
            'name': _("Loans"),
            'res_model': 'account.loan',
            'views': [(False, 'list'), (False, 'form')],
            'target': 'self',
        }
        if self.line_ids:
            self.amount_borrowed = sum(self.line_ids.mapped('principal'))
            self.interest = sum(self.line_ids.mapped('interest'))
            self.duration = len(self.line_ids)
            self.date = self.line_ids[0].date
            return {
                **action,
                'res_id': self.id,
                'views': [(False, 'form')],
            }
        return action

    def action_open_compute_wizard(self):
        if not self:
            raise UserError(_("Please add a name before computing the loan"))
        wizard = self.env['account.loan.compute.wizard'].create({
            'loan_id': self.id,
            'loan_amount': self.amount_borrowed,
        })
        if self.date:
            wizard["start_date"] = self.date
            wizard["first_payment_date"] = self.date.replace(day=1) + relativedelta(months=1)  # first day of next month
        return {
            'name': _("Compute New Loan"),
            'res_id': wizard.id,
            'type': 'ir.actions.act_window',
            'res_model': 'account.loan.compute.wizard',
            'target': 'new',
            'views': [[False, 'form']],
            'context': self.env.context,
        }

    def action_reset(self):
        self.ensure_one()
        self.line_ids.unlink()

    def action_close(self):
        self.ensure_one()
        wizard = self.env['account.loan.close.wizard'].create({
            'loan_id': self.id,
        })
        return {
            'name': _('Close'),
            'view_mode': 'form',
            'res_model': 'account.loan.close.wizard',
            'type': 'ir.actions.act_window',
            'target': 'new',
            'res_id': wizard.id,
        }

    def action_cancel(self):
        self.line_ids.generated_move_ids.filtered(lambda m: m.state != 'cancel')._unlink_or_reverse()
        self.state = 'cancelled'

    def action_set_to_draft(self):
        self.line_ids.generated_move_ids.filtered(lambda m: m.state != 'cancel')._unlink_or_reverse()
        self.state = 'draft'

    def action_open_loan_entries(self):
        self.ensure_one()
        return {
            'name': _('Loan Entries'),
            'view_mode': 'list,form',
            'res_model': 'account.move',
            'views': [(self.env.ref('account_loans.account_loan_view_account_move_list_view').id, 'list'), (False, 'form')],
            'type': 'ir.actions.act_window',
            'domain': [('id', 'in', self.line_ids.generated_move_ids.ids)],
        }

    def action_open_linked_assets(self):
        self.ensure_one()
        return {
            'name': _('Linked Assets'),
            'view_mode': 'list,form',
            'res_model': 'account.asset',
            'type': 'ir.actions.act_window',
            'domain': [('id', 'in', self.linked_assets_ids.ids)],
        }

    # Model methods
    @api.ondelete(at_uninstall=False)
    def _unlink_loan(self):
        for loan in self:
            loan.line_ids.generated_move_ids._unlink_or_reverse()
            loan.line_ids.unlink()
