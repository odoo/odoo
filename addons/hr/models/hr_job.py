# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging

from openerp.osv import fields, osv
from openerp.tools.translate import _


class hr_job(osv.Model):

    def _get_nbr_employees(self, cr, uid, ids, name, args, context=None):
        res = {}
        for job in self.browse(cr, uid, ids, context=context):
            nb_employees = len(job.employee_ids or [])
            res[job.id] = {
                'no_of_employee': nb_employees,
                'expected_employees': nb_employees + job.no_of_recruitment,
            }
        return res

    def _get_job_position(self, cr, uid, ids, context=None):
        res = []
        for employee in self.pool.get('hr.employee').browse(cr, uid, ids, context=context):
            if employee.job_id:
                res.append(employee.job_id.id)
        return res

    _name = "hr.job"
    _description = "Job Position"
    _inherit = ['mail.thread']
    _columns = {
        'name': fields.char('Job Name', required=True, select=True, translate=True),
        'expected_employees': fields.function(_get_nbr_employees, string='Total Forecasted Employees',
            help='Expected number of employees for this job position after new recruitment.',
            store = {
                'hr.job': (lambda self,cr,uid,ids,c=None: ids, ['no_of_recruitment'], 10),
                'hr.employee': (_get_job_position, ['job_id'], 10),
            }, type='integer',
            multi='_get_nbr_employees'),
        'no_of_employee': fields.function(_get_nbr_employees, string="Current Number of Employees",
            help='Number of employees currently occupying this job position.',
            store = {
                'hr.employee': (_get_job_position, ['job_id'], 10),
            }, type='integer',
            multi='_get_nbr_employees'),
        'no_of_recruitment': fields.integer('Expected New Employees', copy=False,
                                            help='Number of new employees you expect to recruit.'),
        'no_of_hired_employee': fields.integer('Hired Employees', copy=False,
                                               help='Number of hired employees for this job position during recruitment phase.'),
        'employee_ids': fields.one2many('hr.employee', 'job_id', 'Employees', groups='base.group_user'),
        'description': fields.text('Job Description'),
        'requirements': fields.text('Requirements'),
        'department_id': fields.many2one('hr.department', 'Department'),
        'company_id': fields.many2one('res.company', 'Company'),
        'state': fields.selection([('recruit', 'Recruitment in Progress'), ('open', 'Recruitment Closed')],
                                  string='Status', readonly=True, required=True,
                                  track_visibility='always', copy=False,
                                  help="Set whether the recruitment process is open or closed for this job position."),
        'write_date': fields.datetime('Update Date', readonly=True),
    }

    _defaults = {
        'company_id': lambda self, cr, uid, ctx=None: self.pool.get('res.company')._company_default_get(cr, uid, 'hr.job', context=ctx),
        'state': 'recruit',
        'no_of_recruitment' : 1,
    }

    _sql_constraints = [
        ('name_company_uniq', 'unique(name, company_id, department_id)', 'The name of the job position must be unique per department in company!'),

    ]

    def set_recruit(self, cr, uid, ids, context=None):
        for job in self.browse(cr, uid, ids, context=context):
            no_of_recruitment = job.no_of_recruitment == 0 and 1 or job.no_of_recruitment
            self.write(cr, uid, [job.id], {'state': 'recruit', 'no_of_recruitment': no_of_recruitment}, context=context)
        return True

    def set_open(self, cr, uid, ids, context=None):
        self.write(cr, uid, ids, {
            'state': 'open',
            'no_of_recruitment': 0,
            'no_of_hired_employee': 0
        }, context=context)
        return True

    def copy(self, cr, uid, id, default=None, context=None):
        if default is None:
            default = {}
        if 'name' not in default:
            job = self.browse(cr, uid, id, context=context)
            default['name'] = _("%s (copy)") % (job.name)
        return super(hr_job, self).copy(cr, uid, id, default=default, context=context)

    # ----------------------------------------
    # Compatibility methods
    # ----------------------------------------
    _no_of_employee = _get_nbr_employees  # v7 compatibility
    job_open = set_open  # v7 compatibility
    job_recruitment = set_recruit  # v7 compatibility
