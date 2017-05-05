# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _

from odoo.exceptions import UserError


class ResCompany(models.Model):
    _inherit = 'res.company'

    def _default_opening_date(self):
        today = datetime.now()
        return today + relativedelta(day=1, hour=0, minute=0, second=0, microsecond=0)

    account_accountant_opening_move_id = fields.Many2one(string='Opening journal entry', comodel_name='account.move', help="The journal entry containing all the opening journal items of this company's accounting.")
    account_accountant_opening_journal_id = fields.Many2one(string='Opening journal', comodel_name='account.journal', related='account_accountant_opening_move_id.journal_id', help="Journal when the opening moves of this company's accounting has been posted.")
    account_accountant_opening_date = fields.Date(string='Accounting opening date',default=_default_opening_date, related='account_accountant_opening_move_id.date', help="Date of the opening entries of this company's accounting.")
    account_accountant_opening_move_adjustment_amount = fields.Monetary(string='Adjustment difference', help="Adjustment difference of this company's opening move.")
    account_accountant_opening_adjustment_account_id = fields.Many2one(string='Adjustment account', comodel_name='account.account', help="The account into which the opening move adjustment difference will be posted")

    #Fields used to force step completion during setup, in case the user does not want to enter some data:
    account_accountant_setup_company_data_marked_done = fields.Boolean(string='Company setup marked as done', default=False, help="True iff the user has forced the completion of the company setup step.")
    account_accountant_setup_bank_data_marked_done = fields.Boolean('Bank setup marked as done', default=False, help="True iff the user has forced the completion of the bank setup step.")

    #Fields marking the completion of a setup step
    account_accountant_setup_chart_of_accounts_done = fields.Boolean(string='Chart of account checked', default=False, help="True iff the wizard has displayed the chart of account once.")
    account_accountant_setup_bar_closed = fields.Boolean(string='Setup bar closed', default=False, help="True iff the setup bar has been closed by the user.")

    @api.model
    def setting_init_company_action(self):
        """ Called by the 'Company Data' button of the setup bar.
        """
        current_company = self.env['res.company']._company_default_get()
        view_id = self.env.ref('account_accountant.init_view_company_form').id

        return {'type': 'ir.actions.act_window',
                'res_model': 'res.company',
                'target': 'new',
                'view_mode': 'form',
                'res_id': current_company.id,
                'views': [[view_id, 'form']],
        }

    @api.model
    def setting_init_bank_account_action(self):
        """ Called by the 'Bank Account' button of the setup bar.
        """
        current_company = self.env['res.company']._company_default_get()
        view_id = self.env.ref('account_accountant.init_bank_journal_form').id

        rslt_act_dict = {
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'account.journal',
            'target': 'new',
            'views': [[view_id, 'form']],
        }

        # If some bank journal already exists, we open it in the form, so the user can edit it.
        # Otherwise, we just open the form in creation mode.
        bank_journal = self.env['account.journal'].search([('company_id','=',current_company.id), ('type','=','bank')], limit=1)
        if bank_journal:
            rslt_act_dict['res_id'] = bank_journal.id
        else:
            rslt_act_dict['context'] = {'default_type': 'bank'}

        return rslt_act_dict

    @api.model
    def setting_init_fiscal_year_action(self):
        """ Called by the 'Fiscal Year Opening' button of the setup bar.
        """
        current_company = self.env['res.company']._company_default_get()
        current_company.create_op_move_if_non_existant()

        new_wizard = self.env['accountant.financial.year.op'].create({'company_id': current_company.id})
        view_id = self.env.ref('account_accountant.init_financial_year_opening_form').id

        return {
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'accountant.financial.year.op',
            'target': 'new',
            'res_id': new_wizard.id,
            'views': [[view_id, 'form']],
        }

    @api.model
    def setting_chart_of_accounts_action(self):
        """ Called by the 'Chart of Accounts' button of the setup bar.
        """
        current_company = self._company_default_get()

        # If an opening move has already been posted, we open the tree view showing all the accounts
        if current_company.opening_move_posted():
            return 'account.action_account_form'

        # Otherwise, we open a custom tree view allowing to edit opening balances of the account, to prepare the opening move
        current_company.account_accountant_setup_chart_of_accounts_done = True
        self.create_op_move_if_non_existant()

        # We return the name of the action to execute (to display the list of all the accounts,
        # now we have created an opening move allowing to post initial balances through this view.
        return 'account_accountant.action_accounts_setup_tree'

    @api.model
    def setting_opening_move_action(self):
        """ Called by the 'Initial Balances' button of the setup bar.
        """
        current_company = self.env['res.company']._company_default_get()

        # If the opening move has already been posted, we open its form view
        if current_company.opening_move_posted():
            form_view_id = self.env.ref('account.view_move_form').id

            return {
                'type': 'ir.actions.act_window',
                'view_mode': 'form',
                'res_model': 'account.move',
                'target': 'new',
                'res_id': current_company.account_accountant_opening_move_id.id,
                'views': [[form_view_id, 'form']],
            }

        # Otherwise, we open a custom wizard to post it.
        self.create_op_move_if_non_existant()
        new_wizard = self.env['accountant.opening'].create({'company_id': current_company.id})
        view_id = self.env.ref('account_accountant.init_opening_move_wizard_form').id

        return {
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'accountant.opening',
            'target': 'new',
            'res_id': new_wizard.id,
            'views': [[view_id, 'form']],
        }

    @api.model
    def setting_hide_setup_bar(self):
        """ Called by the cross button of the setup bar, to close it.
        """
        current_company = self._company_default_get()
        current_company.account_accountant_setup_bar_closed = True
        return 'account_accountant.init_wizard_refresh_view'

    @api.model
    def create_op_move_if_non_existant(self):
        """ Creates an empty opening move in 'draft' state for the current company
        if there wasn't already one defined. For this, the function needs at least
        one journal of type 'bank' to exist (required by account.move).
        """
        current_company = self._company_default_get()
        if not current_company.account_accountant_opening_move_id:
            default_journal = self.env['account.journal'].search([('type', '=', 'bank'), ('company_id', '=', current_company.id)], limit=1)

            if not default_journal:
                raise UserError("No journal of type 'bank' could be found. Please create one before proceeding.")

            current_company.account_accountant_opening_move_id = self.env['account.move'].create({
                'name': _('Opening move'),
                'company_id': current_company.id,
                'journal_id': default_journal.id,
            })

    def mark_company_setup_as_done_action(self):
        """ Forces the completion of the 'company' setup step and returns an action
        refreshing the view.
        """
        self.account_accountant_setup_company_data_marked_done = True
        return self.env.ref('account_accountant.init_wizard_refresh_view').read([])[0]

    def opening_move_posted(self):
        """ Returns true if and only if this company has an opening account move,
        and this move has been posted.
        """
        return bool(self.account_accountant_opening_move_id) and self.account_accountant_opening_move_id.state == 'posted'