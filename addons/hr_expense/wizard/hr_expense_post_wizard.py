from odoo import _, api, fields, models
from odoo.exceptions import UserError


class HrExpensePostWizard(models.TransientModel):
    _name = 'hr.expense.post.wizard'
    _description = 'Expense Posting Wizard'

    @api.model
    def _default_journal_id(self):
        """
         The journal is determining the company of the accounting entries generated from expense.
         We need to force journal company and expense company to be the same.
        """
        company_journal_id = self.env.company.expense_journal_id
        if company_journal_id:
            return company_journal_id.id
        closest_parent_company_journal = self.env.company.parent_ids[::-1].expense_journal_id[:1]
        if closest_parent_company_journal:
            return closest_parent_company_journal.id

        journal = self.env['account.journal'].search([
            *self.env['account.journal']._check_company_domain(self.env.company.id),
            ('type', '=', 'purchase'),
        ], limit=1)
        return journal.id

    company_id = fields.Many2one(comodel_name='res.company', default=lambda self: self.env.company, string='Company', readonly=True)

    accounting_date = fields.Date(  # The date used for the accounting entries or the one we'd like to use if not yet posted
        string="Accounting Date",
        default=fields.Date.context_today,
        help="Specify the bill date of the related vendor bill."
    )
    employee_journal_id = fields.Many2one(
        comodel_name='account.journal',
        string="Journal",
        default=_default_journal_id,
        check_company=True,
        domain=[('type', '=', 'purchase')],
        help="The journal used when the expense is paid by employee.",
    )

    def action_post_entry(self):
        expenses = self.env['hr.expense'].browse(self.env.context['active_ids'])
        if not self.env['account.move'].has_access('create'):
            raise UserError(_("You don't have the rights to create accounting entries."))
        expense_receipt_vals_list = [
            {
                **new_receipt_vals,
                'journal_id': self.employee_journal_id.id,
                'invoice_date': self.accounting_date,
            }
            for new_receipt_vals in expenses._prepare_receipts_vals()
        ]
        moves_sudo = self.env['account.move'].sudo().create(expense_receipt_vals_list)
        for move_sudo in moves_sudo:
            move_sudo._message_set_main_attachment_id(move_sudo.attachment_ids, force=True, filter_xml=False)
        moves_sudo.action_post()

        if not self.company_id.expense_journal_id:  # Sets the default one if not specified
            self.sudo().company_id.expense_journal_id = self.employee_journal_id.id

        # Add the company_paid ids to the redirect
        moves_ids = moves_sudo.ids + self.env.context.get('company_paid_move_ids', tuple())

        action = {
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
        }
        if len(moves_ids) == 1:
            action.update({
                'name': moves_sudo.ref,
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
