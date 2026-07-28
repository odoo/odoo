# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, models


class OnboardingStep(models.Model):
    _inherit = 'onboarding.onboarding.step'

    # COMMON STEPS
    @api.model
    def action_open_step_company_data(self):
        """Set company's basic information."""
        action = {
            'type': 'ir.actions.act_window',
            'name': _('Set your company data'),
            'res_model': 'res.company',
            'res_id': self.env.company.id,
            'views': [(self.env.ref('account.res_company_form_view_onboarding').id, "form")],
            'target': 'new',
        }
        return action

    @api.model
    def action_open_step_base_document_layout(self):
        view_id = self.env.ref('web.view_base_document_layout').id
        return {
            'name': _('Configure your document layout'),
            'type': 'ir.actions.act_window',
            'res_model': 'base.document.layout',
            'target': 'new',
            'views': [(view_id, 'form')],
        }

    @api.model
    def action_validate_step_base_document_layout(self):
        """Set the onboarding(s) step as done only if layout is set."""
        step = self.env.ref('account.onboarding_onboarding_step_base_document_layout', raise_if_not_found=False)
        if not step or not self.env.company.external_report_layout_id:
            return False
        return self.action_validate_step('account.onboarding_onboarding_step_base_document_layout')

    # INVOICE ONBOARDING
    @api.model
    def action_open_step_bank_account(self):
        return self.env.company.setting_init_bank_account_action()

    @api.model
    def action_open_step_create_invoice(self):
        return {
            'type': 'ir.actions.act_window',
            'name': _('Create first invoice'),
            'views': [(self.env.ref("account.view_move_form").id, 'form')],
            'res_model': 'account.move',
            'context': {'default_move_type': 'out_invoice'},
        }

    # DASHBOARD ONBOARDING
    @api.model
    def action_open_step_fiscal_year(self):
        company = self.env.company
        company.create_op_move_if_non_existant()
        new_wizard = self.env['account.financial.year.op'].create({'company_id': company.id})
        view_id = self.env.ref('account.setup_financial_year_opening_form').id

        return {
            'type': 'ir.actions.act_window',
            'name': _('Accounting Periods'),
            'view_mode': 'form',
            'res_model': 'account.financial.year.op',
            'target': 'new',
            'res_id': new_wizard.id,
            'views': [[view_id, 'form']],
        }

    @api.model
    def action_open_step_default_taxes(self):
        """ Called by the 'Taxes' button of the setup bar."""
        self.action_validate_step('account.onboarding_onboarding_step_default_taxes')

        view_id_list = self.env.ref('account.view_onboarding_tax_tree').id
        view_id_form = self.env.ref('account.view_tax_form').id

        return {
            'type': 'ir.actions.act_window',
            'name': _('Taxes'),
            'res_model': 'account.tax',
            'target': 'current',
            'views': [[view_id_list, 'list'], [view_id_form, 'form']],
            'context': {'search_default_sale': True, 'search_default_purchase': True, 'active_test': False},
        }

    @api.model
    def action_open_step_chart_of_accounts(self):
        """ Called by the 'Chart of Accounts' button of the dashboard onboarding panel."""
        company = self.env.company
        self.sudo().action_validate_step('account.onboarding_onboarding_step_chart_of_accounts')

        # If an opening move has already been posted, we open the tree view showing all the accounts
        if company.opening_move_posted():
            return 'account.action_account_form'

        # Otherwise, we create the opening move
        company.create_op_move_if_non_existant()

        # Then, we open will open a custom tree view allowing to edit opening balances of the account
        view_id = self.env.ref('account.init_accounts_tree').id
        # Hide the current year earnings account as it is automatically computed
        domain = [
            *self.env['account.account']._check_company_domain(company),
            ('account_type', '!=', 'equity_unaffected'),
        ]
        return {
            'type': 'ir.actions.act_window',
            'name': _('Chart of Accounts'),
            'res_model': 'account.account',
            'view_mode': 'tree',
            'limit': 99999999,
            'search_view_id': [self.env.ref('account.view_account_search').id],
            'views': [[view_id, 'list'], [False, 'form']],
            'domain': domain,
        }

    # STEPS WITHOUT PANEL
    @api.model
    def action_open_step_sales_tax(self):
        view_id = self.env.ref('account.res_company_form_view_onboarding_sale_tax').id

        return {
            'type': 'ir.actions.act_window',
            'name': _('Sales tax'),
            'res_id': self.env.company.id,
            'res_model': 'res.company',
            'target': 'new',
            'view_mode': 'form',
            'views': [[view_id, 'form']],
        }
