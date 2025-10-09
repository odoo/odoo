# Part of Odoo. See LICENSE file for full copyright and licensing details.

import ast

from markupsafe import Markup

from odoo import _, api, fields, models
from odoo.exceptions import AccessError
from odoo.fields import Domain
from odoo.tools.misc import clean_context


def field_employee(field_type: type[fields.Field], name: str, *, field_name='', user_writeable=False, **kw):
    """Simulating a related field "employee_id.{name}".

    Current user is read and updated with `sudo()`. Otherwise, behaves as a
    simple related field.

    :param field_name: provide if you name your field in some other way than
        on the employee model
    """
    # simulating a related field which bypasses access only for the current user
    assert 'related' not in kw and 'store' not in kw, "Unsupported parameters found"
    if not field_name:
        field_name = name

    @api.depends(f'employee_id.{name}')
    @api.depends_context('uid')
    def compute_employee_field(self):
        current_user = self.env.user
        for user in self:
            if user == current_user:
                employee = user.sudo().employee_id.with_prefetch()
            else:
                employee = user.employee_id
            user[field_name] = employee[name]

    def inverse_employee_field(self):
        current_user = self.env.user
        for user in self:
            if user_writeable and user == current_user:
                employee = user.sudo().employee_id.with_prefetch()
            else:
                employee = user.employee_id
            employee[name] = user[field_name]

    def search_employee_field(self, operator, value):
        if operator in Domain.NEGATIVE_OPERATORS:
            return NotImplemented
        subdomain = Domain(name, operator, value)
        Employee = self.env['hr.employee']
        if Employee.has_access('read') and Employee._has_field_access(Employee._fields[name], 'read'):
            return Domain('employee_id', 'any', subdomain)
        else:
            user = self.env.user.employee_id.filtered_domain(subdomain).user_id
            return Domain('id', 'in', user.ids)

    # mark the compute function for identification later
    compute_employee_field.is_field_employee = True
    return field_type(
        **kw,
        compute=compute_employee_field,
        inverse=inverse_employee_field,
        search=search_employee_field,
        user_writeable=user_writeable,
    )


