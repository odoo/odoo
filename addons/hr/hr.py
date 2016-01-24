# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging

import openerp
from openerp import api
from openerp import SUPERUSER_ID
from openerp import tools
from openerp.modules.module import get_module_resource
from openerp.osv import fields, osv
from openerp.tools.translate import _

_logger = logging.getLogger(__name__)


class hr_employee_category(osv.Model):

    _name = "hr.employee.category"
    _description = "Employee Category"
    _columns = {
        'name': fields.char("Employee Tag", required=True),
        'color': fields.integer('Color Index'),
        'employee_ids': fields.many2many('hr.employee', 'employee_category_rel', 'category_id', 'emp_id', 'Employees'),
    }
    _sql_constraints = [
            ('name_uniq', 'unique (name)', "Tag name already exists !"),
    ]


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

    # TDE note: done in new api, because called with new api -> context is a
    # frozendict -> error when tryign to manipulate it
    @api.model
    def create(self, values):
        return super(hr_job, self.with_context(mail_create_nosubscribe=True)).create(values)

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


class hr_employee(osv.osv):
    _name = "hr.employee"
    _description = "Employee"
    _order = 'name_related'
    _inherits = {'resource.resource': "resource_id"}
    _inherit = ['mail.thread']

    _mail_post_access = 'read'

    _columns = {
        #we need a related field in order to be able to sort the employee by name
        'name_related': fields.related('resource_id', 'name', type='char', string='Name', readonly=True, store=True),
        'country_id': fields.many2one('res.country', 'Nationality (Country)'),
        'birthday': fields.date("Date of Birth"),
        'ssnid': fields.char('SSN No', help='Social Security Number'),
        'sinid': fields.char('SIN No', help="Social Insurance Number"),
        'identification_id': fields.char('Identification No'),
        'gender': fields.selection([('male', 'Male'), ('female', 'Female'), ('other', 'Other')], 'Gender'),
        'marital': fields.selection([('single', 'Single'), ('married', 'Married'), ('widower', 'Widower'), ('divorced', 'Divorced')], 'Marital Status'),
        'department_id': fields.many2one('hr.department', 'Department'),
        'address_id': fields.many2one('res.partner', 'Working Address'),
        'address_home_id': fields.many2one('res.partner', 'Home Address'),
        'bank_account_id': fields.many2one('res.partner.bank', 'Bank Account Number', domain="[('partner_id','=',address_home_id)]", help="Employee bank salary account"),
        'work_phone': fields.char('Work Phone', readonly=False),
        'mobile_phone': fields.char('Work Mobile', readonly=False),
        'work_email': fields.char('Work Email', size=240),
        'work_location': fields.char('Work Location'),
        'notes': fields.text('Notes'),
        'parent_id': fields.many2one('hr.employee', 'Manager'),
        'category_ids': fields.many2many('hr.employee.category', 'employee_category_rel', 'emp_id', 'category_id', 'Tags'),
        'child_ids': fields.one2many('hr.employee', 'parent_id', 'Subordinates'),
        'resource_id': fields.many2one('resource.resource', 'Resource', ondelete='cascade', required=True, auto_join=True),
        'coach_id': fields.many2one('hr.employee', 'Coach'),
        'job_id': fields.many2one('hr.job', 'Job Title'),
        'passport_id': fields.char('Passport No'),
        'color': fields.integer('Color Index'),
        'city': fields.related('address_id', 'city', type='char', string='City'),
        'login': fields.related('user_id', 'login', type='char', string='Login', readonly=1),
        'last_login': fields.related('user_id', 'date', type='datetime', string='Latest Connection', readonly=1),
    }

    # image: all image fields are base64 encoded and PIL-supported
    image = openerp.fields.Binary("Photo", attachment=True,
        help="This field holds the image used as photo for the employee, limited to 1024x1024px.")
    image_medium = openerp.fields.Binary("Medium-sized photo",
        compute='_compute_images', inverse='_inverse_image_medium', store=True, attachment=True,
        help="Medium-sized photo of the employee. It is automatically "\
             "resized as a 128x128px image, with aspect ratio preserved. "\
             "Use this field in form views or some kanban views.")
    image_small = openerp.fields.Binary("Small-sized photo",
        compute='_compute_images', inverse='_inverse_image_small', store=True, attachment=True,
        help="Small-sized photo of the employee. It is automatically "\
             "resized as a 64x64px image, with aspect ratio preserved. "\
             "Use this field anywhere a small image is required.")

    @api.depends('image')
    def _compute_images(self):
        for rec in self:
            rec.image_medium = tools.image_resize_image_medium(rec.image)
            rec.image_small = tools.image_resize_image_small(rec.image)

    def _inverse_image_medium(self):
        for rec in self:
            rec.image = tools.image_resize_image_big(rec.image_medium)

    def _inverse_image_small(self):
        for rec in self:
            rec.image = tools.image_resize_image_big(rec.image_small)

    def _get_default_image(self, cr, uid, context=None):
        image_path = get_module_resource('hr', 'static/src/img', 'default_image.png')
        return tools.image_resize_image_big(open(image_path, 'rb').read().encode('base64'))

    defaults = {
        'active': 1,
        'image': _get_default_image,
        'color': 0,
    }

    def unlink(self, cr, uid, ids, context=None):
        resource_ids = []
        for employee in self.browse(cr, uid, ids, context=context):
            resource_ids.append(employee.resource_id.id)
        super(hr_employee, self).unlink(cr, uid, ids, context=context)
        return self.pool.get('resource.resource').unlink(cr, uid, resource_ids, context=context)

    def onchange_address_id(self, cr, uid, ids, address, context=None):
        if address:
            address = self.pool.get('res.partner').browse(cr, uid, address, context=context)
            return {'value': {'work_phone': address.phone, 'mobile_phone': address.mobile}}
        return {'value': {}}

    def onchange_company(self, cr, uid, ids, company, context=None):
        address_id = False
        if company:
            company_id = self.pool.get('res.company').browse(cr, uid, company, context=context)
            address = self.pool.get('res.partner').address_get(cr, uid, [company_id.partner_id.id], ['contact'])
            address_id = address and address['contact'] or False
        return {'value': {'address_id': address_id}}

    def onchange_department_id(self, cr, uid, ids, department_id, context=None):
        value = {'parent_id': False}
        if department_id:
            department = self.pool.get('hr.department').browse(cr, uid, department_id)
            value['parent_id'] = department.manager_id.id
        return {'value': value}

    def onchange_user(self, cr, uid, ids, name, image, user_id, context=None):
        if user_id:
            user = self.pool['res.users'].browse(cr, uid, user_id, context=context)
            values = {
                'name': name or user.name,
                'work_email': user.email,
                'image': image or user.image,
            }
            return {'value': values}

    def action_follow(self, cr, uid, ids, context=None):
        """ Wrapper because message_subscribe_users take a user_ids=None
            that receive the context without the wrapper. """
        return self.message_subscribe_users(cr, uid, ids, context=context)

    def action_unfollow(self, cr, uid, ids, context=None):
        """ Wrapper because message_unsubscribe_users take a user_ids=None
            that receive the context without the wrapper. """
        return self.message_unsubscribe_users(cr, uid, ids, context=context)

    def _message_get_auto_subscribe_fields(self, cr, uid, updated_fields, auto_follow_fields=None, context=None):
        """ Overwrite of the original method to always follow user_id field,
        even when not track_visibility so that a user will follow it's employee
        """
        if auto_follow_fields is None:
            auto_follow_fields = ['user_id']
        user_field_lst = []
        for name, field in self._fields.items():
            if name in auto_follow_fields and name in updated_fields and field.comodel_name == 'res.users':
                user_field_lst.append(name)
        return user_field_lst

    _constraints = [(osv.osv._check_recursion, _('Error! You cannot create recursive hierarchy of Employee(s).'), ['parent_id']),]


