# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, fields, _, SUPERUSER_ID
from odoo.exceptions import AccessError


class User(models.Model):
    _inherit = ['res.users']

    # note: a user can only be linked to one employee per company (see sql constraint in ´hr.employee´)
    employee_ids = fields.One2many('hr.employee', 'user_id', string='Related employee')
    employee_id = fields.Many2one('hr.employee', string="Company employee",
        compute='_compute_company_employee', search='_search_company_employee', store=False)

    job_title = fields.Char(related='employee_id.job_title', readonly=False, related_sudo=False)
    work_phone = fields.Char(related='employee_id.work_phone', readonly=False, related_sudo=False)
    mobile_phone = fields.Char(related='employee_id.mobile_phone', readonly=False, related_sudo=False)
    employee_phone = fields.Char(related='employee_id.phone', readonly=False, related_sudo=False)
    work_email = fields.Char(related='employee_id.work_email', readonly=False, related_sudo=False)
    category_ids = fields.Many2many(related='employee_id.category_ids', string="Employee Tags", readonly=False, related_sudo=False)
    department_id = fields.Many2one(related='employee_id.department_id', readonly=False, related_sudo=False)
    address_id = fields.Many2one(related='employee_id.address_id', readonly=False, related_sudo=False)
    work_location = fields.Char(related='employee_id.work_location', readonly=False, related_sudo=False)
    employee_parent_id = fields.Many2one(related='employee_id.parent_id', readonly=False, related_sudo=False)
    coach_id = fields.Many2one(related='employee_id.coach_id', readonly=False, related_sudo=False)
    address_home_id = fields.Many2one(related='employee_id.address_home_id', readonly=False, related_sudo=False)
    is_address_home_a_company = fields.Boolean(related='employee_id.is_address_home_a_company', readonly=False, related_sudo=False)
    private_email = fields.Char(related='address_home_id.email', string="Private Email", readonly=False)
    km_home_work = fields.Integer(related='employee_id.km_home_work', readonly=False, related_sudo=False)
    # res.users already have a field bank_account_id and country_id from the res.partner inheritance: don't redefine them
    employee_bank_account_id = fields.Many2one(related='employee_id.bank_account_id', string="Employee's Bank Account Number", related_sudo=False, readonly=False)
    employee_country_id = fields.Many2one(related='employee_id.country_id', string="Employee's Country", readonly=False, related_sudo=False)
    identification_id = fields.Char(related='employee_id.identification_id', readonly=False, related_sudo=False)
    passport_id = fields.Char(related='employee_id.passport_id', readonly=False, related_sudo=False)
    gender = fields.Selection(related='employee_id.gender', readonly=False, related_sudo=False)
    birthday = fields.Date(related='employee_id.birthday', readonly=False, related_sudo=False)
    place_of_birth = fields.Char(related='employee_id.place_of_birth', readonly=False, related_sudo=False)
    country_of_birth = fields.Many2one(related='employee_id.country_of_birth', readonly=False, related_sudo=False)
    marital = fields.Selection(related='employee_id.marital', readonly=False, related_sudo=False)
    spouse_complete_name = fields.Char(related='employee_id.spouse_complete_name', readonly=False, related_sudo=False)
    spouse_birthdate = fields.Date(related='employee_id.spouse_birthdate', readonly=False, related_sudo=False)
    children = fields.Integer(related='employee_id.children', readonly=False, related_sudo=False)
    emergency_contact = fields.Char(related='employee_id.emergency_contact', readonly=False, related_sudo=False)
    emergency_phone = fields.Char(related='employee_id.emergency_phone', readonly=False, related_sudo=False)
    visa_no = fields.Char(related='employee_id.visa_no', readonly=False, related_sudo=False)
    permit_no = fields.Char(related='employee_id.permit_no', readonly=False, related_sudo=False)
    visa_expire = fields.Date(related='employee_id.visa_expire', readonly=False, related_sudo=False)
    additional_note = fields.Text(related='employee_id.additional_note', readonly=False, related_sudo=False)
    barcode = fields.Char(related='employee_id.barcode', readonly=False, related_sudo=False)
    pin = fields.Char(related='employee_id.pin', readonly=False, related_sudo=False)
    certificate = fields.Selection(related='employee_id.certificate', readonly=False, related_sudo=False)
    study_field = fields.Char(related='employee_id.study_field', readonly=False, related_sudo=False)
    study_school = fields.Char(related='employee_id.study_school', readonly=False, related_sudo=False)
    employee_count = fields.Integer(compute='_compute_employee_count')
    hr_presence_state = fields.Selection(related='employee_id.hr_presence_state')
    last_activity = fields.Date(related='employee_id.last_activity')
    last_activity_time = fields.Char(related='employee_id.last_activity_time')

    can_edit = fields.Boolean(compute='_compute_can_edit')

    def _compute_can_edit(self):
        can_edit = self.env['ir.config_parameter'].sudo().get_param('hr.hr_employee_self_edit') or self.env.user.has_group('hr.group_hr_user')
        for user in self:
            user.can_edit = can_edit

    @api.depends('employee_ids')
    def _compute_employee_count(self):
        for user in self.with_context(active_test=False):
            user.employee_count = len(user.employee_ids)

    def __init__(self, pool, cr):
        """ Override of __init__ to add access rights.
            Access rights are disabled by default, but allowed
            on some specific fields defined in self.SELF_{READ/WRITE}ABLE_FIELDS.
        """
        hr_readable_fields = [
            'active',
            'child_ids',
            'employee_id',
            'employee_ids',
            'employee_parent_id',
            'hr_presence_state',
            'last_activity',
            'last_activity_time',
            'can_edit',
        ]

        hr_writable_fields = [
            'additional_note',
            'address_home_id',
            'address_id',
            'barcode',
            'birthday',
            'category_ids',
            'children',
            'coach_id',
            'country_of_birth',
            'department_id',
            'display_name',
            'emergency_contact',
            'emergency_phone',
            'employee_bank_account_id',
            'employee_country_id',
            'gender',
            'identification_id',
            'is_address_home_a_company',
            'job_title',
            'private_email',
            'km_home_work',
            'marital',
            'mobile_phone',
            'notes',
            'employee_parent_id',
            'passport_id',
            'permit_no',
            'employee_phone',
            'pin',
            'place_of_birth',
            'spouse_birthdate',
            'spouse_complete_name',
            'visa_expire',
            'visa_no',
            'work_email',
            'work_location',
            'work_phone',
            'certificate',
            'study_field',
            'study_school',
        ]

        init_res = super(User, self).__init__(pool, cr)
        # duplicate list to avoid modifying the original reference
        type(self).SELF_READABLE_FIELDS = type(self).SELF_READABLE_FIELDS + hr_readable_fields + hr_writable_fields
        type(self).SELF_WRITEABLE_FIELDS = type(self).SELF_WRITEABLE_FIELDS + hr_writable_fields
        return init_res

    @api.model
    def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
        # When the front-end loads the views it gets the list of available fields
        # for the user (according to its access rights). Later, when the front-end wants to
        # populate the view with data, it only asks to read those available fields.
        # However, in this case, we want the user to be able to read/write its own data,
        # even if they are protected by groups.
        # We make the front-end aware of those fields by sending all field definitions.
        # Note: limit the `sudo` to the only action of "editing own profile" action in order to
        # avoid breaking `groups` mecanism on res.users form view.
        profile_view = self.env.ref("hr.res_users_view_form_profile")
        if profile_view and view_id == profile_view.id:
            self = self.with_user(SUPERUSER_ID)
        return super(User, self).fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar, submenu=submenu)

    def write(self, vals):
        """
        Synchronize user and its related employee
        and check access rights if employees are not allowed to update
        their own data (otherwise sudo is applied for self data).
        """
        hr_fields = {
            field
            for field_name, field in self._fields.items()
            if field.related_field and field.related_field.model_name == 'hr.employee' and field_name in vals
        }
        can_edit_self = self.env['ir.config_parameter'].sudo().get_param('hr.hr_employee_self_edit') or self.env.user.has_group('hr.group_hr_user')
        if hr_fields and not can_edit_self:
            # Raise meaningful error message
            raise AccessError(_("You are only allowed to update your preferences. Please contact a HR officer to update other informations."))

        result = super(User, self).write(vals)

        employee_values = {}
        for fname in [f for f in ['name', 'email', 'image_1920', 'tz'] if f in vals]:
            employee_values[fname] = vals[fname]
        if employee_values:
            if 'email' in employee_values:
                employee_values['work_email'] = employee_values.pop('email')
            if 'image_1920' in vals:
                without_image = self.env['hr.employee'].sudo().search([('user_id', 'in', self.ids), ('image_1920', '=', False)])
                with_image = self.env['hr.employee'].sudo().search([('user_id', 'in', self.ids), ('image_1920', '!=', False)])
                without_image.write(employee_values)
                if not can_edit_self:
                    employee_values.pop('image_1920')
                with_image.write(employee_values)
            else:
                self.env['hr.employee'].sudo().search([('user_id', 'in', self.ids)]).write(employee_values)
        return result

    @api.model
    def action_get(self):
        if self.env.user.employee_id:
            return self.sudo().env.ref('hr.res_users_action_my').read()[0]
        return super(User, self).action_get()

    @api.depends('employee_ids')
    @api.depends_context('force_company')
    def _compute_company_employee(self):
        for user in self:
            user.employee_id = self.env['hr.employee'].search([('id', 'in', user.employee_ids.ids), ('company_id', '=', self.env.company.id)], limit=1)

    def _search_company_employee(self, operator, value):
        employees = self.env['hr.employee'].search([
            ('name', operator, value),
            '|',
            ('company_id', '=', self.env.company.id),
            ('company_id', '=', False)
        ], order='company_id ASC')
        return [('id', 'in', employees.mapped('user_id').ids)]

    def action_create_employee(self):
        self.ensure_one()
        self.env['hr.employee'].create(dict(
            name=self.name,
            company_id=self.env.company.id,
            **self.env['hr.employee']._sync_user(self)
        ))
