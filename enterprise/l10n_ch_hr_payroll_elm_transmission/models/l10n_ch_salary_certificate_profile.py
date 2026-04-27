# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from .hr_employee import CANTONS


class L10nChsalaryCertificateProfile(models.Model):
    _name = 'l10n.ch.salary.certificate.profile'
    _description = 'Salary Certificate Profile'

    employee_id = fields.Many2one("hr.employee")
    name = fields.Char(string="Name")
    certificate_template_id = fields.Many2one("l10n.ch.salary.certificate.profile", domain=[('employee_id', '=', False)])
    company_id = fields.Many2one("res.company", default=lambda self: self.env.company)

    valid_from = fields.Date(default=lambda self: fields.Date.context_today(self).replace(month=1, day=1))

    l10n_ch_certificate_type = fields.Selection(string="Certificate Type",
                                                selection=[('TaxSalary', "Salary Certificate"),
                                                           ('TaxAnnuity', "Pension Statement")], default="TaxSalary")
    l10n_ch_source_tax_settlement_letter = fields.Boolean(string="Source-Tax Settlement Letter")
    l10n_ch_child_allowance_indirect = fields.Boolean(string="Child Allowances paid by FCF")
    l10n_ch_relocation_costs = fields.Float(string="Relocation Costs Paid by the Company")
    l10n_ch_provision_salary = fields.Boolean(string="Provision of Salary")
    l10n_ch_provision_salary_first_name = fields.Char()
    l10n_ch_provision_salary_last_name = fields.Char()
    l10n_ch_provision_salary_street = fields.Char()
    l10n_ch_provision_salary_street2 = fields.Char()
    l10n_ch_provision_salary_zip = fields.Char()
    l10n_ch_provision_salary_city = fields.Char()
    l10n_ch_provision_salary_country = fields.Many2one('res.country', default=lambda self: self.env.ref('base.ch').id)

    l10n_ch_cs_free_transport = fields.Boolean(string="F. Free Transportion", help="""
    Free transportation between home and workplace, this setting should be checked only:
    - If the worker should not incur any costs for commuting this setting should be checked
    -The commuting expenses are not reimbursed to the worker in section 2.3""", compute="_compute_certificate_values", store=True, readonly=False)
    l10n_ch_cs_free_meals = fields.Boolean(string="G. Free meals or Lunch Vouchers", help="""
    Cafeteria Meals / Lunch Vouchers:
    - Option to have lower-cost meals at lunchtime or in the evening
    - Expense allowance for the main meal eaten outside on more than half of the working days
    """, compute="_compute_certificate_values", store=True, readonly=False)

    l10n_ch_cs_car_policy = fields.Selection(selection=[("none", "No Company Car"),
                                              ("empPart", "Employee Pays at least 0.9% per month"),
                                              ("toClarify", "To be clarified")], string="Car Policy", compute="_compute_certificate_values", store=True, readonly=False)
    l10n_ch_cs_expense_policy = fields.Selection(selection=[("approved", "Approved"),
                                                  ("rz52", "Effective Expenses according to Rz 52"),
                                                  ("receipts", "Based on Receipts")], string="Expense Policy", compute="_compute_certificate_values", store=True, readonly=False)
    l10n_ch_cs_expense_policy_approved_canton = fields.Selection(selection=CANTONS, string="Approval Canton", compute="_compute_certificate_values", store=True, readonly=False)
    l10n_ch_cs_expense_policy_approved_date = fields.Date(string="Approval Date", compute="_compute_certificate_values", store=True, readonly=False)

    l10n_ch_cs_expense_expatriate_ruling_approved = fields.Boolean(string="Expatriate Ruling Approved", compute="_compute_certificate_values", store=True, readonly=False)
    l10n_ch_cs_expense_expatriate_ruling_approved_canton = fields.Selection(selection=CANTONS, compute="_compute_certificate_values", store=True, readonly=False)
    l10n_ch_cs_expense_expatriate_ruling_approved_date = fields.Date(compute="_compute_certificate_values", store=True, readonly=False)

    l10n_ch_cs_employee_parti_fair_market_value = fields.Boolean(string="Fair Market Value", compute="_compute_certificate_values", store=True, readonly=False)
    l10n_ch_cs_employee_parti_fair_market_value_canton = fields.Selection(selection=CANTONS, compute="_compute_certificate_values", store=True, readonly=False)
    l10n_ch_cs_employee_parti_fair_market_value_date = fields.Date(compute="_compute_certificate_values", store=True, readonly=False)

    l10n_ch_cs_employee_participation_taxable_income = fields.Boolean(string="Without Taxable Income", compute="_compute_certificate_values", store=True, readonly=False)
    l10n_ch_cs_employee_participation_taxable_income_locked = fields.Boolean(string="Locked Options", compute="_compute_certificate_values", store=True, readonly=False)
    l10n_ch_cs_employee_participation_taxable_income_unlisted = fields.Boolean(string="Unlisted Stock Options", compute="_compute_certificate_values", store=True, readonly=False)
    l10n_ch_cs_employee_participation_taxable_income_reversional = fields.Boolean(string="Reversional to Shares", compute="_compute_certificate_values", store=True, readonly=False)
    l10n_ch_cs_employee_participation_taxable_income_virtual = fields.Boolean(string="Virtual Participation", compute="_compute_certificate_values", store=True, readonly=False)


    l10n_ch_cs_other_fringe_benefits = fields.Char(string="Other Fringe Benefits", compute="_compute_certificate_values", store=True, readonly=False)
    l10n_ch_cs_additional_text = fields.Char(string="Additional Text", compute="_compute_certificate_values", store=True, readonly=False)

    _sql_constraints = [
        ('ch_certificate_unique', 'unique(employee_id, valid_from)', 'Employee can only have one wage statement running at the same time.')
    ]

    @api.constrains('valid_from')
    def _check_valid_from(self):
        for profile in self:
            if profile.valid_from and profile.valid_from.day != 1:
                raise ValidationError(_("Validity date must start on the first of the month"))

    @api.depends("certificate_template_id")
    def _compute_certificate_values(self):
        for certificate in self:
            if certificate.certificate_template_id:
                certificate_fields = certificate.certificate_template_id._fields
                for field in certificate_fields:
                    if field.startswith("l10n_ch_cs_"):
                        certificate[field] = certificate.certificate_template_id[field]

    def action_update_all_certificates(self):
        self.ensure_one()
        if self.employee_id:
            raise ValidationError(_("This action can only be performed on templates"))

        certificates_using_template = self.env['l10n.ch.salary.certificate.profile'].search([('certificate_template_id', '=', self.id)])
        certificates_using_template._compute_certificate_values()