class hr_department(osv.osv):
    _name = "hr.department"
    _description = "HR Department"
    _inherit = ['mail.thread', 'ir.needaction_mixin']

    def _dept_name_get_fnc(self, cr, uid, ids, prop, unknow_none, context=None):
        res = self.name_get(cr, uid, ids, context=context)
        return dict(res)

    _columns = {
        'name': fields.char('Department Name', required=True),
        'complete_name': fields.function(_dept_name_get_fnc, type="char", string='Name'),
        'company_id': fields.many2one('res.company', 'Company', select=True, required=False),
        'parent_id': fields.many2one('hr.department', 'Parent Department', select=True),
        'child_ids': fields.one2many('hr.department', 'parent_id', 'Child Departments'),
        'manager_id': fields.many2one('hr.employee', 'Manager', track_visibility='onchange'),
        'member_ids': fields.one2many('hr.employee', 'department_id', 'Members', readonly=True),
        'jobs_ids': fields.one2many('hr.job', 'department_id', 'Jobs'),
        'note': fields.text('Note'),
        'color': fields.integer('Color Index'),
    }

    _defaults = {
        'company_id': lambda self, cr, uid, c: self.pool.get('res.company')._company_default_get(cr, uid, 'hr.department', context=c),
    }

    _constraints = [
        (osv.osv._check_recursion, _('Error! You cannot create recursive departments.'), ['parent_id'])
    ]

    def name_get(self, cr, uid, ids, context=None):
        if not ids:
            return []
        if isinstance(ids, (int, long)):
            ids = [ids]
        if context is None:
            context = {}
        reads = self.read(cr, uid, ids, ['name','parent_id'], context=context)
        res = []
        for record in reads:
            name = record['name']
            if record['parent_id']:
                name = record['parent_id'][1]+' / '+name
            res.append((record['id'], name))
        return res

    def create(self, cr, uid, vals, context=None):
        if context is None:
            context = {}
        context = dict(context, mail_create_nosubscribe=True)
        # TDE note: auto-subscription of manager done by hand, because currently
        # the tracking allows to track+subscribe fields linked to a res.user record
        # An update of the limited behavior should come, but not currently done.
        manager_id = vals.get("manager_id")
        new_id = super(hr_department, self).create(cr, uid, vals, context=context)
        if manager_id:
            employee = self.pool.get('hr.employee').browse(cr, uid, manager_id, context=context)
            if employee.user_id:
                self.message_subscribe_users(cr, uid, [new_id], user_ids=[employee.user_id.id], context=context)
        return new_id

    def write(self, cr, uid, ids, vals, context=None):
        # TDE note: auto-subscription of manager done by hand, because currently
        # the tracking allows to track+subscribe fields linked to a res.user record
        # An update of the limited behavior should come, but not currently done.
        if isinstance(ids, (int, long)):
            ids = [ids]
        employee_ids = []
        if 'manager_id' in vals:
            manager_id = vals.get("manager_id")
            if manager_id:
                employee = self.pool['hr.employee'].browse(cr, uid, manager_id, context=context)
                if employee.user_id:
                    self.message_subscribe_users(cr, uid, ids, user_ids=[employee.user_id.id], context=context)
            for department in self.browse(cr, uid, ids, context=context):
                employee_ids += self.pool['hr.employee'].search(
                    cr, uid, [
                        ('id', '!=', manager_id),
                        ('department_id', '=', department.id),
                        ('parent_id', '=', department.manager_id.id)
                    ], context=context)
            self.pool['hr.employee'].write(cr, uid, employee_ids, {'parent_id': manager_id}, context=context)
        return super(hr_department, self).write(cr, uid, ids, vals, context=context)


class res_users(osv.osv):
    _name = 'res.users'
    _inherit = 'res.users'

    def write(self, cr, uid, ids, vals, context=None):
        if isinstance(ids, (int, long)):
            ids = [ids]
        result = super(res_users, self).write(cr, uid, ids, vals, context=context)
        employee_obj = self.pool.get('hr.employee')
        if vals.get('name'):
            for user_id in ids:
                if user_id == SUPERUSER_ID:
                    employee_ids = employee_obj.search(cr, uid, [('user_id', '=', user_id)])
                    employee_obj.write(cr, uid, employee_ids, {'name': vals['name']}, context=context)
        return result
