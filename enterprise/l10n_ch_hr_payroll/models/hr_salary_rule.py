# -*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class HrSalaryRule(models.Model):
    _inherit = 'hr.salary.rule'

    l10n_ch_code = fields.Char(string="External Code")

    l10n_ch_ac_included = fields.Boolean(
        string="AVS/AC Included", help="Whether the amount is included in the basis to compute the retirement/unemployement deduction")
    # YTI TODO MASTER RENAME INTO l10n_ch_laa_included
    l10n_ch_aanp_included = fields.Boolean(
        string="AANP Included", help="Whether the amount is included in the basis to compute the accident insurance deduction")
    l10n_ch_ijm_included = fields.Boolean(
        string="IJM Included", help="Whether the amount is included in the basis to compute the daily sick pay deduction")
    l10n_ch_source_tax_included = fields.Boolean(
        string="Source Tax Included", help="Whether the amount is included in the basis to compute the daily sick pay deduction")
    l10n_ch_13th_month_included = fields.Boolean(string="13th Month Included")
    l10n_ch_5_cents_rounding = fields.Boolean(string="5 cents rounding", default=True)
    l10n_ch_gross_included = fields.Boolean(string="Gross Included")
    l10n_ch_laac_included = fields.Boolean(
        string="LAAC Included", help="Whether the amount is included in the basis to compute the additional accident insurance deduction")
    # YTI TODO : add help
    l10n_ch_lpp_forecast = fields.Boolean(
        string="LPP Forecast", default=False)
    l10n_ch_lpp_factor = fields.Integer(
        string="LPP Factor", default=0)
    l10n_ch_lpp_retroactive = fields.Boolean(
        string="LPP Retroactive", default=False)
    l10n_ch_salary_certificate = fields.Char(string="Salary certificate")
    l10n_ch_caf_statement = fields.Char(string="CAF Statement")
    l10n_ch_wage_statement = fields.Char(string="Monthly Statistics", help="""Code meaning:
- I: Gross base salary and regular allowances
    - Ordinary salary paid, such as monthly, hourly, piece rate, working from home, etc.
    - Regular allowances paid, such as allowances for position or for length of service,
      residence, housing, travel or cost of living allowances.
    - Tips paid subject to AVS contributions.
    - Regular payments (at each pay) of a commission, turnover contribution or other bonus
      paid regularly.
- J: Gross amount of compensation for shift work, Sunday or night work and other arduousness
     bonuses (compensation for on-call duty, dirty work, etc.).
- K: Total amount of family allowances paid by the employer in the form of child allowances,
     vocational training allowances, household allowances or care allowances.
- Y: Benefits provided by insurance or similar institutions and which have an impact on
     employee contributions
- L: Amount of AVS/AI/APG/AC/ (1st pillar) and AANP (employee’s share) contributions.
     Not included:
        - the employer’s share,
        - the Parifonds,
        - daily allowance insurance in the event of IJM illness,
        - LAAC supplementary accident insurance
        - Social contributions must in principle be transmitted in the form of negative values.
- M: Amount of ordinary contributions (employee's share) to LPP professional pension provision or
     the 2nd pillar, in accordance with legal, statutory or regulatory provisions.
     The amount indicated should not include redemption contributions.
     Regular BVG-LPP contributions must in principle be transmitted as negative values.""")
    l10n_ch_yearly_statement = fields.Char(string="Yearly Statistics", help="""Code meaning:
- O: 13th salary paid (with the 14th and following) provided that it is not in the form of a bonus
- P: Overtime pay
- Q: Sporadic Benefits, e.g.
        - bonuses,
        - merit-based rewards,
        - participation in profit or turnover,
        - engagement bonuses and severance pay,
        - loyalty bonuses, bonuses and gifts for length of service,
        - fixed moving compensation,
        - Christmas bonuses,
        - compensation for members of the board of directors (attendance fees, fees, etc.).
- R: Fringe Benefits
        - board and lodging (section 2.1 of the salary certificate);
      - the private share of the company car (section 2.2 of the salary certificate);
      - other ancillary salary benefits (section 2.3 of the salary certificate);
      - participation rights (section 5 of the salary certificate).
- S: Capital Payment: Capital benefits of a pension nature paid by the employer directly to the
     employee and likely to be taxed at a reduced rate.
      - severance pay of a provident nature;
      - capital benefits of a pension nature;
      - salary payments after death.
- T: Other Benefits: All other services covered on an optional basis by the employer, although
     they are generally due by the employee.
        - partial or total coverage of contributions owed by the employee to LPP professional
          insurance, including executive insurance;
        - payments to occupational pension institutions (2nd pillar) made by the employer in
          favor of the employee (purchase contributions);
        - payment of insurance contributions in favor of the employee and members of his family
          (health insurance, optional 3rd pillar b insurance, life insurance, etc.);
        - payment of contributions to recognized forms of linked individual pension provision (3rd pillar a).""")
