# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import timedelta
from pytz import timezone, UTC

from odoo import api, fields, models, tools
from odoo.tools import format_time


class HrEmployeePublic(models.Model):
    _name = 'hr.employee.public'
    _description = 'Public Employee'
    _order = 'name'
    _auto = False
    _log_access = True  # Include magic fields

    # Fields coming from hr.employee
    create_date = fields.Datetime(readonly=True)
    name = fields.Char(readonly=True)
    active = fields.Boolean(readonly=True)
    department_id = fields.Many2one('hr.department', readonly=True)
    member_of_department = fields.Boolean(compute='_compute_member_of_department', search='_search_part_of_department')
    job_id = fields.Many2one('hr.job', readonly=True)
    job_title = fields.Char(related='employee_id.job_title')
    company_id = fields.Many2one('res.company', readonly=True)
    address_id = fields.Many2one('res.partner', readonly=True)
    mobile_phone = fields.Char(readonly=True)
    work_phone = fields.Char(readonly=True)
    work_email = fields.Char(readonly=True)
    share = fields.Boolean(related='employee_id.share')
    phone = fields.Char(related='employee_id.phone')
    im_status = fields.Char(related='employee_id.im_status')
    email = fields.Char(related='employee_id.email')
    work_contact_id = fields.Many2one('res.partner', readonly=True)
    work_location_id = fields.Many2one('hr.work.location', readonly=True)
    work_location_name = fields.Char(compute="_compute_work_location_name")
    work_location_type = fields.Selection(related='employee_id.work_location_type')
    user_id = fields.Many2one('res.users', readonly=True)
    resource_id = fields.Many2one('resource.resource', readonly=True)
    tz = fields.Selection(related='resource_id.tz')
    color = fields.Integer(readonly=True)
    hr_presence_state = fields.Selection([
        ('present', 'Present'),
        ('absent', 'Absent'),
        ('archive', 'Archived'),
        ('out_of_working_hour', 'Out of Working hours')], compute='_compute_presence_state', default='out_of_working_hour')
    hr_icon_display = fields.Selection(
        selection='_get_selection_hr_icon_display',
        compute='_compute_presence_icon')
    show_hr_icon_display = fields.Boolean(compute='_compute_presence_icon')
    last_activity = fields.Date(compute="_compute_last_activity")
    last_activity_time = fields.Char(compute="_compute_last_activity")
    resource_calendar_id = fields.Many2one('resource.calendar', readonly=True)
    country_code = fields.Char(compute='_compute_country_code')

    # Manager-only fields
    is_manager = fields.Boolean(compute='_compute_is_manager')

    employee_id = fields.Many2one('hr.employee', 'Employee', compute="_compute_employee_id", search="_search_employee_id", compute_sudo=True)
    # hr.employee.public specific fields
    child_ids = fields.One2many('hr.employee.public', 'parent_id', string='Direct subordinates', readonly=True)
    image_1920 = fields.Image("Image", related='employee_id.image_1920', compute_sudo=True)
    image_1024 = fields.Image("Image 1024", related='employee_id.image_1024', compute_sudo=True)
    image_512 = fields.Image("Image 512", related='employee_id.image_512', compute_sudo=True)
    image_256 = fields.Image("Image 256", related='employee_id.image_256', compute_sudo=True)
    image_128 = fields.Image("Image 128", related='employee_id.image_128', compute_sudo=True)
    avatar_1920 = fields.Image("Avatar", related='employee_id.avatar_1920', compute_sudo=True)
    avatar_1024 = fields.Image("Avatar 1024", related='employee_id.avatar_1024', compute_sudo=True)
    avatar_512 = fields.Image("Avatar 512", related='employee_id.avatar_512', compute_sudo=True)
    avatar_256 = fields.Image("Avatar 256", related='employee_id.avatar_256', compute_sudo=True)
    avatar_128 = fields.Image("Avatar 128", related='employee_id.avatar_128', compute_sudo=True)
    parent_id = fields.Many2one('hr.employee.public', 'Manager', readonly=True)
    coach_id = fields.Many2one('hr.employee.public', 'Coach', readonly=True)
    user_partner_id = fields.Many2one(related='user_id.partner_id', related_sudo=False, string="User's partner")
    birthday_public_display_string = fields.Char("Public Date of Birth", related='employee_id.birthday_public_display_string')

    newly_hired = fields.Boolean('Newly Hired', compute='_compute_newly_hired', search='_search_newly_hired')

    def _get_selection_hr_icon_display(self):
        return self.env['hr.employee']._fields['hr_icon_display']._description_selection(self.env)

    def _compute_from_employee(self, field_names):
        if isinstance(field_names, str):
            field_names = [field_names]
        employees_sudo = self.sudo().env['hr.employee'].browse(self.ids)
        employee_per_id = {emp.id: emp for emp in employees_sudo}
        for public_employee in self:
            employee = employee_per_id[public_employee.id]
            for field_name in field_names:
                public_employee[field_name] = employee[field_name]

    @api.depends('user_id')
    def _compute_last_activity(self):
        for employee in self:
            tz = employee.tz
            # sudo: res.users - can access presence of accessible user
            if last_presence := employee.user_id.sudo().presence_ids.last_presence:
                last_activity_datetime = last_presence.replace(tzinfo=UTC).astimezone(timezone(tz)).replace(tzinfo=None)
                employee.last_activity = last_activity_datetime.date()
                if employee.last_activity == fields.Date.today():
                    employee.last_activity_time = format_time(self.env, last_presence, time_format='short')
                else:
                    employee.last_activity_time = False
            else:
                employee.last_activity = False
                employee.last_activity_time = False

    def _compute_country_code(self):
        self._compute_from_employee('country_code')

    @api.depends_context('uid')
    @api.depends('parent_id')
    def _compute_is_manager(self):
        all_reports = self.env['hr.employee.public'].search([('id', 'child_of', self.env.user.employee_id.id)]).ids
        for employee in self:
            employee.is_manager = employee.id in all_reports

    def _compute_presence_state(self):
        self._compute_from_employee('hr_presence_state')

    def _compute_presence_icon(self):
        self._compute_from_employee('hr_icon_display')
        self._compute_from_employee('show_hr_icon_display')

    def _compute_member_of_department(self):
        self._compute_from_employee('member_of_department')

    def _compute_work_location_name(self):
        self._compute_from_employee('work_location_name')

    def _get_manager_only_fields(self):
        return []

    def _search_part_of_department(self, operator, value):
        if operator != 'in':
            return NotImplemented

        user_employee = self._get_valid_employee_for_user()
        if not user_employee.department_id:
            return [('id', 'in', user_employee.ids)]
        return [('department_id', 'child_of', user_employee.department_id.ids)]

    def _get_valid_employee_for_user(self):
        user = self.env.user
        # retrieve the employee of the current active company for the user
        employee = user.employee_id
        if not employee:
            # search for all employees as superadmin to not get blocked by multi-company rules
            user_employees = user.employee_id.sudo().search([
                ('user_id', '=', user.id)
            ])
            # the default company employee is most likely the correct one, but fallback to the first if not available
            employee = user_employees.filtered(lambda r: r.company_id == user.company_id) or user_employees[:1]
        return employee

    @api.depends_context('uid')
    def _compute_manager_only_fields(self):
        manager_fields = self._get_manager_only_fields()
        for employee in self:
            if employee.is_manager:
                employee_sudo = employee.employee_id.sudo()
                for f in manager_fields:
                    employee[f] = employee_sudo[f]
            else:
                for f in manager_fields:
                    employee[f] = False

    def _search_employee_id(self, operator, value):
        return [('id', operator, value)]

    def _compute_employee_id(self):
        for employee in self:
            employee.employee_id = self.env['hr.employee'].browse(employee.id)

    def _compute_newly_hired(self):
        self._compute_from_employee('newly_hired')

    def _search_newly_hired(self, operator, value):
        if operator not in ('in', 'not in'):
            return NotImplemented
        new_hire_field = self.env['hr.employee']._get_new_hire_field()
        new_hires = self.env['hr.employee'].sudo().search([
            (new_hire_field, '>', fields.Datetime.now() - timedelta(days=90))
        ])
        return [('id', operator, new_hires.ids)]

    @api.model
    def _get_fields(self):
        return 'e.id AS id,e.name AS name,e.active AS active,' + ','.join(
            ('v.%s' if name in self.env['hr.version']._fields and self.env['hr.version']._fields[name].store else 'e.%s') % name
            for name, field in self._fields.items()
            if field.store and field.type not in ['many2many', 'one2many'] and name not in ['id', 'name', 'active'])

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute("""CREATE or REPLACE VIEW %s as (
            SELECT
                %s
            FROM hr_employee e
            JOIN hr_version v
              ON v.id = e.current_version_id
        )""" % (self._table, self._get_fields()))

    def get_avatar_card_data(self, fields):
        return self.read(fields)
