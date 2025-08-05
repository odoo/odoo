# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from markupsafe import Markup

from odoo import api, models, fields, _, SUPERUSER_ID
from odoo.exceptions import AccessError
from odoo.tools.misc import clean_context
from odoo.addons.mail.tools.discuss import Store


HR_READABLE_FIELDS = [
    'active',
    'child_ids',
    'employee_id',
    'employee_ids',
    'employee_parent_id',
    'hr_presence_state',
    'last_activity',
    'last_activity_time',
    'can_edit',
    'is_hr_user',
    'is_system',
    'employee_resource_calendar_id',
    'work_contact_id',
    'bank_account_id',
]

HR_WRITABLE_FIELDS = [
    'additional_note',
    'private_street',
    'private_street2',
    'private_city',
    'private_state_id',
    'private_zip',
    'private_country_id',
    'private_phone',
    'private_email',
    'address_id',
    'barcode',
    'birthday',
    'birthday_public_display',
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
    'sex',
    'identification_id',
    'ssnid',
    'job_title',
    'km_home_work',
    'distance_home_work',
    'distance_home_work_unit',
    'marital',
    'mobile_phone',
    'employee_parent_id',
    'passport_id',
    'permit_no',
    'pin',
    'place_of_birth',
    'spouse_birthdate',
    'spouse_complete_name',
    'visa_expire',
    'visa_no',
    'work_email',
    'work_location_id',
    'work_phone',
    'certificate',
    'study_field',
    'study_school',
    'private_lang',
    'employee_type',
]


