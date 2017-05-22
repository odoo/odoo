# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api

class AccountJournal(models.Model):
    _inherit = 'account.journal'

    account_accountant_setup_bank_data_marked_done = fields.Boolean(string='Bank setup marked as done', compute="_compute_setup_marked_done")

    @api.depends('company_id.account_accountant_setup_bank_data_marked_done')
    def _compute_setup_marked_done(self):
        for record in self:
            record.account_accountant_setup_bank_data_marked_done = record.company_id.account_accountant_setup_bank_data_marked_done

    @api.model
    def retrieve_account_dashboard(self):
        """ Returns the data used by the setup bar on account's dashboard.
        """
        company = self.env['res.company']._company_default_get()

        if company.account_accountant_setup_bar_closed:
            return {'show_setup_bar': False}

        data = {'show_setup_bar': True}

        data['company'] = company.account_accountant_setup_company_data_marked_done
        data['bank'] = company.account_accountant_setup_bank_data_marked_done
        data['fiscal_year'] = company.account_accountant_setup_financial_year_data_marked_done
        data['chart_of_accounts'] = company.account_accountant_setup_chart_of_accounts_marked_done
        data['initial_balance'] = company.opening_move_posted()

        return data

    def mark_bank_setup_as_done_action(self):
        """ Forces the 'bank setup' step of setup to mark it as done. It will hence
        be marked as such in the setup bar.
        """
        self.company_id.account_accountant_setup_bank_data_marked_done = True
        return self.env.ref('account_accountant.init_wizard_refresh_view').read([])[0]

    def unmark_bank_setup_as_done_action(self):
        """ Forces the 'bank setup' step of setup to mark it as undone. It will hence
        be marked as such in the setup bar.
        """
        self.company_id.account_accountant_setup_bank_data_marked_done = False
        return self.env.ref('account_accountant.init_wizard_refresh_view').read([])[0]
