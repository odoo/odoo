# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields


class HrContract(models.Model):
    _inherit = "hr.contract"

    l10n_us_pre_retirement_amount = fields.Float(
        string="Retirement Plans: 401(k)",
        help="Pre-tax contributions to Retirement Plans: 401(k), could be either a percentage or a fixed amount per payslip.")
    l10n_us_pre_retirement_type = fields.Selection(
        selection=[
            ('percent', '%'),
            ('fixed', '$ / slip')],
        string="Retirement Plans: 401(k) Type",
        default='percent')
    l10n_us_pre_retirement_matching_amount = fields.Float(
        string="Retirement Plans: Matching Amount",
        help="Benefit Matching to Retirement Plans: Employer's 401(k) benefit matching, could be either a percentage or a fixed amount per payslip.")
    l10n_us_pre_retirement_matching_type = fields.Selection(
        selection=[
            ('percent', '%'),
            ('fixed', '$ / slip')],
        string="Retirement Plans: Matching Type",
        default='percent')
    l10n_us_pre_retirement_matching_yearly_cap = fields.Float(
        string='Retirement Plans: Matching Yearly Cap',
        default=100,
        help="Maximum amount, as percentage (%), of the employee's salary that will be matched by the Employer as benefit.")
    l10n_us_health_benefits_medical = fields.Monetary(
        string="Health Benefits: Medical",
        help="Pre-tax amount (USD) deducted for Medical health benefits.")
    l10n_us_health_benefits_dental = fields.Monetary(
        string="Health Benefits: Dental",
        help="Pre-tax amount (USD) deducted for Dental health benefits.")
    l10n_us_health_benefits_vision = fields.Monetary(
        string="Health Benefits: Vision",
        help="Pre-tax amount (USD) deducted for  Vision health benefits.")
    l10n_us_health_benefits_fsa = fields.Monetary(
        string="Health Benefits: FSA",
        help="Pre-tax amount (USD) deducted for Flexible Spending Accounts (FSA).")
    l10n_us_health_benefits_fsadc = fields.Monetary(
        string="Health Benefits: FSA Dependent Care",
        help="Pre-tax amount (USD) deducted for Flexible Spending Accounts (FSA) for Dependent Care.")
    l10n_us_health_benefits_hsa = fields.Monetary(
        string="Health Benefits: HSA",
        help="Pre-tax amount (USD) deducted for pre-tax Health Savings Account (HSA).")
    l10n_us_commuter_benefits = fields.Monetary(
        string="Commuter Benefits",
        help="Pre-tax amount (USD) deducted for Commuter benefits.")
    l10n_us_post_roth_401k_amount = fields.Float(
        string="ROTH 401(k)",
        help="Post-tax contributions to Retirement plan: Roth 401(K), could be either a percentage or a fixed amount per payslip.")
    l10n_us_post_roth_401k_type = fields.Selection(
        selection=[
            ('percent', '%'),
            ('fixed', '$ / slip')],
        string="ROTH 401(k) Type",
        default='percent')
    l10n_us_employee_state_code = fields.Char(
        related='employee_id.address_id.state_id.code',
        readonly=True)
    l10n_us_worker_compensation_id = fields.Many2one(
        'l10n.us.worker.compensation',
        string="Worker Compensation")

    _sql_constraints = [
        (
            'l10n_us_pre_retirement_amount_is_percentage',
            "CHECK(l10n_us_pre_retirement_type IS NULL OR l10n_us_pre_retirement_type='fixed' OR (l10n_us_pre_retirement_type='percent' AND l10n_us_pre_retirement_amount >= 0 AND l10n_us_pre_retirement_amount <= 100))",
            'The contribution rate must be a percentage between 0 and 100.'
        ),
        (
            'l10n_us_post_roth_401k_amount_is_percentage',
            "CHECK(l10n_us_post_roth_401k_type IS NULL OR l10n_us_post_roth_401k_type='fixed' OR (l10n_us_post_roth_401k_type='percent' AND l10n_us_post_roth_401k_amount >= 0 AND l10n_us_post_roth_401k_amount <= 100))",
            'The contribution rate must be a percentage between 0 and 100.'
        ),
    ]
