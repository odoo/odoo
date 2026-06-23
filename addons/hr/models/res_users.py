# Part of Odoo. See LICENSE file for full copyright and licensing details.

import ast

from markupsafe import Markup

from odoo import _, api, fields, models
from odoo.exceptions import AccessError
from odoo.fields import Domain
from odoo.tools.misc import clean_context
from odoo.addons.mail.tools.discuss import Store

from .hr_employee_location import DAYS


def related_employee_field(name: str, *, field_name: str | None = None, string: str = '__default__'):
    """Simulating a related field "employee_id.{name}".

    Current user is read and updated with `sudo()`. Otherwise, behaves as a
    simple related field.

    :param field_name: provide if you name your field in some other way than
        on the employee model
    :param string: field label override
    """
    # simulating a related field which bypasses access only for the current user
    if field_name is None:
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
        user_writeable = getattr(self._fields[field_name], 'user_writeable', False)
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
        if Employee.has_access('read') and Employee.has_field_access(Employee._fields[name], 'read'):
            return Domain('employee_id', 'any', subdomain)
        else:
            user = self.env.user.employee_id.filtered_domain(subdomain).user_id
            return Domain('id', 'in', user.ids)

    # mark the compute function for identification later
    compute_employee_field.employee_field_name = name
    return {
        'string': string,
        'compute': compute_employee_field,
        'inverse': inverse_employee_field,
        'search': search_employee_field,
         # make it not shareable since we update the field in _post_model_setup__
        '_shareable': False,
    }


