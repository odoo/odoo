# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import date, timedelta

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class FinancialYearOpeningWizard(models.TransientModel):
    _name = 'account.financial.year.op'
    _description = 'Opening Balance of Financial Year'

    company_id = fields.Many2one(comodel_name='res.company', required=True)
    opening_move_posted = fields.Boolean(string='Opening Move Posted', compute='_compute_opening_move_posted')
    opening_date = fields.Date(string='Opening Date', required=True, related='company_id.account_opening_date', help="Date from which the accounting is managed in Odoo. It is the date of the opening entry.", readonly=False)
    fiscalyear_last_day = fields.Integer(related="company_id.fiscalyear_last_day", required=True, readonly=False,
                                         help="The last day of the month will be used if the chosen day doesn't exist.")
    fiscalyear_last_month = fields.Selection(related="company_id.fiscalyear_last_month", readonly=False,
                                             required=True,
                                             help="The last day of the month will be used if the chosen day doesn't exist.")

    @api.depends('company_id.account_opening_move_id')
    def _compute_opening_move_posted(self):
        for record in self:
            record.opening_move_posted = record.company_id.opening_move_posted()

    @api.constrains('fiscalyear_last_day', 'fiscalyear_last_month')
    def _check_fiscalyear(self):
        # We try if the date exists in 2020, which is a leap year.
        # We do not define the constrain on res.company, since the recomputation of the related
        # fields is done one field at a time.
        for wiz in self:
            try:
                date(2020, int(wiz.fiscalyear_last_month), wiz.fiscalyear_last_day)
            except ValueError:
                raise ValidationError(
                    _('Incorrect fiscal year date: day is out of range for month. Month: %s; Day: %s',
                    wiz.fiscalyear_last_month, wiz.fiscalyear_last_day)
                )

    def write(self, vals):
        # Amazing workaround: non-stored related fields on company are a BAD idea since the 3 fields
        # must follow the constraint '_check_fiscalyear_last_day'. The thing is, in case of related
        # fields, the inverse write is done one value at a time, and thus the constraint is verified
        # one value at a time... so it is likely to fail.
        for wiz in self:
            wiz.company_id.write({
                'fiscalyear_last_day': vals.get('fiscalyear_last_day') or wiz.company_id.fiscalyear_last_day,
                'fiscalyear_last_month': vals.get('fiscalyear_last_month') or wiz.company_id.fiscalyear_last_month,
                'account_opening_date': vals.get('opening_date') or wiz.company_id.account_opening_date,
            })
            wiz.company_id.account_opening_move_id.write({
                'date': fields.Date.from_string(vals.get('opening_date') or wiz.company_id.account_opening_date) - timedelta(days=1),
            })

        vals.pop('opening_date', None)
        vals.pop('fiscalyear_last_day', None)
        vals.pop('fiscalyear_last_month', None)
        return super().write(vals)

    def action_save_onboarding_fiscal_year(self):
        return self.env['onboarding.onboarding.step'].action_validate_step('account.onboarding_onboarding_step_fiscal_year')


class SetupBarBankConfigWizard(models.TransientModel):
    _inherits = {'res.partner.bank': 'res_partner_bank_id'}
    _name = 'account.setup.bank.manual.config'
    _description = 'Bank setup manual config'
    _check_company_auto = True

    res_partner_bank_id = fields.Many2one(comodel_name='res.partner.bank', ondelete='cascade', required=True)
    new_journal_name = fields.Char(default=lambda self: self.linked_journal_id.name, inverse='set_linked_journal_id', required=True, help='Will be used to name the Journal related to this bank account')
    linked_journal_id = fields.Many2one(string="Journal",
        comodel_name='account.journal', inverse='set_linked_journal_id',
        compute="_compute_linked_journal_id",
        check_company=True,
        domain=[('type', '=', 'bank'), ('bank_account_id', '=', False)])
    bank_bic = fields.Char(related='bank_id.bic', readonly=False, string="Bic")
    num_journals_without_account = fields.Integer(default=lambda self: self._number_unlinked_journal())
    company_id = fields.Many2one('res.company', required=True, compute='_compute_company_id')

    def _number_unlinked_journal(self):
        return self.env['account.journal'].search_count([
            ('type', '=', 'bank'),
            ('bank_account_id', '=', False),
            ('id', '!=', self.default_linked_journal_id()),
        ])

    @api.onchange('acc_number')
    def _onchange_acc_number(self):
        for record in self:
            record.new_journal_name = record.acc_number

    @api.model_create_multi
    def create(self, vals_list):
        """ This wizard is only used to setup an account for the current active
        company, so we always inject the corresponding partner when creating
        the model.
        """
        for vals in vals_list:
            vals['partner_id'] = self.env.company.partner_id.id
            vals['new_journal_name'] = vals['acc_number']

            # If no bank has been selected, but we have a bic, we are using it to find or create the bank
            if not vals['bank_id'] and vals['bank_bic']:
                vals['bank_id'] = self.env['res.bank'].search([('bic', '=', vals['bank_bic'])], limit=1).id \
                                  or self.env['res.bank'].create({'name': vals['bank_bic'], 'bic': vals['bank_bic']}).id

        return super().create(vals_list)

    @api.onchange('linked_journal_id')
    def _onchange_new_journal_related_data(self):
        for record in self:
            if record.linked_journal_id:
                record.new_journal_name = record.linked_journal_id.name

    @api.depends('journal_id')  # Despite its name, journal_id is actually a One2many field
    def _compute_linked_journal_id(self):
        for record in self:
            record.linked_journal_id = record.journal_id and record.journal_id[0] or record.default_linked_journal_id()

    def default_linked_journal_id(self):
        for journal_id in self.env['account.journal'].search([('type', '=', 'bank'), ('bank_account_id', '=', False)]):
            empty_journal_count = self.env['account.move'].search_count([('journal_id', '=', journal_id.id)])
            if empty_journal_count == 0:
                return journal_id.id
        return False

    def set_linked_journal_id(self):
        """ Called when saving the wizard.
        """
        for record in self:
            selected_journal = record.linked_journal_id
            if not selected_journal:
                new_journal_code = self.env['account.journal'].get_next_bank_cash_default_code('bank', self.env.company)
                company = self.env.company
                record.linked_journal_id = self.env['account.journal'].create({
                    'name': record.new_journal_name,
                    'code': new_journal_code,
                    'type': 'bank',
                    'company_id': company.id,
                    'bank_account_id': record.res_partner_bank_id.id,
                    'bank_statements_source': 'undefined',
                })
            else:
                selected_journal.bank_account_id = record.res_partner_bank_id.id
                selected_journal.name = record.new_journal_name

    def validate(self):
        """Called by the validation button of this wizard. Serves as an
        extension hook in account_bank_statement_import.
        """
        self.env["onboarding.onboarding.step"].action_validate_step("account.onboarding_onboarding_step_bank_account")
        return {'type': 'ir.actions.client', 'tag': 'soft_reload'}

    def _compute_company_id(self):
        for wizard in self:
            if not wizard.company_id:
                wizard.company_id = self.env.company
