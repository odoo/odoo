from odoo import fields, models


class HrSalaryRule(models.Model):
    _name = 'hr.salary.rule'
    _inherit = ['hr.salary.rule', 'mail.thread']

    l10n_ch_code = fields.Char(tracking=True)
    l10n_ch_ac_included = fields.Boolean(tracking=True)
    l10n_ch_aanp_included = fields.Boolean(tracking=True)
    l10n_ch_ijm_included = fields.Boolean(tracking=True)
    l10n_ch_source_tax_included = fields.Boolean(tracking=True)
    l10n_ch_wage_statement = fields.Selection(string="Monthly Statistic", help="""Code meaning:
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
     Regular BVG-LPP contributions must in principle be transmitted as negative values.""",
        selection=[
            ('I', 'I'),
            ('J', 'J'),
            ('K', 'K'),
            ('Y', 'Y'),
            ('L', 'L'),
            ('M', 'M')], tracking=True)
    l10n_ch_yearly_statement = fields.Selection(
        string="Yearly Statistic", help="""Code meaning:
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
        - payment of contributions to recognized forms of linked individual pension provision (3rd pillar a).""",
        selection=[
            ('P', 'P'),
            ('O', 'O'),
            ('Q', 'Q'),
            ('R', 'R'),
            ('S', 'S'),
            ('T', 'T')], tracking=True)

    l10n_ch_13th_month_included = fields.Boolean(tracking=True)
    l10n_ch_13th_month_hourly_included = fields.Boolean(tracking=True)
    l10n_ch_vacation_pay_included = fields.Boolean(tracking=True)

    l10n_ch_5_cents_rounding = fields.Boolean(tracking=True)
    l10n_ch_gross_included = fields.Boolean(tracking=True)
    l10n_ch_laac_included = fields.Boolean(tracking=True)
    l10n_ch_lpp_forecast = fields.Boolean(tracking=True)
    l10n_ch_lpp_factor = fields.Integer(tracking=True)
    l10n_ch_lpp_retroactive = fields.Boolean(tracking=True)
    l10n_ch_salary_certificate = fields.Selection(selection=[
        ('1', '1. Salary'),
        ('2.1', '2.1 Room and board'),
        ('2.2', '2.2 Personal use of the company car'),
        ('2.3', '2.3 Additional salary benefits - Other'),
        ('3', '3. Irregular Benefits'),
        ('4', '4. Capital Benefits'),
        ('5', '5. Ownership right in accordance with supplement'),
        ('6', '6. Board of directors’ compensation'),
        ('7', '7. Other benefits'),
        ('8', '8. Gross Salary Total / Pension'),
        ('9', '9. Contributions OASI/DI/IC/UI/NBUV'),
        ('10.1', '10.1 Regular contributions'),
        ('10.2', '10.2 Purchasing contribution'),
        ('11', '11. Net salary / Pension'),
        ('12', '12. Withholding tax deduction'),
        ('13.1.1', '13.1.1. Actual expenses - Trip, room and board'),
        ('13.1.2', '13.1.2. Actual expenses - Others'),
        ('13.2.1', '13.2.1. Overall expenses - Representation'),
        ('13.2.2', '13.2.2. Overall expenses - Car'),
        ('13.2.3', '13.2.3. Overall expenses - Other'),
        ('13.3', '13.3. Contributions to further education'),
        ('14', '14. Further fringe benefits'),
    ], tracking=True)
    l10n_ch_caf_statement = fields.Char(tracking=True)
    l10n_ch_is_periodic = fields.Boolean(tracking=True)
