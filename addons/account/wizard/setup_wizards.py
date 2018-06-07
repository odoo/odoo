# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class FinancialYearOpeningWizard(models.TransientModel):
    _name = 'account.financial.year.op'

    company_id = fields.Many2one(comodel_name='res.company', required=True)
    opening_move_posted = fields.Boolean(string='Opening Move Posted', compute='_compute_opening_move_posted')
    opening_date = fields.Date(string='Opening Date', required=True, related='company_id.account_opening_date', help="Date from which the accounting is managed in Odoo. It is the date of the opening entry.")
    fiscalyear_last_day = fields.Integer(related="company_id.fiscalyear_last_day", required=True,
                                         help="The last day of the month will be taken if the chosen day doesn't exist.")
    fiscalyear_last_month = fields.Selection(selection=[(1, 'January'), (2, 'February'), (3, 'March'), (4, 'April'), (5, 'May'), (6, 'June'), (7, 'July'), (8, 'August'), (9, 'September'), (10, 'October'), (11, 'November'), (12, 'December')],
                                             related="company_id.fiscalyear_last_month",
                                             required=True,
                                             help="The last day of the month will be taken if the chosen day doesn't exist.")
    account_setup_fy_data_done = fields.Boolean(string='Financial year setup marked as done', compute="_compute_setup_marked_done")

    @api.depends('company_id.account_setup_fy_data_done')
    def _compute_setup_marked_done(self):
        for record in self:
            record.account_setup_fy_data_done = record.company_id.account_setup_fy_data_done

    @api.depends('company_id.account_opening_move_id')
    def _compute_opening_move_posted(self):
        for record in self:
            record.opening_move_posted = record.company_id.opening_move_posted()

    def mark_as_done(self):
        """ Forces fiscal year setup state to 'done'."""
        self.company_id.account_setup_fy_data_done = True

    def unmark_as_done(self):
        """ Forces fiscal year setup state to 'undone'."""
        self.company_id.account_setup_fy_data_done = False

    @api.multi
    def write(self, vals):
        if 'fiscalyear_last_day' in vals or 'fiscalyear_last_month' in vals:
            for wizard in self:
                company = wizard.company_id
                vals['fiscalyear_last_day'] = company._verify_fiscalyear_last_day(
                    company.id,
                    vals.get('fiscalyear_last_day'),
                    vals.get('fiscalyear_last_month'))
        return super(FinancialYearOpeningWizard, self).write(vals)


class SetupBarBankConfigWizard(models.TransientModel):
    _inherits = {'res.partner.bank': 'res_partner_bank_id'}
    _name = 'account.setup.bank.manual.config'

    setup_journal_link_creation = fields.Selection(selection=[('new', 'Create new journal'), ('link', 'Link to an existing journal')], default='new')
    single_journal_id = fields.Many2one(string="Journal", comodel_name='account.journal', compute='compute_single_journal_id', inverse='set_single_journal_id')
    single_journal_name = fields.Char(compute='compute_single_journal_related_data', inverse='set_single_journal_id', required=True)

    wizard_acc_type = fields.Selection(string="Account Type", selection=lambda x: x.env['res.partner.bank'].get_supported_account_types(), compute='_compute_wizard_acc_type')

    @api.depends('acc_number')
    def _compute_wizard_acc_type(self):
        for record in self:
            record.wizard_acc_type = self.env['res.partner.bank'].retrieve_acc_type(record.acc_number)

    @api.model
    def create(self, vals):
        """ This wizard is only used to setup an account for the current active
        company, so we always inject the corresponding partner when creating
        the model.
        """
        vals['partner_id'] = self.env['res.company']._company_default_get().partner_id.id
        return super(SetupBarBankConfigWizard, self).create(vals)

    @api.depends('single_journal_id')
    def compute_single_journal_related_data(self):
        for record in self:
            if record.single_journal_id:
                record.single_journal_name = record.single_journal_id.name

    @api.depends('journal_id') # Despite its name, journal_id is actually a One2many field
    def compute_single_journal_id(self):
        for record in self:
            record.single_journal_id = record.journal_id and record.journal_id[0] or None

    def set_single_journal_id(self):
        """ Called when saving the wizard.
        """
        for record in self:
            selected_journal = record.single_journal_id
            if record.setup_journal_link_creation == 'new':
                company = self.env['res.company']._company_default_get('account.journal')
                bank_journal_count = self.env['account.journal'].search_count([('company_id','=',company.id), ('type','=','bank')])
                selected_journal = self.env['account.journal'].create({
                    'name': record.single_journal_name,
                    'code': 'BNK' + str(bank_journal_count + 1),
                    'type': 'bank',
                    'company_id': company.id,
                })

            record.journal_id = [(6, False, selected_journal.ids)]

    def validate(self):
        """ Called by the validation button of this wizard. Serves as an
        extension hook.
        """
        pass