class ResUsers(models.Model):
    _inherit = 'res.users'

    def _employee_ids_domain(self):
        # employee_ids is considered a safe field and as such will be fetched as sudo.
        # So try to enforce the security rules on the field to make sure we do not load employees outside of active companies
        return [('company_id', 'in', self.env.companies.ids)]

    def _post_model_setup__(self):  # noqa: PLW3201
        for field in self._fields.values():
            if callable(field.compute) and hasattr(field.compute, 'employee_field_name'):
                related_field = self.env.registry['hr.employee']._fields[field.compute.employee_field_name]
                if field.string == '__default__':
                    field.string = related_field.string
                if field.help is None:
                    field.help = related_field.help

        return super()._post_model_setup__()

    # note: a user can only be linked to one employee per company (see sql constraint in `hr.employee`)
    employee_ids = fields.One2many('hr.employee', 'user_id', string='Related employee', domain=_employee_ids_domain)
    all_employee_ids = fields.One2many("hr.employee", "user_id", string="Related employees from all companies")
    employee_public_ids = fields.One2many('hr.employee.public', 'user_id', string='Related employee (public)', domain=_employee_ids_domain, readonly=True)
    employee_id = fields.Many2one('hr.employee', string="Company employee",
        compute='_compute_company_employee', search='_search_company_employee', readonly=True)
    department_id = fields.Many2one(related='employee_id.department_id', string='Department')

    job_title = fields.Char(**related_employee_field('job_title'), user_writeable=True)
    work_phone = fields.Char(**related_employee_field('work_phone'), user_writeable=True)
    mobile_phone = fields.Char(**related_employee_field('mobile_phone'), user_writeable=True)
    work_email = fields.Char(**related_employee_field('work_email'), user_writeable=True)
    category_ids = fields.Many2many('hr.employee.category', **related_employee_field('category_ids', string="Employee Tags"), user_writeable=True)
    work_contact_id = fields.Many2one('res.partner', **related_employee_field('work_contact_id'))
    work_location_id = fields.Many2one('hr.work.location', **related_employee_field('work_location_id'), user_writeable=True)
    work_location_name = fields.Char(related="employee_id.work_location_name")
    work_location_type = fields.Selection(related="employee_id.work_location_type")
    private_street = fields.Char(**related_employee_field('private_street'), user_writeable=True)
    private_street2 = fields.Char(**related_employee_field('private_street2'), user_writeable=True)
    private_city = fields.Char(**related_employee_field('private_city'), user_writeable=True)
    private_state_id = fields.Many2one(
        'res.country.state',
        domain="[('country_id', '=?', private_country_id)]",
        **related_employee_field('private_state_id'),
        user_writeable=True,
    )
    private_zip = fields.Char(**related_employee_field('private_zip'), user_writeable=True)
    private_country_id = fields.Many2one('res.country', **related_employee_field('private_country_id'), user_writeable=True)
    private_phone = fields.Char(**related_employee_field('private_phone'), user_writeable=True)
    private_email = fields.Char(**related_employee_field('private_email'), user_writeable=True)
    km_home_work = fields.Integer(**related_employee_field('km_home_work'), user_writeable=True)
    # res.users already have a field bank_account_id and country_id from the res.partner inheritance: don't redefine them
    # This field no longer appears to be in use. To avoid breaking anything it must only be removed after the freeze of v19.
    employee_bank_account_ids = fields.Many2many(
        'res.partner.bank',
        **related_employee_field('bank_account_ids', field_name='employee_bank_account_ids', string="Employee's Bank Accounts"),
        user_writeable=True,
    )
    emergency_contact = fields.Char(**related_employee_field('emergency_contact'), user_writeable=True)
    emergency_phone = fields.Char(**related_employee_field('emergency_phone'), user_writeable=True)
    visa_expire = fields.Date(**related_employee_field('visa_expire'), user_writeable=True)
    additional_note = fields.Text(**related_employee_field('additional_note'), user_writeable=True)
    barcode = fields.Char(**related_employee_field('barcode'), user_writeable=True)
    pin = fields.Char(**related_employee_field('pin'), user_writeable=True)
    employee_count = fields.Integer(compute='_compute_employee_count')
    employee_resource_calendar_id = fields.Many2one(related='employee_id.resource_calendar_id', string="Employee's Working Hours", readonly=True)
    bank_account_ids = fields.Many2many('res.partner.bank', **related_employee_field('bank_account_ids'))
    marital = fields.Selection(
        selection=lambda self: self.env["hr.employee"]._fields["marital"]._description_selection(self.env),
        **related_employee_field('marital'),
        user_writeable=True,
    )
    spouse_complete_name = fields.Char(**related_employee_field('spouse_complete_name'), user_writeable=True)
    spouse_birthdate = fields.Date(**related_employee_field('spouse_birthdate'), user_writeable=True)
    children = fields.Integer(**related_employee_field('children'), user_writeable=True)
    legal_name = fields.Char(
        help="The employee's official name as per government-issued or legal documents.",
        **related_employee_field('legal_name'),
        user_writeable=True,
    )
    birthday = fields.Date(**related_employee_field('birthday'), user_writeable=True)
    birthday_public_display = fields.Boolean(**related_employee_field('birthday_public_display'), user_writeable=True)
    place_of_birth = fields.Char(**related_employee_field('place_of_birth'), user_writeable=True)
    country_of_birth = fields.Many2one('res.country', **related_employee_field('country_of_birth'), user_writeable=True)
    sex = fields.Selection(
        selection=lambda self: self.env["hr.employee"]._fields["sex"]._description_selection(self.env),
        help="This is the legal sex as recognized by the state, used for official and statutory purposes.",
        **related_employee_field('sex'),
        user_writeable=True,
    )

    create_employee = fields.Boolean(store=False, default=False, copy=False, string="Technical field, whether to create an employee")
    create_employee_id = fields.Many2one('hr.employee', store=False, copy=False, string="Technical field, bind user to this employee on create")

    is_system = fields.Boolean(compute="_compute_is_system")
    is_hr_user = fields.Boolean(compute='_compute_is_hr_user')

    monday_location_id = fields.Many2one('hr.work.location', **related_employee_field('monday_location_id', string='Mondays'), user_writeable=True)
    tuesday_location_id = fields.Many2one('hr.work.location', **related_employee_field('tuesday_location_id', string='Tuesdays'), user_writeable=True)
    wednesday_location_id = fields.Many2one('hr.work.location', **related_employee_field('wednesday_location_id', string='Wednesdays'), user_writeable=True)
    thursday_location_id = fields.Many2one('hr.work.location', **related_employee_field('thursday_location_id', string='Thursdays'), user_writeable=True)
    friday_location_id = fields.Many2one('hr.work.location', **related_employee_field('friday_location_id', string='Fridays'), user_writeable=True)
    saturday_location_id = fields.Many2one('hr.work.location', **related_employee_field('saturday_location_id', string='Saturdays'), user_writeable=True)
    sunday_location_id = fields.Many2one('hr.work.location', **related_employee_field('sunday_location_id', string='Sundays'), user_writeable=True)

    # Redefine role to add light user -> that will just limit the groups compared to a user.
    role = fields.Selection([('light', 'Light User'), ('group_user', 'User'), ('group_system', 'Administrator')],
                                         compute='_compute_role', inverse='_inverse_user', readonly=False, string="Role")

    def _compute_role(self):
        # TODO DBE: not tested, just writing the idea.
        super()._compute_role()
        minimal_light_user_groups = self.minimal_light_user_groups()
        group_user = self.env.ref('base.group_user')
        group_no_one = self.env.ref('base.group_no_one')
        for user in self:
            # If what's left is more that user_lite groups -> cannot be lite user.
            user_groups = user.all_group_ids._origin - group_user - group_user.implied_ids - group_no_one
            if user_groups == minimal_light_user_groups:
                user.role = 'light'

    def _inverse_role(self):
        minimal_light_user_groups = self.minimal_light_user_groups()
        for user in self:
            if user.role == 'light':
                user.groups_ids = minimal_light_user_groups

    def _get_minimal_light_user_groups(self):
        """ List of all groups of the light user. Can be overriden by other modules to exetend the group list. """
        return [
            # Bla bla bla
        ]

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
        return ['name', 'email', 'image_1920', 'tz'] + DAYS

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
            if callable(field.compute) and hasattr(field.compute, 'employee_field_name')
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
        employee_per_user = dict(self.env['hr.employee'].sudo()._read_group(
            domain=[('user_id', 'in', self.ids), ('company_id', '=', self.env.company.id)],
            groupby=['user_id'],
            aggregates=['id:recordset'],
        ))

        for user in self:
            employee = employee_per_user.get(user, self.env['hr.employee'])
            if user != self.env.user and not self.env.su:
                # since the search is done in sudo to avoid cache issues, apply access rules
                employee = employee.filtered(lambda e: e.has_access('read'))
            user.employee_id = employee

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
        return self.env['hr.employee'].create(dict(
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

    def get_record_default_action(self, access_uid=None):
        """ Override this method in order to redirect many2one towards the full user form view
        incase the user is ERP manager and the request coming from employee form."""

        res = super().get_record_default_action(access_uid=access_uid)
        user = self.env.user
        if access_uid:
            user = self.env['res.users'].browse(access_uid).sudo()

        if self.env.context.get('default_create_employee_id') and user.has_group('base.group_erp_manager'):
            res['views'] = [(self.env.ref('base.view_users_form').id, 'form')]

        return res

    def _store_avatar_card_fields(self, res: Store.FieldList):
        super()._store_avatar_card_fields(res)
        if res.is_for_internal_users():
            # sudo: res.users - internal users can access employee information of accessible user
            res.many("employee_ids", "_store_avatar_card_fields", sudo=True)

    def _store_im_status_fields(self, res: Store.FieldList):
        super()._store_im_status_fields(res)
        # sudo: res.users - internal users can access employee information for the IM status
        res.many("all_employee_ids", "_store_im_status_fields", sudo=True)
