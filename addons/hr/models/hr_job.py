# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.addons.web_editor.controllers.main import handle_history_divergence


class Job(models.Model):

    _name = "hr.job"
    _description = "Job Position"
    _inherit = ['mail.thread']
    _order = 'sequence'

    name = fields.Char(string='Job Position', required=True, index=True, translate=True)
    sequence = fields.Integer(default=10)
    expected_employees = fields.Integer(compute='_compute_employees', string='Total Forecasted Employees', store=True,
        help='Expected number of employees for this job position after new recruitment.')
    no_of_employee = fields.Integer(compute='_compute_employees', string="Current Number of Employees", store=True,
        help='Number of employees currently occupying this job position.')
    no_of_recruitment = fields.Integer(string='Expected New Employees', copy=False,
        help='Number of new employees you expect to recruit.', default=1)
    no_of_hired_employee = fields.Integer(string='Hired Employees', copy=False,
        help='Number of hired employees for this job position during recruitment phase.')
    employee_ids = fields.One2many('hr.employee', 'job_id', string='Employees', groups='base.group_user')
    description = fields.Html(string='Job Description')
    requirements = fields.Text('Requirements')
    department_id = fields.Many2one('hr.department', string='Department', domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]")
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)
    state = fields.Selection([
        ('recruit', 'Recruitment in Progress'),
        ('open', 'Not Recruiting')
    ], string='Status', readonly=True, required=True, tracking=True, copy=False, default='recruit', help="Set whether the recruitment process is open or closed for this job position.")

    _sql_constraints = [
        ('name_company_uniq', 'unique(name, company_id, department_id)', 'The name of the job position must be unique per department in company!'),
        ('no_of_recruitment_positive', 'CHECK(no_of_recruitment >= 0)', 'The expected number of new employees must be positive.')
    ]

    @api.depends('no_of_recruitment', 'employee_ids.job_id', 'employee_ids.active')
    def _compute_employees(self):
        employee_data = self.env['hr.employee'].read_group([('job_id', 'in', self.ids)], ['job_id'], ['job_id'])
        result = dict((data['job_id'][0], data['job_id_count']) for data in employee_data)
        for job in self:
            job.no_of_employee = result.get(job.id, 0)
            job.expected_employees = result.get(job.id, 0) + job.no_of_recruitment

    @api.model
    def create(self, values):
        """ We don't want the current user to be follower of all created job """
        return super(Job, self.with_context(mail_create_nosubscribe=True)).create(values)

    @api.returns('self', lambda value: value.id)
    def copy(self, default=None):
        self.ensure_one()
        default = dict(default or {})
        if 'name' not in default:
            default['name'] = _("%s (copy)") % (self.name)
        return super(Job, self).copy(default=default)

    def set_recruit(self):
        for record in self:
            no_of_recruitment = 1 if record.no_of_recruitment == 0 else record.no_of_recruitment
            record.write({'state': 'recruit', 'no_of_recruitment': no_of_recruitment})
        return True

    def set_open(self):
        return self.write({
            'state': 'open',
            'no_of_recruitment': 0,
            'no_of_hired_employee': 0
        })

    def write(self, vals):
        if len(self) == 1:
            handle_history_divergence(self, 'description', vals)
        return super(Job, self).write(vals)
