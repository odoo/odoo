# -*- coding: utf-8 -*-

from openerp import api, fields, models, _


class HrJob(models.Model):
    _name = "hr.job"
    _description = "Job Position"
    _inherit = 'mail.thread'

    name = fields.Char(string='Job Name', required=True, index=True, translate=True)
    expected_employees = fields.Integer(compute='_compute_employees',
         string='Total Forecasted Employees', store=True,
         help='Expected number of employees for this job position after new recruitment.')
    no_of_employee = fields.Integer(compute='_compute_employees',
         string='Current Number of Employees', store=True,
         help='Number of employees currently occupying this job position.')
    no_of_recruitment = fields.Integer(string='Expected New Employees', copy=False,
        help='Number of new employees you expect to recruit.', default=1)
    no_of_hired_employee = fields.Integer(string='Hired Employees', copy=False,
        help='Number of hired employees for this job position during recruitment phase.')
    employee_ids = fields.One2many('hr.employee', 'job_id', string='Employees',
        groups='base.group_user')
    description = fields.Text(string='Job Description')
    requirements = fields.Text()
    department_id = fields.Many2one('hr.department', string='Department')
    company_id = fields.Many2one('res.company', string='Company',
        default=lambda self: self.env['res.company']._company_default_get('hr.job'))
    state = fields.Selection([
            ('recruit', 'Recruitment in Progress'),
            ('open', 'Recruitment Closed')
        ], string='Status', readonly=True, required=True, track_visibility='always',
        copy=False, default='recruit',
        help='Set whether the recruitment process is open or closed for this job position.')
    write_date = fields.Datetime(string='Update Date', readonly=True)

    _sql_constraints = [
        ('name_company_uniq', 'unique(name, company_id, department_id)',
        'The name of the job position must be unique per department in company!'),
    ]

    @api.one
    @api.depends('no_of_recruitment', 'employee_ids')
    def _compute_employees(self):
        nb_employees = len(self.employee_ids)
        self.no_of_employee = nb_employees
        self.expected_employees = nb_employees + self.no_of_recruitment

    @api.one
    def copy(self, default=None):
        if default is None:
            default = {}
        if 'name' not in default:
            default['name'] = _("%s (copy)") % (self.name)
        return super(HrJob, self).copy(default=default)

    @api.multi
    def set_recruit(self):
        for job in self:
            no_of_recruitment = job.no_of_recruitment == 0 and 1 or job.no_of_recruitment
            job.write({'state': 'recruit', 'no_of_recruitment': no_of_recruitment})
        return True

    @api.multi
    def set_open(self):
        return self.write({
            'state': 'open',
            'no_of_recruitment': 0,
            'no_of_hired_employee': 0
        })

    # ----------------------------------------
    # Compatibility methods
    # ----------------------------------------
    job_open = set_open  # v7 compatibility
    job_recruitment = set_recruit  # v7 compatibility
