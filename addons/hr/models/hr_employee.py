# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
from random import choice
from string import digits
import itertools
from werkzeug import url_encode
import pytz

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, AccessError
from odoo.modules.module import get_module_resource
from odoo.addons.resource.models.resource_mixin import timezone_datetime


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
    _inherit = ['hr.employee.base', 'mail.thread', 'mail.activity.mixin', 'resource.mixin', 'image.mixin']
    _mail_post_access = 'read'

    @api.model
    def _default_image(self):
        image_path = get_module_resource('hr', 'static/src/img', 'default_image.png')
        return base64.b64encode(open(image_path, 'rb').read())

    # resource and user
    # required on the resource, make sure required="True" set in the view
    name = fields.Char(string="Employee Name", related='resource_id.name', store=True, readonly=False, tracking=True)
    user_id = fields.Many2one('res.users', 'User', related='resource_id.user_id', store=True, readonly=False)
    user_partner_id = fields.Many2one(related='user_id.partner_id', related_sudo=False, string="User's partner")
    active = fields.Boolean('Active', related='resource_id.active', default=True, store=True, readonly=False)
    # private partner
    address_home_id = fields.Many2one(
        'res.partner', 'Address', help='Enter here the private address of the employee, not the one linked to your company.',
        groups="hr.group_hr_user", tracking=True,
        domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]")
    is_address_home_a_company = fields.Boolean(
        'The employee address has a company linked',
        compute='_compute_is_address_home_a_company',
    )
    private_email = fields.Char(related='address_home_id.email', string="Private Email", groups="hr.group_hr_user")
    country_id = fields.Many2one(
        'res.country', 'Nationality (Country)', groups="hr.group_hr_user", tracking=True)
    gender = fields.Selection([
        ('male', 'Male'),
        ('female', 'Female'),
        ('other', 'Other')
    ], groups="hr.group_hr_user", default="male", tracking=True)
    marital = fields.Selection([
        ('single', 'Single'),
        ('married', 'Married'),
        ('cohabitant', 'Legal Cohabitant'),
        ('widower', 'Widower'),
        ('divorced', 'Divorced')
    ], string='Marital Status', groups="hr.group_hr_user", default='single', tracking=True)
    spouse_complete_name = fields.Char(string="Spouse Complete Name", groups="hr.group_hr_user", tracking=True)
    spouse_birthdate = fields.Date(string="Spouse Birthdate", groups="hr.group_hr_user", tracking=True)
    children = fields.Integer(string='Number of Children', groups="hr.group_hr_user", tracking=True)
    place_of_birth = fields.Char('Place of Birth', groups="hr.group_hr_user", tracking=True)
    country_of_birth = fields.Many2one('res.country', string="Country of Birth", groups="hr.group_hr_user", tracking=True)
    birthday = fields.Date('Date of Birth', groups="hr.group_hr_user", tracking=True)
    ssnid = fields.Char('SSN No', help='Social Security Number', groups="hr.group_hr_user", tracking=True)
    sinid = fields.Char('SIN No', help='Social Insurance Number', groups="hr.group_hr_user", tracking=True)
    identification_id = fields.Char(string='Identification No', groups="hr.group_hr_user", tracking=True)
    passport_id = fields.Char('Passport No', groups="hr.group_hr_user", tracking=True)
    bank_account_id = fields.Many2one(
        'res.partner.bank', 'Bank Account Number',
        domain="[('partner_id', '=', address_home_id), '|', ('company_id', '=', False), ('company_id', '=', company_id)]",
        groups="hr.group_hr_user",
        tracking=True,
        help='Employee bank salary account')
    permit_no = fields.Char('Work Permit No', groups="hr.group_hr_user", tracking=True)
    visa_no = fields.Char('Visa No', groups="hr.group_hr_user", tracking=True)
    visa_expire = fields.Date('Visa Expire Date', groups="hr.group_hr_user", tracking=True)
    additional_note = fields.Text(string='Additional Note', groups="hr.group_hr_user", tracking=True)
    certificate = fields.Selection([
        ('bachelor', 'Bachelor'),
        ('master', 'Master'),
        ('other', 'Other'),
    ], 'Certificate Level', default='other', groups="hr.group_hr_user", tracking=True)
    study_field = fields.Char("Field of Study", groups="hr.group_hr_user", tracking=True)
    study_school = fields.Char("School", groups="hr.group_hr_user", tracking=True)
    emergency_contact = fields.Char("Emergency Contact", groups="hr.group_hr_user", tracking=True)
    emergency_phone = fields.Char("Emergency Phone", groups="hr.group_hr_user", tracking=True)
    km_home_work = fields.Integer(string="Km Home-Work", groups="hr.group_hr_user", tracking=True)

    image_1920 = fields.Image(default=_default_image)
    phone = fields.Char(related='address_home_id.phone', related_sudo=False, string="Private Phone", groups="hr.group_hr_user")
    # employee in company
    child_ids = fields.One2many('hr.employee', 'parent_id', string='Direct subordinates')
    category_ids = fields.Many2many(
        'hr.employee.category', 'employee_category_rel',
        'emp_id', 'category_id', groups="hr.group_hr_manager",
        string='Tags')
    # misc
    notes = fields.Text('Notes', groups="hr.group_hr_user")
    color = fields.Integer('Color Index', default=0, groups="hr.group_hr_user")
    barcode = fields.Char(string="Badge ID", help="ID used for employee identification.", groups="hr.group_hr_user", copy=False)
    pin = fields.Char(string="PIN", groups="hr.group_hr_user", copy=False,
        help="PIN used to Check In/Out in Kiosk Mode (if enabled in Configuration).")
    departure_reason = fields.Selection([
        ('fired', 'Fired'),
        ('resigned', 'Resigned'),
        ('retired', 'Retired')
    ], string="Departure Reason", groups="hr.group_hr_user", copy=False, tracking=True)
    departure_description = fields.Text(string="Additional Information", groups="hr.group_hr_user", copy=False, tracking=True)
    message_main_attachment_id = fields.Many2one(groups="hr.group_hr_user")

    _sql_constraints = [
        ('barcode_uniq', 'unique (barcode)', "The Badge ID must be unique, this one is already assigned to another employee."),
        ('user_uniq', 'unique (user_id, company_id)', "A user cannot be linked to multiple employees in the same company.")
    ]

    def name_get(self):
        if self.check_access_rights('read', raise_exception=False):
            return super(HrEmployeePrivate, self).name_get()
        return self.env['hr.employee.public'].browse(self.ids).name_get()

    def _read(self, fields):
        if self.check_access_rights('read', raise_exception=False):
            return super(HrEmployeePrivate, self)._read(fields)

        res = self.env['hr.employee.public'].browse(self.ids).read(fields)
        for r in res:
            record = self.browse(r['id'])
            record._update_cache({k:v for k,v in r.items() if k in fields}, validate=False)

    def read(self, fields, load='_classic_read'):
        if self.check_access_rights('read', raise_exception=False):
            return super(HrEmployeePrivate, self).read(fields, load=load)
        private_fields = set(fields).difference(self.env['hr.employee.public']._fields.keys())
        if private_fields:
            raise AccessError(_('The fields "%s" you try to read is not available on the public employee profile.') % (','.join(private_fields)))
        return self.env['hr.employee.public'].browse(self.ids).read(fields, load=load)

    @api.model
    def load_views(self, views, options=None):
        if self.check_access_rights('read', raise_exception=False):
            return super(HrEmployeePrivate, self).load_views(views, options=options)
        return self.env['hr.employee.public'].load_views(views, options=options)

    @api.model
    def _search(self, args, offset=0, limit=None, order=None, count=False, access_rights_uid=None):
        """
            We override the _search because it is the method that checks the access rights
            This is correct to override the _search. That way we enforce the fact that calling
            search on an hr.employee returns a hr.employee recordset, even if you don't have access
            to this model, as the result of _search (the ids of the public employees) is to be
            browsed on the hr.employee model. This can be trusted as the ids of the public
            employees exactly match the ids of the related hr.employee.
        """
        if self.check_access_rights('read', raise_exception=False):
            return super(HrEmployeePrivate, self)._search(args, offset=offset, limit=limit, order=order, count=count, access_rights_uid=access_rights_uid)
        return self.env['hr.employee.public']._search(args, offset=offset, limit=limit, order=order, count=count, access_rights_uid=access_rights_uid)

    def get_formview_id(self, access_uid=None):
        """ Override this method in order to redirect many2one towards the right model depending on access_uid """
        if access_uid:
            self_sudo = self.with_user(access_uid)
        else:
            self_sudo = self

        if self_sudo.check_access_rights('read', raise_exception=False):
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

        if not self_sudo.check_access_rights('read', raise_exception=False):
            res['res_model'] = 'hr.employee.public'

        return res

    @api.constrains('pin')
    def _verify_pin(self):
        for employee in self:
            if employee.pin and not employee.pin.isdigit():
                raise ValidationError(_("The PIN must be a sequence of digits."))

    @api.onchange('job_id')
    def _onchange_job_id(self):
        if self.job_id:
            self.job_title = self.job_id.name

    @api.onchange('address_id')
    def _onchange_address(self):
        self.work_phone = self.address_id.phone
        self.mobile_phone = self.address_id.mobile

    @api.onchange('company_id')
    def _onchange_company(self):
        address = self.company_id.partner_id.address_get(['default'])
        self.address_id = address['default'] if address else False

    @api.onchange('department_id')
    def _onchange_department(self):
        if self.department_id.manager_id:
            self.parent_id = self.department_id.manager_id

    @api.onchange('user_id')
    def _onchange_user(self):
        if self.user_id:
            self.update(self._sync_user(self.user_id))
            if not self.name:
                self.name = self.user_id.name

    @api.onchange('resource_calendar_id')
    def _onchange_timezone(self):
        if self.resource_calendar_id and not self.tz:
            self.tz = self.resource_calendar_id.tz

    def _sync_user(self, user):
        vals = dict(
            image_1920=user.image_1920,
            work_email=user.email,
            user_id=user.id,
        )
        if user.tz:
            vals['tz'] = user.tz
        return vals

    @api.model
    def create(self, vals):
        if vals.get('user_id'):
            user = self.env['res.users'].browse(vals['user_id'])
            vals.update(self._sync_user(user))
            vals['name'] = vals.get('name', user.name)
        employee = super(HrEmployeePrivate, self).create(vals)
        url = '/web#%s' % url_encode({
            'action': 'hr.plan_wizard_action',
            'active_id': employee.id,
            'active_model': 'hr.employee',
            'menu_id': self.env.ref('hr.menu_hr_root').id,
        })
        employee._message_log(body=_('<b>Congratulations!</b> May I recommend you to setup an <a href="%s">onboarding plan?</a>') % (url))
        if employee.department_id:
            self.env['mail.channel'].sudo().search([
                ('subscription_department_ids', 'in', employee.department_id.id)
            ])._subscribe_users()
        return employee

    def write(self, vals):
        if 'address_home_id' in vals:
            account_id = vals.get('bank_account_id') or self.bank_account_id.id
            if account_id:
                self.env['res.partner.bank'].browse(account_id).partner_id = vals['address_home_id']
        if vals.get('user_id'):
            vals.update(self._sync_user(self.env['res.users'].browse(vals['user_id'])))
        res = super(HrEmployeePrivate, self).write(vals)
        if vals.get('department_id') or vals.get('user_id'):
            department_id = vals['department_id'] if vals.get('department_id') else self[:1].department_id.id
            # When added to a department or changing user, subscribe to the channels auto-subscribed by department
            self.env['mail.channel'].sudo().search([
                ('subscription_department_ids', 'in', department_id)
            ])._subscribe_users()
        return res

    def unlink(self):
        resources = self.mapped('resource_id')
        super(HrEmployeePrivate, self).unlink()
        return resources.unlink()

    def toggle_active(self):
        res = super(HrEmployeePrivate, self).toggle_active()
        self.filtered(lambda employee: employee.active).write({
            'departure_reason': False,
            'departure_description': False,
        })
        if len(self) == 1 and not self.active:
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

    def generate_random_barcode(self):
        for employee in self:
            employee.barcode = '041'+"".join(choice(digits) for i in range(9))

    @api.depends('address_home_id.parent_id')
    def _compute_is_address_home_a_company(self):
        """Checks that chosen address (res.partner) is not linked to a company.
        """
        for employee in self:
            try:
                employee.is_address_home_a_company = employee.address_home_id.parent_id.id is not False
            except AccessError:
                employee.is_address_home_a_company = False

    # ---------------------------------------------------------
    # Business Methods
    # ---------------------------------------------------------

    @api.model
    def get_import_templates(self):
        return [{
            'label': _('Import Template for Employees'),
            'template': '/hr/static/xls/hr_employee.xls'
        }]

    def _post_author(self):
        """
        When a user updates his own employee's data, all operations are performed
        by super user. However, tracking messages should not be posted as OdooBot
        but as the actual user.
        This method is used in the overrides of `_message_log` and `message_post`
        to post messages as the correct user.
        """
        real_user = self.env.context.get('binary_field_real_user')
        if self.env.is_superuser() and real_user:
            self = self.with_user(real_user)
        return self

    # ---------------------------------------------------------
    # Messaging
    # ---------------------------------------------------------

    def _message_log(self, **kwargs):
        return super(HrEmployeePrivate, self._post_author())._message_log(**kwargs)

    @api.returns('mail.message', lambda value: value.id)
    def message_post(self, **kwargs):
        return super(HrEmployeePrivate, self._post_author()).message_post(**kwargs)

    def _sms_get_partner_fields(self):
        return ['user_partner_id']

    def _sms_get_number_fields(self):
        return ['mobile_phone']