class ResUsers(models.Model):
    _inherit = 'res.users'

    def _employee_ids_domain(self):
        # employee_ids is considered a safe field and as such will be fetched as sudo.
        # So try to enforce the security rules on the field to make sure we do not load employees outside of active companies
        return [('company_id', 'in', self.env.companies.ids)]

    # note: a user can only be linked to one employee per company (see sql constraint in `hr.employee`)
    employee_ids = fields.One2many('hr.employee', 'user_id', string='Related employee', domain=_employee_ids_domain)
    employee_public_ids = fields.One2many('hr.employee.public', 'user_id', string='Related employee (public)', domain=_employee_ids_domain, readonly=True)
    employee_id = fields.Many2one('hr.employee', string="Company employee",
        compute='_compute_company_employee', search='_search_company_employee', readonly=True)

    job_title = field_employee(fields.Char, 'job_title', user_writeable=True)
    work_phone = field_employee(fields.Char, 'work_phone', user_writeable=True)
    mobile_phone = field_employee(fields.Char, 'mobile_phone', user_writeable=True)
    work_email = field_employee(fields.Char, 'work_email', user_writeable=True)
    category_ids = field_employee(fields.Many2many, 'category_ids', comodel_name='hr.employee.category', string="Employee Tags", user_writeable=True)
    work_contact_id = field_employee(fields.Many2one, 'work_contact_id', comodel_name='res.partner')
    work_location_id = field_employee(fields.Many2one, 'work_location_id', comodel_name='hr.work.location', user_writeable=True)
    work_location_name = fields.Char(related="employee_id.work_location_name")
    work_location_type = fields.Selection(related="employee_id.work_location_type")
    private_street = field_employee(fields.Char, 'private_street', string="Private Street", user_writeable=True)
    private_street2 = field_employee(fields.Char, 'private_street2', string="Private Street2", user_writeable=True)
    private_city = field_employee(fields.Char, 'private_city', string="Private City", user_writeable=True)
    private_state_id = field_employee(fields.Many2one, 'private_state_id', string="Private State", user_writeable=True,
        comodel_name='res.country.state',
        domain="[('country_id', '=?', private_country_id)]")
    private_zip = field_employee(fields.Char, 'private_zip', string="Private Zip", user_writeable=True)
    private_country_id = field_employee(fields.Many2one, 'private_country_id', comodel_name='res.country', string="Private Country", user_writeable=True)
    private_phone = field_employee(fields.Char, 'private_phone', user_writeable=True)
    private_email = field_employee(fields.Char, 'private_email', user_writeable=True)
    km_home_work = field_employee(fields.Integer, 'km_home_work', user_writeable=True)
    # res.users already have a field bank_account_id and country_id from the res.partner inheritance: don't redefine them
    # This field no longer appears to be in use. To avoid breaking anything it must only be removed after the freeze of v19.
    employee_bank_account_ids = field_employee(fields.Many2many, 'bank_account_ids', comodel_name='res.partner.bank', string="Employee's Bank Accounts", user_writeable=True, field_name='employee_bank_account_ids')
    emergency_contact = field_employee(fields.Char, 'emergency_contact', user_writeable=True)
    emergency_phone = field_employee(fields.Char, 'emergency_phone', user_writeable=True)
    visa_expire = field_employee(fields.Date, 'visa_expire', user_writeable=True)
    additional_note = field_employee(fields.Text, 'additional_note', user_writeable=True)
    barcode = field_employee(fields.Char, 'barcode', user_writeable=True)
    pin = field_employee(fields.Char, 'pin', user_writeable=True)
    employee_count = fields.Integer(compute='_compute_employee_count')
    employee_resource_calendar_id = fields.Many2one(related='employee_id.resource_calendar_id', string="Employee's Working Hours", readonly=True)
    bank_account_ids = field_employee(fields.Many2many, 'bank_account_ids', comodel_name='res.partner.bank')

    create_employee = fields.Boolean(store=False, default=False, copy=False, string="Technical field, whether to create an employee")
    create_employee_id = fields.Many2one('hr.employee', store=False, copy=False, string="Technical field, bind user to this employee on create")

    is_system = fields.Boolean(compute="_compute_is_system")
    is_hr_user = fields.Boolean(compute='_compute_is_hr_user')

    @api.depends_context('uid')
    def _compute_is_system(self):
        self.is_system = self.env.user._is_system()

    @api.depends_context('uid')
    def _compute_is_hr_user(self):
        is_hr_user = self.env.user.has_group('hr.group_hr_user')
        self.is_hr_user = is_hr_user

    @api.depends('employee_ids')
    def _compute_employee_count(self):
        for user in self.with_context(active_test=False):
            user.employee_count = len(user.employee_ids)

    @api.onchange("private_state_id")
    def _onchange_private_state_id(self):
        if self.private_state_id:
            self.private_country_id = self.private_state_id.country_id

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
        if employee.version_id.hr_responsible_id:
            return (
                _("You are receiving this message because you are the HR Responsible of this employee."),
                employee.version_id.hr_responsible_id.partner_id.ids,
            )
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
            if field_name in vals
            if callable(field.compute) and hasattr(field.compute, 'is_field_employee')
        }

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
                with_image.write(employee_values)
            else:
                employees = self.env['hr.employee'].sudo().search(employee_domain)
                if employees:
                    employees.write(employee_values)
        return result

    @api.model
    def action_get(self):
        if self.env.user.employee_id:
            action = self.env['ir.actions.act_window']._for_xml_id('hr.res_users_action_my')
            groups = {
                group_xml_id[0]: True
                for group_xml_id in self.env.user.all_group_ids._get_external_ids().values()
                if group_xml_id
            }
            action_context = ast.literal_eval(action['context']) if action['context'] else {}
            action_context.update(groups)
            action['context'] = str(action_context)
            return action
        return super().action_get()

    @api.depends('employee_ids')
    @api.depends_context('company', 'uid')
    def _compute_company_employee(self):
        Employee = self.env['hr.employee']
        if self == self.env.user:
            Employee = Employee.sudo()
        employee_per_user = {
            employee.user_id: employee
            for employee in Employee.search([('user_id', 'in', self.ids), ('company_id', '=', self.env.company.id)])
        }
        for user in self:
            user.employee_id = employee_per_user.get(user)

    def _search_company_employee(self, operator, value):
        # Equivalent to `[('employee_ids', operator, value)]`,
        # but we inline the ids directly to simplify final queries and improve performance,
        # as it's part of a few ir.rules.
        # If we're going to inject too many `ids`, we fall back on the default behavior
        # to avoid a performance regression.
        IN_MAX = 10_000
        # HACK: search directly on public ids to avoid optimization on employee
        # where we may not have access to all fields.
        employee_field = 'employee_ids' if self.env['hr.employee'].has_access('read') else 'employee_public_ids'
        domain = Domain(employee_field, operator, value)
        user_ids = self.env['res.users'].with_context(active_test=False)._search(domain, limit=IN_MAX).get_result_ids()
        if len(user_ids) < IN_MAX:
            return Domain('id', 'in', user_ids)

        return domain

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
