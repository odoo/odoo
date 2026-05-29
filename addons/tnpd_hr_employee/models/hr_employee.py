# Part of TNPD Prison HR Employee Extension.
# License: LGPL-3

from odoo import api, fields, models
from odoo.exceptions import ValidationError


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

    x_initial = fields.Char(
        string='Initial',
        help='Name initial(s) of the employee (e.g. "R.", "A.K.").',
        groups='hr.group_hr_user',
    )

    x_mobile_no = fields.Char(
        string='Mobile No',
        help='Personal mobile number of the employee.',
        groups='hr.group_hr_user',
    )

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

   # In hr_employee.py find and update
    x_religion = fields.Selection(
        selection=[
            ('hinduism', 'Hindu'),
            ('islam', 'Muslim'),
            ('christianity', 'Christian'),
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

    # Legacy Char fields — kept for backward compatibility with existing data
    # and the prison-master lookup helpers. New code should use the *_jail_id
    # Many2one fields below which enforce the prison.jail hierarchy.
    x_central_prison = fields.Char(
        string='Controlling Central Prison (Present Station)',
        help='Name of the Central Prison that exercises administrative control '
             'over the employee\'s current posting.',
        index=True,
        groups='hr.group_hr_user',
    )
    x_district_jail = fields.Char(
        string='District Jail (Legacy)',
        help='Legacy text field. Use x_district_jail_id for new records.',
        groups='hr.group_hr_user',
    )
    x_sub_jail = fields.Char(
        string='Sub Jail (Legacy)',
        help='Legacy text field. Use x_sub_jail_id for new records.',
        groups='hr.group_hr_user',
    )

    # ── Hierarchy-aware jail assignment (uses prison.jail master) ─────────
    # Architecture: three separate Many2one fields (Option A) chosen over a
    # single jail_id because:
    #   • Direct ORM filtering on any tier: domain=[('x_central_jail_id','=',id)]
    #   • No traversal overhead in reporting queries
    #   • Explicit cascade validation at write time
    #   • Transfer approval can update each tier independently

    x_central_jail_id = fields.Many2one(
        comodel_name='prison.jail',
        string='Central Jail (Present Station)',
        domain=[('jail_type', '=', 'central_jail'), ('active', '=', True)],
        ondelete='restrict',
        index=True,
        tracking=True,
        groups='hr.group_hr_user',
        help='Central Jail that exercises administrative control over this employee.',
    )
    x_district_jail_id = fields.Many2one(
        comodel_name='prison.jail',
        string='District Jail (Present Station)',
        domain="[('jail_type', '=', 'district_jail'), ('active', '=', True), ('parent_id', '=', x_central_jail_id)]",
        ondelete='restrict',
        index=True,
        tracking=True,
        groups='hr.group_hr_user',
        help='District Jail under which the employee is currently posted.',
    )
    x_sub_jail_id = fields.Many2one(
        comodel_name='prison.jail',
        string='Sub Jail (Present Station)',
        domain="[('jail_type', '=', 'sub_jail'), ('active', '=', True), ('parent_id', '=', x_district_jail_id)]",
        ondelete='restrict',
        index=True,
        tracking=True,
        groups='hr.group_hr_user',
        help='Sub Jail at the employee\'s current posting, if applicable.',
    )

    # ── Onchange: reset dependents when parent changes ────────────────────

    @api.onchange('x_central_jail_id')
    def _onchange_x_central_jail_id(self):
        self.x_district_jail_id = False
        self.x_sub_jail_id = False

    @api.onchange('x_district_jail_id')
    def _onchange_x_district_jail_id(self):
        self.x_sub_jail_id = False

    # ── Hierarchy integrity constraint ────────────────────────────────────

    @api.constrains('x_central_jail_id', 'x_district_jail_id', 'x_sub_jail_id')
    def _check_employee_jail_hierarchy(self):
        for emp in self:
            if emp.x_district_jail_id and emp.x_central_jail_id:
                if emp.x_district_jail_id.parent_id != emp.x_central_jail_id:
                    raise ValidationError(
                        f'District Jail "{emp.x_district_jail_id.name}" does not belong '
                        f'to Central Jail "{emp.x_central_jail_id.name}". '
                        'Select a District Jail that is under the chosen Central Jail.'
                    )
            if emp.x_sub_jail_id and emp.x_district_jail_id:
                if emp.x_sub_jail_id.parent_id != emp.x_district_jail_id:
                    raise ValidationError(
                        f'Sub Jail "{emp.x_sub_jail_id.name}" does not belong '
                        f'to District Jail "{emp.x_district_jail_id.name}". '
                        'Select a Sub Jail that is under the chosen District Jail.'
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

    x_major_punishment_details = fields.Text(
        string='Details of Major Punishment Awarded',
        help='Chronological record of major punishments awarded, including '
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

    x_training_undergone = fields.Text(
        string='Training Undergone',
        help='Details of training programmes attended, including course name, '
             'institution, duration, and year.',
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

    # ── Section 10: Service Status ────────────────────────────────────────

    x_status = fields.Selection(
        selection=[
            ('active',   'Active'),
            ('pending',  'Pending'),
            ('transfer', 'Transfer'),
            ('inactive', 'Inactive'),
        ],
        string='Status',
        default='active',
        index=True,
        tracking=True,
        groups='hr.group_hr_user',
        help='Current service status of the employee within the department.',
    )
