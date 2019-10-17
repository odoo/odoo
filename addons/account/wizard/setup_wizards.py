# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class FinancialYearOpeningWizard(models.TransientModel):
    _name = 'account.financial.year.op'
    _description = 'Opening Balance of Financial Year'

    company_id = fields.Many2one(comodel_name='res.company', required=True)
    opening_move_posted = fields.Boolean(string='Opening Move Posted', compute='_compute_opening_move_posted')
    opening_date = fields.Date(string='Opening Date', required=True, related='company_id.account_opening_date', help="Date from which the accounting is managed in Odoo. It is the date of the opening entry.", readonly=False)
    fiscalyear_last_day = fields.Integer(related="company_id.fiscalyear_last_day", required=True, readonly=False,
                                         help="Fiscal year last day.")
    fiscalyear_last_month = fields.Selection(selection=[(1, 'January'), (2, 'February'), (3, 'March'), (4, 'April'), (5, 'May'), (6, 'June'), (7, 'July'), (8, 'August'), (9, 'September'), (10, 'October'), (11, 'November'), (12, 'December')],
                                             related="company_id.fiscalyear_last_month", readonly=False,
                                             required=True,
                                             help="Fiscal year last month.")

    @api.depends('company_id.account_opening_move_id')
    def _compute_opening_move_posted(self):
        for record in self:
            record.opening_move_posted = record.company_id.opening_move_posted()

    @api.multi
    def write(self, vals):
        # Amazing workaround: non-stored related fields on company are a BAD idea since the 3 fields
        # must follow the constraint '_check_fiscalyear_last_day'. The thing is, in case of related
        # fields, the inverse write is done one value at a time, and thus the constraint is verified
        # one value at a time... so it is likely to fail.
        for wiz in self:
            wiz.company_id.write({
                'account_opening_date': vals.get('opening_date') or wiz.company_id.account_opening_date,
                'fiscalyear_last_day': vals.get('fiscalyear_last_day') or wiz.company_id.fiscalyear_last_day,
                'fiscalyear_last_month': vals.get('fiscalyear_last_month') or wiz.company_id.fiscalyear_last_month,
            })
        vals.pop('opening_date', None)
        vals.pop('fiscalyear_last_day', None)
        vals.pop('fiscalyear_last_month', None)
        return super().write(vals)

    @api.multi
    def action_save_onboarding_fiscal_year(self):
        self.env.user.company_id.set_onboarding_step_done('account_setup_fy_data_state')


class SetupBarBankConfigWizard(models.TransientModel):
    _inherits = {'res.partner.bank': 'res_partner_bank_id'}
    _name = 'account.setup.bank.manual.config'
    _description = 'Bank setup manual config'

    res_partner_bank_id = fields.Many2one(comodel_name='res.partner.bank', ondelete='cascade', required=True)
    create_or_link_option = fields.Selection(selection=[('new', 'Create new journal'), ('link', 'Link to an existing journal')], default='new')
    new_journal_name = fields.Char(compute='compute_new_journal_related_data', inverse='set_linked_journal_id', required=True, help='Will be used to name the Journal related to this bank account')
    linked_journal_id = fields.Many2one(string="Journal", comodel_name='account.journal', compute='compute_linked_journal_id', inverse='set_linked_journal_id')
    new_journal_code = fields.Char(string="Code", required=True, default=lambda self: self.env['account.journal'].get_next_bank_cash_default_code('bank', self.env['res.company']._company_default_get('account.journal').id))

    # field computing the type of the res.patrner.bank. It's behaves the same as a related res_part_bank_id.acc_type
    # except we want to display  this information while the record isn't yet saved.
    related_acc_type = fields.Selection(string="Account Type", selection=lambda x: x.env['res.partner.bank'].get_supported_account_types(), compute='_compute_related_acc_type')

    @api.depends('acc_number')
    def _compute_related_acc_type(self):
        for record in self:
            record.related_acc_type = self.env['res.partner.bank'].retrieve_acc_type(record.acc_number)

    @api.model
    def create(self, vals):
        """ This wizard is only used to setup an account for the current active
        company, so we always inject the corresponding partner when creating
        the model.
        """
        vals['partner_id'] = self.env.user.company_id.partner_id.id
        return super(SetupBarBankConfigWizard, self).create(vals)

    @api.depends('linked_journal_id')
    def compute_new_journal_related_data(self):
        for record in self:
            if record.linked_journal_id:
                record.new_journal_name = record.linked_journal_id.name

    @api.depends('journal_id')  # Despite its name, journal_id is actually a One2many field
    def compute_linked_journal_id(self):
        for record in self:
            record.linked_journal_id = record.journal_id and record.journal_id[0] or None

    def set_linked_journal_id(self):
        """ Called when saving the wizard.
        """
        for record in self:
            selected_journal = record.linked_journal_id
            if record.create_or_link_option == 'new':
                company = self.env['res.company']._company_default_get('account.journal')
                selected_journal = self.env['account.journal'].create({
                    'name': record.new_journal_name,
                    'code': record.new_journal_code,
                    'type': 'bank',
                    'company_id': company.id,
                    'bank_account_id': record.res_partner_bank_id.id,
                })
            else:
                selected_journal.bank_account_id = record.res_partner_bank_id.id

    def validate(self):
        """ Called by the validation button of this wizard. Serves as an
        extension hook in account_bank_statement_import.
        """
        self.env.user.company_id.set_onboarding_step_done('account_setup_bank_data_state')
