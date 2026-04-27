from dateutil.relativedelta import relativedelta
from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class L10nChHrEmployeeChildren(models.Model):
    _inherit = 'l10n.ch.hr.employee.children'

    l10n_ch_child_status = fields.Selection([
        ('responsible', 'Responsible Child'),
        ('dependent', 'Dependent / Incapable of Work'),
        ('non_responsible', 'Non-responsible Child')
    ], string="Child Status", default='responsible', required=True,
        help="Determines the automatic calculation of allowance end dates.")

    allowance_eligible = fields.Boolean(
        string="Child Receives Allowance",
        default=True
    )
    allowance_supplementary_eligible = fields.Boolean(
        string="Child Receives Supplementary Allowance",
        default=False
    )

    allowance_start_date = fields.Date(
        string="Allowance Start Date",
        compute='_compute_allowance_dates', store=True, readonly=False
    )

    child_allowance_end_date = fields.Date(
        string="Child Allowance Until",
        compute='_compute_allowance_dates', store=True, readonly=False,
        help="Date until the basic child allowance is paid (usually 16 or 20)."
    )

    education_allowance_end_date = fields.Date(
        string="Education Allowance Until",
        compute='_compute_allowance_dates', store=True, readonly=False,
        help="Date until the education allowance is paid (usually 25)."
    )

    @api.depends('birthdate', 'l10n_ch_child_status')
    def _compute_allowance_dates(self):
        """
        automates dates based on FCF Rules:
        1. Responsible: Child until 16, Edu until 25.
        2. Dependent (Incapable): Child until 20, Edu until 25.
        3. Non-Responsible: Child until 16, No Edu.
        dates are set to the end of the month of the birthday.
        source :
        https://www.bsv.admin.ch/bsv/fr/home/assurances-sociales/famz/grundlagen-und-gesetze/leistungen/arten.html
        """
        for child in self:
            if not child.birthdate:
                child.allowance_start_date = False
                child.child_allowance_end_date = False
                child.education_allowance_end_date = False
                continue

            if not child.allowance_start_date:
                child.allowance_start_date = child.birthdate

            def get_end_of_month_limit(years):
                date_limit = child.birthdate + relativedelta(years=years)
                return date_limit + relativedelta(day=31)

            if child.l10n_ch_child_status == 'responsible':
                child.child_allowance_end_date = get_end_of_month_limit(16)
                child.education_allowance_end_date = get_end_of_month_limit(25)

            elif child.l10n_ch_child_status == 'dependent':
                child.child_allowance_end_date = get_end_of_month_limit(20)
                child.education_allowance_end_date = get_end_of_month_limit(25)

            elif child.l10n_ch_child_status == 'non_responsible':
                child.child_allowance_end_date = get_end_of_month_limit(16)
                child.education_allowance_end_date = False
