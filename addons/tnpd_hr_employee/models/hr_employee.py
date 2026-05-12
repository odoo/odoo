# Part of TNPD Prison HR Employee Extension.
# License: LGPL-3

from odoo import fields, models


class HrEmployee(models.Model):
    """
    Extends hr.employee with prison-department-specific fields.

    All fields use the 'x_' prefix as required by the department naming
    convention. Fields are restricted to hr.group_hr_user so sensitive
    service data is not visible to every user.

    NOTE: 'Gender' (sex) and 'Date of Birth' (birthday) already exist on
    the core hr.employee / hr.version model. They are surfaced in the TNPD
    view via XPath and do not need to be redeclared here.
    """

    _inherit = 'hr.employee'

    # ── Section 1: Service Identification ─────────────────────────────────

    x_designation = fields.Char(
        string='Designation',
        help='Official designation of the employee within the prison department '
             '(e.g. Jailor, Deputy Jailor, Warder).',
        index=True,
        tracking=True,
        groups='hr.group_hr_user',
    )

    x_employee_code = fields.Char(
        string='Employee ID',
        help='Unique service/payroll ID assigned by the department. '
             'Different from the Odoo internal ID.',
        index=True,
        copy=False,
        groups='hr.group_hr_user',
    )

    x_cps_no = fields.Char(
        string='CPS No',
        help='Contributory Pension Scheme (CPS / NPS) account number.',
        index=True,
        groups='hr.group_hr_user',
    )

    x_gpf_no = fields.Char(
        string='GPF No',
        help='General Provident Fund (GPF) account number. '
             'Applicable to employees who joined before NPS transition.',
        index=True,
        groups='hr.group_hr_user',
    )

    x_cug_mobile = fields.Char(
        string='Mobile (CUG) No',
        help='Closed User Group (CUG) mobile number issued by the department.',
        groups='hr.group_hr_user',
    )

    x_date_of_appointment = fields.Date(
        string='Date of Appointment',
        help='Date on which the employee was first appointed to government service.',
        tracking=True,
        groups='hr.group_hr_user',
    )

    x_date_of_retirement = fields.Date(
        string='Date of Retirement',
        help='Scheduled date of superannuation / retirement.',
        tracking=True,
        groups='hr.group_hr_user',
    )

    x_date_of_promotion = fields.Date(
        string='Date of Promotion',
        help='Date on which the employee was last promoted to the current designation.',
        tracking=True,
        groups='hr.group_hr_user',
    )

    # ── Section 2: Permanent Address ──────────────────────────────────────

    x_permanent_address = fields.Text(
        string='Permanent Address',
        help='Full permanent residential address of the employee.',
        groups='hr.group_hr_user',
    )

    x_taluk = fields.Char(
        string='Taluk',
        help='Taluk (sub-district / tehsil) of permanent residence.',
        groups='hr.group_hr_user',
    )

    x_town = fields.Char(
        string='Town',
        help='Town or village of permanent residence.',
        groups='hr.group_hr_user',
    )

    x_native_district = fields.Char(
        string='Native District',
        help='Native district of the employee.',
        index=True,
        groups='hr.group_hr_user',
    )

    # ── Section 3: Seniority & Panel ──────────────────────────────────────

    x_panel_year_sl_no = fields.Char(
        string='Panel Year and SL No',
        help='Seniority panel year and serial number used for promotions '
             'and posting orders (e.g. "2019 / 045").',
        index=True,
        groups='hr.group_hr_user',
    )

    # ── Section 4: Demographic Information ────────────────────────────────

    x_religion = fields.Selection(
        selection=[
            ('hinduism', 'Hinduism'),
            ('islam', 'Islam'),
            ('christianity', 'Christianity'),
            ('sikhism', 'Sikhism'),
            ('buddhism', 'Buddhism'),
            ('jainism', 'Jainism'),
            ('other', 'Other'),
        ],
        string='Religion',
        groups='hr.group_hr_user',
    )

    x_community = fields.Selection(
        selection=[
            ('oc', 'OC – Open / General'),
            ('bc', 'BC – Backward Class'),
            ('bcm', 'BCM – Backward Class (Muslim)'),
            ('mbc', 'MBC – Most Backward Class'),
            ('dnc', 'DNC – De-notified Community'),
            ('sc', 'SC – Scheduled Caste'),
            ('sca', 'SCA – Scheduled Caste (Arunthathiyar)'),
            ('st', 'ST – Scheduled Tribe'),
            ('other', 'Other'),
        ],
        string='Community',
        help='Social community classification as per Tamil Nadu government records.',
        index=True,
        groups='hr.group_hr_user',
    )

    x_caste = fields.Char(
        string='Caste',
        help='Caste of the employee (maintained for official statutory records).',
        groups='hr.group_hr_user',
    )

    x_mother_tongue = fields.Char(
        string='Mother Tongue',
        help='First / native language of the employee.',
        groups='hr.group_hr_user',
    )

    x_education_qualification = fields.Text(
        string='Education Qualification',
        help='Complete educational qualifications (degree, institution, year of passing).',
        groups='hr.group_hr_user',
    )

    # ── Section 5: Present Station ────────────────────────────────────────

    x_date_present_station = fields.Date(
        string='Date Since Working in Present Station',
        help='Date from which the employee has been posted at their current station.',
        tracking=True,
        groups='hr.group_hr_user',
    )

    x_central_prison = fields.Char(
        string='Controlling Central Prison (Present Station)',
        help='Name of the Central Prison that exercises administrative control '
             'over the employee\'s current posting.',
        index=True,
        groups='hr.group_hr_user',
    )

    x_sub_jail = fields.Char(
        string='Sub Jail (Present Station)',
        help='Name of the Sub Jail at the employee\'s current posting, if applicable.',
        groups='hr.group_hr_user',
    )

    x_district_jail = fields.Char(
        string='District Jail (Present Station)',
        help='Name of the District Jail at the employee\'s current posting, if applicable.',
        groups='hr.group_hr_user',
    )

    # ── Section 6: Disciplinary Record ───────────────────────────────────

    x_disciplinary_action_pending = fields.Boolean(
        string='Disciplinary Action Pending',
        default=False,
        help='Set to True if any departmental / court-directed disciplinary '
             'action is currently pending against this employee.',
        tracking=True,
        groups='hr.group_hr_user',
    )

    x_disciplinary_action_details = fields.Text(
        string='Disciplinary Action Details',
        help='Charge sheet particulars, case reference numbers, and current '
             'status of any pending disciplinary action.',
        groups='hr.group_hr_user',
    )

    x_minor_punishment_details = fields.Text(
        string='Details of Minor Punishment Awarded',
        help='Chronological record of minor punishments awarded, including '
             'charge particulars, date, and authority.',
        groups='hr.group_hr_user',
    )

    # ── Section 7: Service History ────────────────────────────────────────

    x_service_history = fields.Text(
        string='Places / Units / Seats Served Throughout Service',
        help='Complete posting history — list each station, unit, or seat '
             'with the dates of joining and relief.',
        groups='hr.group_hr_user',
    )

    # ── Section 8: Achievements & Recognition ────────────────────────────

    x_medals = fields.Text(
        string='Medals',
        help='Details of medals awarded (name of medal, date, and authority).',
        groups='hr.group_hr_user',
    )

    x_rewards = fields.Text(
        string='Rewards',
        help='Details of rewards and commendations received during service.',
        groups='hr.group_hr_user',
    )

    # ── Section 9: Family & Miscellaneous ─────────────────────────────────

    x_spouse_employment = fields.Text(
        string='Details of Spouse Employment',
        help='Name of employer, designation, and place of posting of the spouse, '
             'if employed in government service.',
        groups='hr.group_hr_user',
    )

    x_remarks = fields.Text(
        string='Remarks',
        help='Any additional remarks or administrative notes relevant to '
             'this employee\'s service record.',
        groups='hr.group_hr_user',
    )