class ResUsers(models.Model):
    _inherit = 'res.users'

    def _employee_ids_domain(self):
        # employee_ids is considered a safe field and as such will be fetched as sudo.
        # So try to enforce the security rules on the field to make sure we do not load employees outside of active companies
        return [('company_id', 'in', self.env.company.ids + self.env.context.get('allowed_company_ids', []))]

    # note: a user can only be linked to one employee per company (see sql constraint in ´hr.employee´)
    employee_ids = fields.One2many('hr.employee', 'user_id', string='Related employee', domain=_employee_ids_domain)
    employee_id = fields.Many2one('hr.employee', string="Company employee",
        compute='_compute_company_employee', search='_search_company_employee', store=False)

    job_title = fields.Char(related='employee_id.job_title')
    work_phone = fields.Char(related='employee_id.work_phone', readonly=False, related_sudo=False)
    mobile_phone = fields.Char(related='employee_id.mobile_phone', readonly=False, related_sudo=False)
    work_email = fields.Char(related='employee_id.work_email', readonly=False, related_sudo=False)
    category_ids = fields.Many2many(related='employee_id.category_ids', string="Employee Tags", readonly=False, related_sudo=False)
    department_id = fields.Many2one(related='employee_id.department_id')
    address_id = fields.Many2one(related='employee_id.address_id', readonly=False, related_sudo=False)
    work_contact_id = fields.Many2one(related='employee_id.work_contact_id', readonly=False, related_sudo=False)
    work_location_id = fields.Many2one(related='employee_id.work_location_id')
    work_location_name = fields.Char(related="employee_id.work_location_name")
    work_location_type = fields.Selection(related="employee_id.work_location_type")
    employee_parent_id = fields.Many2one(related='employee_id.parent_id', readonly=False, related_sudo=False)
    coach_id = fields.Many2one(related='employee_id.coach_id', readonly=False, related_sudo=False)
    private_street = fields.Char(related='employee_id.private_street', string="Private Street", readonly=False, related_sudo=False)
    private_street2 = fields.Char(related='employee_id.private_street2', string="Private Street2", readonly=False, related_sudo=False)
    private_city = fields.Char(related='employee_id.private_city', string="Private City", readonly=False, related_sudo=False)
    private_state_id = fields.Many2one(
        related='employee_id.private_state_id', string="Private State", readonly=False, related_sudo=False,
        domain="[('country_id', '=?', private_country_id)]")
    private_zip = fields.Char(related='employee_id.private_zip', readonly=False, string="Private Zip", related_sudo=False)
    private_country_id = fields.Many2one(related='employee_id.private_country_id', string="Private Country", readonly=False, related_sudo=False)
    private_phone = fields.Char(related='employee_id.private_phone', readonly=False, related_sudo=False)
    private_email = fields.Char(related='employee_id.private_email', string="Private Email", readonly=False)
    private_lang = fields.Selection(related='employee_id.lang', string="Employee Lang", readonly=False)
    km_home_work = fields.Integer(related='employee_id.km_home_work', readonly=False, related_sudo=False)
    distance_home_work = fields.Integer(related='employee_id.distance_home_work', readonly=False, related_sudo=False)
    distance_home_work_unit = fields.Selection(related='employee_id.distance_home_work_unit', readonly=False, related_sudo=False)
    # res.users already have a field bank_account_id and country_id from the res.partner inheritance: don't redefine them
    employee_bank_account_id = fields.Many2one(related='employee_id.bank_account_id', string="Employee's Bank Account Number", related_sudo=False, readonly=False)
    employee_country_id = fields.Many2one(related='employee_id.country_id', string="Employee's Country", readonly=False, related_sudo=False)
    identification_id = fields.Char(related='employee_id.identification_id', readonly=False, related_sudo=False)
    ssnid = fields.Char(related='employee_id.ssnid', readonly=False, related_sudo=False)
    passport_id = fields.Char(related='employee_id.passport_id', readonly=False, related_sudo=False)
    sex = fields.Selection(related='employee_id.sex', readonly=False, related_sudo=False)
    birthday = fields.Date(related='employee_id.birthday', readonly=False, related_sudo=False)
    birthday_public_display = fields.Boolean(related='employee_id.birthday_public_display', readonly=False, related_sudo=False)
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
    employee_type = fields.Selection(related='employee_id.employee_type', readonly=False, related_sudo=False)
    employee_resource_calendar_id = fields.Many2one(related='employee_id.resource_calendar_id', string="Employee's Working Hours", readonly=True)
    bank_account_id = fields.Many2one(related="employee_id.bank_account_id")

    create_employee = fields.Boolean(store=False, default=False, copy=False, string="Technical field, whether to create an employee")
    create_employee_id = fields.Many2one('hr.employee', store=False, copy=False, string="Technical field, bind user to this employee on create")

    can_edit = fields.Boolean(compute='_compute_can_edit')
    is_system = fields.Boolean(compute="_compute_is_system")
    is_hr_user = fields.Boolean(compute='_compute_is_hr_user')

    # Skills
    resume_line_ids = fields.One2many(related='employee_id.resume_line_ids', readonly=False)
    employee_skill_ids = fields.One2many(related='employee_id.employee_skill_ids')
    current_employee_skill_ids = fields.One2many('hr.employee.skill', related="employee_id.current_employee_skill_ids", readonly=False)
    certification_ids = fields.One2many('hr.employee.skill', related="employee_id.certification_ids", readonly=False)

    @api.depends_context('uid')
    def _compute_is_system(self):
        self.is_system = self.env.user._is_system()

    def _compute_can_edit(self):
        can_edit = self.env['ir.config_parameter'].sudo().get_param('hr.hr_employee_self_edit') or self.env.user.has_group('hr.group_hr_user')
        for user in self:
            user.can_edit = can_edit

    def _compute_is_hr_user(self):
        is_hr_user = self.env.user.has_group('hr.group_hr_user')
        for user in self:
            user.is_hr_user = is_hr_user

    @api.depends('employee_ids')
    def _compute_employee_count(self):
        for user in self.with_context(active_test=False):
            user.employee_count = len(user.employee_ids)

    @property
    def SELF_READABLE_FIELDS(self):
        return super().SELF_READABLE_FIELDS + HR_READABLE_FIELDS + HR_WRITABLE_FIELDS

    @property
    def SELF_WRITEABLE_FIELDS(self):
        return super().SELF_WRITEABLE_FIELDS + HR_WRITABLE_FIELDS

    @api.model
    def get_views(self, views, options=None):
        # Requests the My Profile form view as last.
        # Otherwise the fields of the 'search' view will take precedence
        # and will omit the fields that are requested as SUPERUSER
        # in `get_view()`.
        profile_view = self.env.ref("hr.res_users_view_form_profile")
        profile_form = profile_view and [profile_view.id, 'form']
        if profile_form and profile_form in views:
            views.remove(profile_form)
            views.append(profile_form)
        result = super().get_views(views, options)
        return result

    @api.model
    def get_view(self, view_id=None, view_type='form', **options):
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
        result = super().get_view(view_id, view_type, **options)
        return result

    @api.model_create_multi
    def create(self, vals_list):
        res = super().create(vals_list)
        employee_create_vals = []
        for user, vals in zip(res, vals_list):
            if not vals.get('create_employee') and not vals.get('create_employee_id'):
                continue
            if vals.get('create_employee_id'):
                self.env['hr.employee'].browse(vals.get('create_employee_id')).user_id = user
            else:
                employee_create_vals.append(dict(
                    name=user.name,
                    company_id=user.env.company.id,
                    **self.env['hr.employee']._sync_user(user)
                ))
        if employee_create_vals:
            self.env['hr.employee'].with_context(clean_context(self.env.context)).create(employee_create_vals)
        return res

    def _get_employee_fields_to_sync(self):
        """Get values to sync to the related employee when the User is changed.
        """
        return ['name', 'email', 'image_1920', 'tz']

    def _get_personal_info_partner_ids_to_notify(self, employee):
        # To override in appropriate module
        return ('', [])

    def write(self, vals):
        """
        Synchronize user and its related employee
        and check access rights if employees are not allowed to update
        their own data (otherwise sudo is applied for self data).
        """
        hr_fields = {
            field_name: field
            for field_name, field in self._fields.items()
            if field.related_field and field.related_field.model_name == 'hr.employee' and field_name in vals
        }
        can_edit_self = self.env['ir.config_parameter'].sudo().get_param('hr.hr_employee_self_edit') or self.env.user.has_group('hr.group_hr_user')
        if hr_fields and not can_edit_self:
            # Raise meaningful error message
            raise AccessError(_("You are only allowed to update your preferences. Please contact a HR officer to update other information."))

        employee_domain = [
            *self.env['hr.employee']._check_company_domain(self.env.company),
            ('user_id', 'in', self.ids),
        ]
        if hr_fields:
            employees = self.env['hr.employee'].sudo().search(employee_domain)
            get_field = self.env['ir.model.fields']._get
            field_names = Markup().join([
                 Markup("<li>%s</li>") % get_field("res.users", fname).field_description for fname in hr_fields
            ])
            for employee in employees:
                reason_message, partner_ids = self._get_personal_info_partner_ids_to_notify(employee)
                if partner_ids:
                    employee.message_notify(
                        body=Markup("<p>%s</p><p>%s</p><ul>%s</ul><p><em>%s</em></p>") % (
                            _('Personal information update.'),
                            _("The following fields were modified by %s", employee.name),
                            field_names,
                            reason_message,
                        ),
                        partner_ids=partner_ids,
                    )
        result = super().write(vals)

        employee_values = {}
        for fname in [f for f in self._get_employee_fields_to_sync() if f in vals]:
            employee_values[fname] = vals[fname]

        if employee_values:
            if 'email' in employee_values:
                employee_values['work_email'] = employee_values.pop('email')
            if 'image_1920' in vals:
                without_image = self.env['hr.employee'].sudo().search(employee_domain + [('image_1920', '=', False)])
                with_image = self.env['hr.employee'].sudo().search(employee_domain + [('image_1920', '!=', False)])
                without_image.write(employee_values)
                if not can_edit_self:
                    employee_values.pop('image_1920')
                with_image.write(employee_values)
            else:
                employees = self.env['hr.employee'].sudo().search(employee_domain)
                if employees:
                    employees.write(employee_values)
        return result

    @api.model
    def action_get(self):
        if self.env.user.employee_id:
            return self.env['ir.actions.act_window']._for_xml_id('hr.res_users_action_my')
        return super().action_get()

    @api.depends('employee_ids')
    @api.depends_context('company')
    def _compute_company_employee(self):
        employee_per_user = {
            employee.user_id: employee
            for employee in self.env['hr.employee'].search([('user_id', 'in', self.ids), ('company_id', '=', self.env.company.id)])
        }
        for user in self:
            user.employee_id = employee_per_user.get(user)

    def _search_company_employee(self, operator, value):
        return [('employee_ids', operator, value)]

    def action_create_employee(self):
        self.ensure_one()
        if self.env.company not in self.company_ids:
            raise AccessError(_("You are not allowed to create an employee because the user does not have access rights for %s", self.env.company.name))
        self.env['hr.employee'].create(dict(
            name=self.name,
            company_id=self.env.company.id,
            **self.env['hr.employee']._sync_user(self)
        ))

    def action_open_employees(self):
        self.ensure_one()
        employees = self.employee_ids
        model = 'hr.employee' if self.env.user.has_group('hr.group_hr_user') else 'hr.employee.public'
        if len(employees) > 1:
            return {
                'name': _('Related Employees'),
                'type': 'ir.actions.act_window',
                'res_model': model,
                'view_mode': 'kanban,list,form',
                'domain': [('id', 'in', employees.ids)],
            }
        return {
            'name': _('Employee'),
            'type': 'ir.actions.act_window',
            'res_model': model,
            'res_id': employees.id,
            'view_mode': 'form',
        }

    def action_related_contact(self):
        return {
            'name': _("Related Contact"),
            'res_id': self.partner_id.id,
            'type': 'ir.actions.act_window',
            'res_model': 'res.partner',
            'view_mode': 'form',
        }

    def get_formview_action(self, access_uid=None):
        """ Override this method in order to redirect many2one towards the full user form view
        incase the user is ERP manager and the request coming from employee form."""

        res = super().get_formview_action(access_uid=access_uid)
        user = self.env.user
        if access_uid:
            user = self.env['res.users'].browse(access_uid).sudo()

        if self.env.context.get('default_create_employee_id') and user.has_group('base.group_erp_manager'):
            res['views'] = [(self.env.ref('base.view_users_form').id, 'form')]

        return res

    def _get_store_avatar_card_fields(self, target):
        avatar_card_fields = super()._get_store_avatar_card_fields(target)
        if target.is_internal(self.env):
            employee_fields = self.employee_ids._get_store_avatar_card_fields(target)
            avatar_card_fields.append(Store.Many("employee_ids", employee_fields, mode="ADD"))
        return avatar_card_fields

    # Skills
    @property
    def SELF_READABLE_FIELDS(self):
        return super().SELF_READABLE_FIELDS + [
            'resume_line_ids',
            'employee_skill_ids',
            'current_employee_skill_ids',
            'certification_ids',
        ]

    @property
    def SELF_WRITEABLE_FIELDS(self):
        return super().SELF_WRITEABLE_FIELDS + [
            'resume_line_ids',
        ]

    def write(self, vals):
        if 'current_employee_skill_ids' in vals or 'certification_ids' in vals or 'employee_skill_ids' in vals:
            vals['employee_skill_ids'] = vals.pop('current_employee_skill_ids', []) + vals.pop('certification_ids', []) + vals.get('employee_skill_ids', [])

        # Must be called directly on employee_id to prevent SET values in vals from causing unintended behavior
        if 'employee_skill_ids' in vals:
            self.employee_id.write({'employee_skill_ids': vals.pop("employee_skill_ids")})
        res = super().write(vals)
        return res
