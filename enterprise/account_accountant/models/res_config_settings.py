from datetime import date

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    fiscalyear_last_day = fields.Integer(related='company_id.fiscalyear_last_day', required=True, readonly=False)
    fiscalyear_last_month = fields.Selection(related='company_id.fiscalyear_last_month', required=True, readonly=False)
    use_anglo_saxon = fields.Boolean(string='Anglo-Saxon Accounting', related='company_id.anglo_saxon_accounting', readonly=False)
    invoicing_switch_threshold = fields.Date(string="Invoicing Switch Threshold", related='company_id.invoicing_switch_threshold', readonly=False)
    group_fiscal_year = fields.Boolean(string='Fiscal Years', implied_group='account_accountant.group_fiscal_year')
    predict_bill_product = fields.Boolean(string="Predict Bill Product", related='company_id.predict_bill_product', readonly=False)

    sign_invoice = fields.Boolean(string='Authorized Signatory on invoice', related='company_id.sign_invoice', readonly=False)
    signing_user = fields.Many2one(
        comodel_name='res.users',
        string="Signature used to sign all the invoice",
        readonly=False,
        related='company_id.signing_user',
        help="Select a user here to override every signature on invoice by this user's signature"
    )
    module_sign = fields.Boolean(string='Sign', compute='_compute_module_sign_status')

    # Deferred expense management
    deferred_expense_journal_id = fields.Many2one(
        comodel_name='account.journal',
        help='Journal used for deferred entries',
        readonly=False,
        related='company_id.deferred_expense_journal_id',
    )
    deferred_expense_account_id = fields.Many2one(
        comodel_name='account.account',
        help='Account used for deferred expenses',
        readonly=False,
        related='company_id.deferred_expense_account_id',
    )
    generate_deferred_expense_entries_method = fields.Selection(
        related='company_id.generate_deferred_expense_entries_method',
        readonly=False, required=True,
        help='Method used to generate deferred entries',
    )
    deferred_expense_amount_computation_method = fields.Selection(
        related='company_id.deferred_expense_amount_computation_method',
        readonly=False, required=True,
        help='Method used to compute the amount of deferred entries',
    )

    # Deferred revenue management
    deferred_revenue_journal_id = fields.Many2one(
        comodel_name='account.journal',
        help='Journal used for deferred entries',
        readonly=False,
        related='company_id.deferred_revenue_journal_id',
    )
    deferred_revenue_account_id = fields.Many2one(
        comodel_name='account.account',
        help='Account used for deferred revenues',
        readonly=False,
        related='company_id.deferred_revenue_account_id',
    )
    generate_deferred_revenue_entries_method = fields.Selection(
        related='company_id.generate_deferred_revenue_entries_method',
        readonly=False, required=True,
        help='Method used to generate deferred entries',
    )
    deferred_revenue_amount_computation_method = fields.Selection(
        related='company_id.deferred_revenue_amount_computation_method',
        readonly=False, required=True,
        help='Method used to compute the amount of deferred entries',
    )

    @api.depends('sign_invoice')
    def _compute_module_sign_status(self):
        sign_installed = 'sign' in self.env['ir.module.module']._installed()
        for settings in self:
            settings.module_sign = sign_installed or settings.company_id.sign_invoice

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
                    _('Incorrect fiscal year date: day is out of range for month. Month: %(month)s; Day: %(day)s',
                    month=wiz.fiscalyear_last_month, day=wiz.fiscalyear_last_day),
                )

    @api.model_create_multi
    def create(self, vals_list):
        # Amazing workaround: non-stored related fields on company are a BAD idea since the 2 fields
        # must follow the constraint '_check_fiscalyear_last_day'. The thing is, in case of related
        # fields, the inverse write is done one value at a time, and thus the constraint is verified
        # one value at a time... so it is likely to fail.
        for vals in vals_list:
            fiscalyear_last_day = vals.pop('fiscalyear_last_day', False) or self.env.company.fiscalyear_last_day
            fiscalyear_last_month = vals.pop('fiscalyear_last_month', False) or self.env.company.fiscalyear_last_month
            vals = {}
            if fiscalyear_last_day != self.env.company.fiscalyear_last_day:
                vals['fiscalyear_last_day'] = fiscalyear_last_day
            if fiscalyear_last_month != self.env.company.fiscalyear_last_month:
                vals['fiscalyear_last_month'] = fiscalyear_last_month
            if vals:
                self.env.company.write(vals)
        return super().create(vals_list)
