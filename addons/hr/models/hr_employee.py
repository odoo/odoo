# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
from pytz import timezone, UTC
from datetime import datetime, time
from random import choice
from string import digits
from dateutil.relativedelta import relativedelta
from markupsafe import Markup

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, AccessError
from odoo.osv import expression
from odoo.tools import convert, format_date


class HrEmployeePrivate(models.Model):
    """
    NB: Any field only available on the model hr.employee (i.e. not on the
    hr.employee.public model) should have `groups="hr.group_hr_user"` on its
    definition to avoid being prefetched when the user hasn't access to the
    hr.employee model. Indeed, the prefetch loads the data for all the fields
    that are available according to the group defined on them.
    """
    _name = "hr.employee"
    _description = "Employee"
    _order = 'name'
    _inherit = ['hr.employee.base', 'mail.thread.main.attachment', 'mail.activity.mixin', 'resource.mixin', 'avatar.mixin']
    _mail_post_access = 'read'

    @api.model
    def _lang_get(self):
        return self.env['res.lang'].get_installed()

    # resource and user
    # required on the resource, make sure required="True" set in the view
    name = fields.Char(string="Employee Name", related='resource_id.name', store=True, readonly=False, tracking=True)
    user_id = fields.Many2one(
        'res.users', 'User',
        related='resource_id.user_id',
        store=True,
        readonly=False,
        check_company=True,
        precompute=True,
        ondelete='restrict')
    user_partner_id = fields.Many2one(related='user_id.partner_id', related_sudo=False, string="User's partner")
    active = fields.Boolean('Active', related='resource_id.active', default=True, store=True, readonly=False)
    resource_calendar_id = fields.Many2one(tracking=True)
    department_id = fields.Many2one(tracking=True)
    company_id = fields.Many2one('res.company', required=True)
    company_country_id = fields.Many2one('res.country', 'Company Country', related='company_id.country_id', readonly=True, groups="base.group_system,hr.group_hr_user")
    company_country_code = fields.Char(related='company_country_id.code', depends=['company_country_id'], readonly=True, groups="base.group_system,hr.group_hr_user")
    # private info
    private_street = fields.Char(string="Private Street", groups="hr.group_hr_user")
    private_street2 = fields.Char(string="Private Street2", groups="hr.group_hr_user")
    private_city = fields.Char(string="Private City", groups="hr.group_hr_user")
    private_state_id = fields.Many2one(
        "res.country.state", string="Private State",
        domain="[('country_id', '=?', private_country_id)]",
        groups="hr.group_hr_user")
    private_zip = fields.Char(string="Private Zip", groups="hr.group_hr_user")
    private_country_id = fields.Many2one("res.country", string="Private Country", groups="hr.group_hr_user")
    private_phone = fields.Char(string="Private Phone", groups="hr.group_hr_user")
    private_email = fields.Char(string="Private Email", groups="hr.group_hr_user")
    lang = fields.Selection(selection=_lang_get, string="Lang", groups="hr.group_hr_user")
    country_id = fields.Many2one(
        'res.country', 'Nationality (Country)', groups="hr.group_hr_user", tracking=True)
    gender = fields.Selection([
        ('male', 'Male'),
        ('female', 'Female'),
        ('other', 'Other')
    ], groups="hr.group_hr_user", tracking=True)
    marital = fields.Selection(
        selection='_get_marital_status_selection',
        string='Marital Status',
        groups="hr.group_hr_user",
        default='single',
        required=True,
        tracking=True)

    spouse_complete_name = fields.Char(string="Spouse Complete Name", groups="hr.group_hr_user", tracking=True)
    spouse_birthdate = fields.Date(string="Spouse Birthdate", groups="hr.group_hr_user", tracking=True)
    children = fields.Integer(string='Number of Dependent Children', groups="hr.group_hr_user", tracking=True)
    place_of_birth = fields.Char('Place of Birth', groups="hr.group_hr_user", tracking=True)
    country_of_birth = fields.Many2one('res.country', string="Country of Birth", groups="hr.group_hr_user", tracking=True)
    birthday = fields.Date('Date of Birth', groups="hr.group_hr_user", tracking=True)
    ssnid = fields.Char('SSN No', help='Social Security Number', groups="hr.group_hr_user", tracking=True)
    sinid = fields.Char('SIN No', help='Social Insurance Number', groups="hr.group_hr_user", tracking=True)
    identification_id = fields.Char(string='Identification No', groups="hr.group_hr_user", tracking=True)
    passport_id = fields.Char('Passport No', groups="hr.group_hr_user", tracking=True)
    bank_account_id = fields.Many2one(
        'res.partner.bank', 'Bank Account',
        domain="[('partner_id', '=', work_contact_id), '|', ('company_id', '=', False), ('company_id', '=', company_id)]",
        groups="hr.group_hr_user",
        tracking=True,
        help='Employee bank account to pay salaries')
    permit_no = fields.Char('Work Permit No', groups="hr.group_hr_user", tracking=True)
    visa_no = fields.Char('Visa No', groups="hr.group_hr_user", tracking=True)
    visa_expire = fields.Date('Visa Expiration Date', groups="hr.group_hr_user", tracking=True)
    work_permit_expiration_date = fields.Date('Work Permit Expiration Date', groups="hr.group_hr_user", tracking=True)
    has_work_permit = fields.Binary(string="Work Permit", groups="hr.group_hr_user")
    work_permit_scheduled_activity = fields.Boolean(default=False, groups="hr.group_hr_user")
    work_permit_name = fields.Char('work_permit_name', compute='_compute_work_permit_name', groups="hr.group_hr_user")
    additional_note = fields.Text(string='Additional Note', groups="hr.group_hr_user", tracking=True)
    certificate = fields.Selection([
        ('graduate', 'Graduate'),
        ('bachelor', 'Bachelor'),
        ('master', 'Master'),
        ('doctor', 'Doctor'),
        ('other', 'Other'),
    ], 'Certificate Level', groups="hr.group_hr_user", tracking=True)
    study_field = fields.Char("Field of Study", groups="hr.group_hr_user", tracking=True)
    study_school = fields.Char("School", groups="hr.group_hr_user", tracking=True)
    emergency_contact = fields.Char("Contact Name", groups="hr.group_hr_user", tracking=True)
    emergency_phone = fields.Char("Contact Phone", groups="hr.group_hr_user", tracking=True)
    distance_home_work = fields.Integer(string="Home-Work Distance", groups="hr.group_hr_user", tracking=True)
    km_home_work = fields.Integer(string="Home-Work Distance in Km", groups="hr.group_hr_user", compute="_compute_km_home_work", inverse="_inverse_km_home_work", store=True)
    distance_home_work_unit = fields.Selection([
        ('kilometers', 'km'),
        ('miles', 'mi'),
    ], 'Home-Work Distance unit', tracking=True, groups="hr.group_hr_user", default='kilometers', required=True)
    employee_type = fields.Selection([
            ('employee', 'Employee'),
            ('worker', 'Worker'),
            ('student', 'Student'),
            ('trainee', 'Trainee'),
            ('contractor', 'Contractor'),
            ('freelance', 'Freelancer'),
        ], string='Employee Type', default='employee', required=True, groups="hr.group_hr_user",
        help="Categorize your Employees by type. This field also has an impact on contracts. Only Employees, Students and Trainee will have contract history.")

    job_id = fields.Many2one(tracking=True)
    # employee in company
    child_ids = fields.One2many('hr.employee', 'parent_id', string='Direct subordinates')
    category_ids = fields.Many2many(
        'hr.employee.category', 'employee_category_rel',
        'employee_id', 'category_id', groups="hr.group_hr_user",
        string='Tags')
    # misc
    notes = fields.Text('Notes', groups="hr.group_hr_user")
    color = fields.Integer('Color Index', default=0)
    barcode = fields.Char(string="Badge ID", help="ID used for employee identification.", groups="hr.group_hr_user", copy=False)
    pin = fields.Char(string="PIN", groups="hr.group_hr_user", copy=False,
        help="PIN used to Check In/Out in the Kiosk Mode of the Attendance application (if enabled in Configuration) and to change the cashier in the Point of Sale application.")
    departure_reason_id = fields.Many2one("hr.departure.reason", string="Departure Reason", groups="hr.group_hr_user",
                                          copy=False, tracking=True, ondelete='restrict')
    departure_description = fields.Html(string="Additional Information", groups="hr.group_hr_user", copy=False)
    departure_date = fields.Date(string="Departure Date", groups="hr.group_hr_user", copy=False, tracking=True)
    message_main_attachment_id = fields.Many2one(groups="hr.group_hr_user")
    id_card = fields.Binary(string="ID Card Copy", groups="hr.group_hr_user")
    driving_license = fields.Binary(string="Driving License", groups="hr.group_hr_user")
    private_car_plate = fields.Char(groups="hr.group_hr_user", help="If you have more than one car, just separate the plates by a space.")
    currency_id = fields.Many2one('res.currency', related='company_id.currency_id', readonly=True, groups="hr.group_hr_user")
    related_partners_count = fields.Integer(compute="_compute_related_partners_count", groups="hr.group_hr_user")
    # properties
    employee_properties = fields.Properties('Properties', definition='company_id.employee_properties_definition', precompute=False, groups="hr.group_hr_user")

    # mail.activity.mixin
    activity_ids = fields.One2many(groups="hr.group_hr_user")
    activity_state = fields.Selection(groups="hr.group_hr_user")
    activity_user_id = fields.Many2one(groups="hr.group_hr_user")
    activity_type_id = fields.Many2one(groups="hr.group_hr_user")
    activity_type_icon = fields.Char(groups="hr.group_hr_user")
    activity_date_deadline = fields.Date(groups="hr.group_hr_user")
    my_activity_date_deadline = fields.Date(groups="hr.group_hr_user")
    activity_summary = fields.Char(groups="hr.group_hr_user")
    activity_exception_decoration = fields.Selection(groups="hr.group_hr_user")
    activity_exception_icon = fields.Char(groups="hr.group_hr_user")

    # mail.thread mixin
    message_is_follower = fields.Boolean(groups="hr.group_hr_user")
    message_follower_ids = fields.One2many(groups="hr.group_hr_user")
    message_partner_ids = fields.Many2many(groups="hr.group_hr_user")
    message_ids = fields.One2many(groups="hr.group_hr_user")
    has_message = fields.Boolean(groups="hr.group_hr_user")
    message_needaction = fields.Boolean(groups="hr.group_hr_user")
    message_needaction_counter = fields.Integer(groups="hr.group_hr_user")
    message_has_error = fields.Boolean(groups="hr.group_hr_user")
    message_has_error_counter = fields.Integer(groups="hr.group_hr_user")
    message_attachment_count = fields.Integer(groups="hr.group_hr_user")

    _sql_constraints = [
        ('barcode_uniq', 'unique (barcode)', "The Badge ID must be unique, this one is already assigned to another employee."),
        ('user_uniq', 'unique (user_id, company_id)', "A user cannot be linked to multiple employees in the same company.")
    ]

    @api.model
    def check_field_access_rights(self, operation, field_names):
        # DISCLAIMER: Dirty hack to avoid having to create a bridge module to override only a
        # groups on a field which is not prefetched (because not stored) but would crash anyway
        # if we try to read them directly (very uncommon use case). Don't add your field on this
        # list if you can specify the group on the field directly (as all the other fields).
        result = super().check_field_access_rights(operation, field_names)
        if not self.env.user.has_group("hr.group_hr_user"):
            result = [field for field in result if field not in ['activity_calendar_event_id', 'rating_ids', 'website_message_ids', 'message_has_sms_error']]
        return result

    @api.depends('name', 'user_id.avatar_1920', 'image_1920')
    def _compute_avatar_1920(self):
        super()._compute_avatar_1920()

    @api.depends('name', 'user_id.avatar_1024', 'image_1024')
    def _compute_avatar_1024(self):
        super()._compute_avatar_1024()

    @api.depends('name', 'user_id.avatar_512', 'image_512')
    def _compute_avatar_512(self):
        super()._compute_avatar_512()

    @api.depends('name', 'user_id.avatar_256', 'image_256')
    def _compute_avatar_256(self):
        super()._compute_avatar_256()

    @api.depends('name', 'user_id.avatar_128', 'image_128')
    def _compute_avatar_128(self):
        super()._compute_avatar_128()

    def _compute_avatar(self, avatar_field, image_field):
        employee_wo_user_and_image = self.env['hr.employee']
        for employee in self:
            if not employee.user_id and not employee._origin[image_field]:
                employee_wo_user_and_image += employee
                continue
            avatar = employee._origin[image_field]
            if not avatar and employee.user_id:
                avatar = employee.user_id.sudo()[avatar_field]
            employee[avatar_field] = avatar
        super(HrEmployeePrivate, employee_wo_user_and_image)._compute_avatar(avatar_field, image_field)

    @api.depends('name', 'permit_no')
    def _compute_work_permit_name(self):
        for employee in self:
            name = employee.name.replace(' ', '_') + '_' if employee.name else ''
            permit_no = '_' + employee.permit_no if employee.permit_no else ''
            employee.work_permit_name = "%swork_permit%s" % (name, permit_no)

    @api.depends('distance_home_work', 'distance_home_work_unit')
    def _compute_km_home_work(self):
        for employee in self:
            employee.km_home_work = employee.distance_home_work * 1.609 if employee.distance_home_work_unit == "miles" else employee.distance_home_work

    def _inverse_km_home_work(self):
        for employee in self:
            employee.distance_home_work = employee.km_home_work / 1.609 if employee.distance_home_work_unit == "miles" else employee.distance_home_work

    def _get_partner_count_depends(self):
        return ['user_id']

    @api.depends(lambda self: self._get_partner_count_depends())
    def _compute_related_partners_count(self):
        self.related_partners_count = len(self._get_related_partners())

    def _get_related_partners(self):
        return self.work_contact_id | self.user_id.partner_id

    def action_related_contacts(self):
        related_partners = self._get_related_partners()
        action = {
            'name': _("Related Contacts"),
            'type': 'ir.actions.act_window',
            'res_model': 'res.partner',
            'view_mode': 'form',
        }
        if len(related_partners) > 1:
            action['view_mode'] = 'kanban,list,form'
            action['domain'] = [('id', 'in', related_partners.ids)]
            return action
        else:
            action['res_id'] = related_partners.id
        return action

    def action_create_user(self):
        self.ensure_one()
        if self.user_id:
            raise ValidationError(_("This employee already has an user."))
        return {
            'name': _('Create User'),
            'type': 'ir.actions.act_window',
            'res_model': 'res.users',
            'view_mode': 'form',
            'view_id': self.env.ref('hr.view_users_simple_form').id,
            'target': 'new',
            'context': dict(self._context, **{
                'default_create_employee_id': self.id,
                'default_name': self.name,
                'default_phone': self.work_phone,
                'default_mobile': self.mobile_phone,
                'default_login': self.work_email,
                'default_partner_id': self.work_contact_id.id,
            })
        }

    def _compute_display_name(self):
        if self.browse().has_access('read'):
            return super()._compute_display_name()
        for employee_private, employee_public in zip(self, self.env['hr.employee.public'].browse(self.ids)):
            employee_private.display_name = employee_public.display_name

    def search_fetch(self, domain, field_names, offset=0, limit=None, order=None):
        if self.browse().has_access('read'):
            return super().search_fetch(domain, field_names, offset, limit, order)

        # HACK: retrieve publicly available values from hr.employee.public and
        # copy them to the cache of self; non-public data will be missing from
        # cache, and interpreted as an access error
        self._check_private_fields(field_names)
        self.flush_model(field_names)
        public = self.env['hr.employee.public'].search_fetch(domain, field_names, offset, limit, order)
        employees = self.browse(public._ids)
        employees._copy_cache_from(public, field_names)
        return employees

    def fetch(self, field_names):
        if self.browse().has_access('read'):
            return super().fetch(field_names)

        # HACK: retrieve publicly available values from hr.employee.public and
        # copy them to the cache of self; non-public data will be missing from
        # cache, and interpreted as an access error
        self._check_private_fields(field_names)
        self.flush_recordset(field_names)
        public = self.env['hr.employee.public'].browse(self._ids)
        public.fetch(field_names)
        self._copy_cache_from(public, field_names)

    def _check_private_fields(self, field_names):
        """ Check whether ``field_names`` contain private fields. """
        public_fields = self.env['hr.employee.public']._fields
        private_fields = [fname for fname in field_names if fname not in public_fields]
        if private_fields:
            raise AccessError(_('The fields “%s”, which you are trying to read, are not available for employee public profiles.', ','.join(private_fields)))

    def _copy_cache_from(self, public, field_names):
        # HACK: retrieve publicly available values from hr.employee.public and
        # copy them to the cache of self; non-public data will be missing from
        # cache, and interpreted as an access error
        for fname in field_names:
            values = self.env.cache.get_values(public, public._fields[fname])
            if self._fields[fname].translate:
                values = [(value.copy() if value else None) for value in values]
            self.env.cache.update_raw(self, self._fields[fname], values)

    @api.model
    def _cron_check_work_permit_validity(self):
        # Called by a cron
        # Schedule an activity 1 month before the work permit expires
        outdated_days = fields.Date.today() + relativedelta(months=+1)
        nearly_expired_work_permits = self.search([('work_permit_scheduled_activity', '=', False), ('work_permit_expiration_date', '<', outdated_days)])
        employees_scheduled = self.env['hr.employee']
        for employee in nearly_expired_work_permits.filtered(lambda employee: employee.parent_id):
            responsible_user_id = employee.parent_id.user_id.id
            if responsible_user_id:
                employees_scheduled |= employee
                lang = self.env['res.users'].browse(responsible_user_id).lang
                formated_date = format_date(employee.env, employee.work_permit_expiration_date, date_format="dd MMMM y", lang_code=lang)
                employee.activity_schedule(
                    'mail.mail_activity_data_todo',
                    note=_('The work permit of %(employee)s expires at %(date)s.',
                        employee=employee.name,
                        date=formated_date),
                    user_id=responsible_user_id)
        employees_scheduled.write({'work_permit_scheduled_activity': True})

    @api.model
    def get_view(self, view_id=None, view_type='form', **options):
        if self.browse().has_access('read'):
            return super().get_view(view_id, view_type, **options)
        return self.env['hr.employee.public'].get_view(view_id, view_type, **options)

    @api.model
    def get_views(self, views, options=None):
        if self.browse().has_access('read'):
            return super().get_views(views, options)
        res = self.env['hr.employee.public'].get_views(views, options)
        res['models'].update({'hr.employee': res['models']['hr.employee.public']})
        return res

    @api.model
    def _search(self, domain, offset=0, limit=None, order=None):
        """
            We override the _search because it is the method that checks the access rights
            This is correct to override the _search. That way we enforce the fact that calling
            search on an hr.employee returns a hr.employee recordset, even if you don't have access
            to this model, as the result of _search (the ids of the public employees) is to be
            browsed on the hr.employee model. This can be trusted as the ids of the public
            employees exactly match the ids of the related hr.employee.
        """
        if self.browse().has_access('read'):
            return super()._search(domain, offset, limit, order)
        try:
            ids = self.env['hr.employee.public']._search(domain, offset, limit, order)
        except ValueError:
            raise AccessError(_('You do not have access to this document.'))
        # the result is expected from this table, so we should link tables
        return super(HrEmployeePrivate, self.sudo())._search([('id', 'in', ids)], order=order)

    def get_formview_id(self, access_uid=None):
        """ Override this method in order to redirect many2one towards the right model depending on access_uid """
        if access_uid:
            self_sudo = self.with_user(access_uid)
        else:
            self_sudo = self

        if self_sudo.browse().has_access('read'):
            return super(HrEmployeePrivate, self).get_formview_id(access_uid=access_uid)
        # Hardcode the form view for public employee
        return self.env.ref('hr.hr_employee_public_view_form').id

    def get_formview_action(self, access_uid=None):
        """ Override this method in order to redirect many2one towards the right model depending on access_uid """
        res = super(HrEmployeePrivate, self).get_formview_action(access_uid=access_uid)
        if access_uid:
            self_sudo = self.with_user(access_uid)
        else:
            self_sudo = self

        if not self_sudo.browse().has_access('read'):
            res['res_model'] = 'hr.employee.public'

        return res

    @api.constrains('pin')
    def _verify_pin(self):
        for employee in self:
            if employee.pin and not employee.pin.isdigit():
                raise ValidationError(_("The PIN must be a sequence of digits."))

    @api.constrains('barcode')
    def _verify_barcode(self):
        for employee in self:
            if employee.barcode and not employee.barcode.isdigit():
                raise ValidationError(_("The Badge ID must be a sequence of digits."))

    @api.constrains('ssnid')
    def _check_ssnid(self):
        # By default, an Social Security Number is always valid, but each localization
        # may want to add its own constraints
        pass

    @api.onchange('user_id')
    def _onchange_user(self):
        self.update(self._sync_user(self.user_id, (bool(self.image_1920))))
        if not self.name:
            self.name = self.user_id.name

    @api.onchange('resource_calendar_id')
    def _onchange_timezone(self):
        if self.resource_calendar_id and not self.tz:
            self.tz = self.resource_calendar_id.tz

    def _sync_user(self, user, employee_has_image=False):
        vals = dict(
            work_contact_id=user.partner_id.id,
            user_id=user.id,
        )
        if not employee_has_image:
            vals['image_1920'] = user.image_1920
        if user.tz:
            vals['tz'] = user.tz
        return vals

    def _prepare_resource_values(self, vals, tz):
        resource_vals = super()._prepare_resource_values(vals, tz)
        vals.pop('name')  # Already considered by super call but no popped
        # We need to pop it to avoid useless resource update (& write) call
        # on every newly created resource (with the correct name already)
        user_id = vals.pop('user_id', None)
        if user_id:
            resource_vals['user_id'] = user_id
        active_status = vals.get('active')
        if active_status is not None:
            resource_vals['active'] = active_status
        return resource_vals

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('user_id'):
                user = self.env['res.users'].browse(vals['user_id'])
                vals.update(self._sync_user(user, bool(vals.get('image_1920'))))
                vals['name'] = vals.get('name', user.name)
        employees = super().create(vals_list)
        # Sudo in case HR officer doesn't have the Contact Creation group
        employees.filtered(lambda e: not e.work_contact_id).sudo()._create_work_contacts()
        for employee_sudo in employees.sudo():
            if not employee_sudo.image_1920:
                employee_sudo.image_1920 = employee_sudo._avatar_generate_svg()
                employee_sudo.work_contact_id.image_1920 = employee_sudo.image_1920
        if self.env.context.get('salary_simulation'):
            return employees
        employee_departments = employees.department_id
        if employee_departments:
            self.env['discuss.channel'].sudo().search([
                ('subscription_department_ids', 'in', employee_departments.ids)
            ])._subscribe_users_automatically()
        onboarding_notes_bodies = {}
        hr_root_menu = self.env.ref('hr.menu_hr_root')
        for employee in employees:
            # Launch onboarding plans
            url = '/odoo/%s/action-hr.plan_wizard_action?active_model=hr.employee&menu_id=%s' % (employee.id, hr_root_menu.id)
            onboarding_notes_bodies[employee.id] = Markup(_(
                '<b>Congratulations!</b> May I recommend you to setup an <a href="%s">onboarding plan?</a>',
            )) % url
        employees._message_log_batch(onboarding_notes_bodies)
        return employees

    def write(self, vals):
        if 'work_contact_id' in vals:
            account_ids = vals.get('bank_account_id') or self.bank_account_id.ids
            if account_ids:
                bank_accounts = self.env['res.partner.bank'].sudo().browse(account_ids)
                for bank_account in bank_accounts:
                    if vals['work_contact_id'] != bank_account.partner_id.id:
                        if bank_account.allow_out_payment:
                            bank_account.allow_out_payment = False
                        if vals['work_contact_id']:
                            bank_account.partner_id = vals['work_contact_id']
            self.message_unsubscribe(self.work_contact_id.ids)
            if vals['work_contact_id']:
                self._message_subscribe([vals['work_contact_id']])
        if 'user_id' in vals:
            # Update the profile pictures with user, except if provided
            vals.update(self._sync_user(self.env['res.users'].browse(vals['user_id']),
                                        (bool(all(emp.image_1920 for emp in self)))))
        if 'work_permit_expiration_date' in vals:
            vals['work_permit_scheduled_activity'] = False
        res = super(HrEmployeePrivate, self).write(vals)
        if vals.get('department_id') or vals.get('user_id'):
            department_id = vals['department_id'] if vals.get('department_id') else self[:1].department_id.id
            # When added to a department or changing user, subscribe to the channels auto-subscribed by department
            self.env['discuss.channel'].sudo().search([
                ('subscription_department_ids', 'in', department_id)
            ])._subscribe_users_automatically()
        if vals.get('departure_description'):
            self.message_post(body=_(
                'Additional Information: \n %(description)s',
                description=vals.get('departure_description')))
        return res

    def unlink(self):
        resources = self.mapped('resource_id')
        super(HrEmployeePrivate, self).unlink()
        return resources.unlink()

    def _get_employee_m2o_to_empty_on_archived_employees(self):
        return ['parent_id', 'coach_id']

    def _get_user_m2o_to_empty_on_archived_employees(self):
        return []

    def toggle_active(self):
        res = super(HrEmployeePrivate, self).toggle_active()
        unarchived_employees = self.filtered(lambda employee: employee.active)
        unarchived_employees.write({
            'departure_reason_id': False,
            'departure_description': False,
            'departure_date': False
        })

        archived_employees = self.filtered(lambda e: not e.active)
        if archived_employees:
            # Empty links to this employees (example: manager, coach, time off responsible, ...)
            employee_fields_to_empty = self._get_employee_m2o_to_empty_on_archived_employees()
            user_fields_to_empty = self._get_user_m2o_to_empty_on_archived_employees()
            employee_domain = [[(field, 'in', archived_employees.ids)] for field in employee_fields_to_empty]
            user_domain = [[(field, 'in', archived_employees.user_id.ids) for field in user_fields_to_empty]]
            employees = self.env['hr.employee'].search(expression.OR(employee_domain + user_domain))
            for employee in employees:
                for field in employee_fields_to_empty:
                    if employee[field] in archived_employees:
                        employee[field] = False
                for field in user_fields_to_empty:
                    if employee[field] in archived_employees.user_id:
                        employee[field] = False

        if len(self) == 1 and not self.active and not self.env.context.get('no_wizard', False):
            return {
                'type': 'ir.actions.act_window',
                'name': _('Register Departure'),
                'res_model': 'hr.departure.wizard',
                'view_mode': 'form',
                'target': 'new',
                'context': {'active_id': self.id},
                'views': [[False, 'form']]
            }
        return res

    @api.onchange('company_id')
    def _onchange_company_id(self):
        if self._origin:
            return {'warning': {
                'title': _("Warning"),
                'message': _("To avoid multi company issues (losing the access to your previous contracts, leaves, ...), you should create another employee in the new company instead.")
            }}

    def generate_random_barcode(self):
        for employee in self:
            employee.barcode = '041'+"".join(choice(digits) for i in range(9))

    def _get_tz(self):
        # Finds the first valid timezone in his tz, his work hours tz,
        #  the company calendar tz or UTC and returns it as a string
        self.ensure_one()
        return self.tz or\
               self.resource_calendar_id.tz or\
               self.company_id.resource_calendar_id.tz or\
               'UTC'

    def _get_tz_batch(self):
        # Finds the first valid timezone in his tz, his work hours tz,
        #  the company calendar tz or UTC
        # Returns a dict {employee_id: tz}
        return {emp.id: emp._get_tz() for emp in self}

    def _employee_attendance_intervals(self, start, stop, lunch=False):
        self.ensure_one()
        calendar = self.resource_calendar_id or self.company_id.resource_calendar_id
        if not lunch:
            return self._get_expected_attendances(start, stop)
        else:
            return calendar._attendance_intervals_batch(start, stop, self.resource_id, lunch=True)[self.resource_id.id]

    def _get_expected_attendances(self, date_from, date_to):
        self.ensure_one()
        employee_timezone = timezone(self.tz) if self.tz else None
        calendar = self.resource_calendar_id or self.company_id.resource_calendar_id
        calendar_intervals = calendar._work_intervals_batch(
                                date_from,
                                date_to,
                                tz=employee_timezone,
                                resources=self.resource_id,
                                compute_leaves=True,
                                domain=[('company_id', 'in', [False, self.company_id.id])])[self.resource_id.id]
        return calendar_intervals

    def _get_calendar_attendances(self, date_from, date_to):
        self.ensure_one()
        employee_timezone = timezone(self.tz) if self.tz else None
        calendar = self.resource_calendar_id or self.company_id.resource_calendar_id
        return calendar\
            .with_context(employee_timezone=employee_timezone)\
            .get_work_duration_data(
                date_from,
                date_to,
                domain=[('company_id', 'in', [False, self.company_id.id])])

    def _get_marital_status_selection(self):
        return [
            ('single', 'Single'),
            ('married', 'Married'),
            ('cohabitant', 'Legal Cohabitant'),
            ('widower', 'Widower'),
            ('divorced', 'Divorced')
        ]

    def _load_scenario(self):
        demo_tag = self.env.ref('hr.employee_category_demo', raise_if_not_found=False)
        if demo_tag:
            return
        convert.convert_file(self.env, 'hr', 'data/scenarios/hr_scenario.xml', None, mode='init', kind='data')

    # ---------------------------------------------------------
    # Business Methods
    # ---------------------------------------------------------

    @api.model
    def get_import_templates(self):
        return [{
            'label': _('Import Template for Employees'),
            'template': '/hr/static/xls/hr_employee.xls'
        }]

    def _get_unusual_days(self, date_from, date_to=None):
        # Checking the calendar directly allows to not grey out the leaves taken
        # by the employee or fallback to the company calendar
        return (self.resource_calendar_id or self.env.company.resource_calendar_id)._get_unusual_days(
            datetime.combine(fields.Date.from_string(date_from), time.min).replace(tzinfo=UTC),
            datetime.combine(fields.Date.from_string(date_to), time.max).replace(tzinfo=UTC),
            self.company_id,
        )

    def _get_age(self, target_date=None):
        self.ensure_one()
        if target_date is None:
            target_date = fields.Date.context_today(self.env.user)
        return relativedelta(target_date, self.birthday).years if self.birthday else 0

    # ---------------------------------------------------------
    # Messaging
    # ---------------------------------------------------------

    def _phone_get_number_fields(self):
        return ['mobile_phone']

    def _mail_get_partner_fields(self, introspect_fields=False):
        return ['user_partner_id']
