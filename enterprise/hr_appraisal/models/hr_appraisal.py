# Part of Odoo. See LICENSE file for full copyright and licensing details.

from dateutil.relativedelta import relativedelta
import datetime
import logging
import pytz

from odoo import api, fields, models, _

from odoo.exceptions import UserError
from odoo.tools import convert
from odoo.tools.misc import format_date

_logger = logging.getLogger(__name__)


class HrAppraisal(models.Model):
    _name = "hr.appraisal"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = "Employee Appraisal"
    _order = 'state desc, date_close, id desc'
    _rec_name = 'employee_id'
    _mail_post_access = 'read'

    def _get_default_employee(self):
        if self.env.context.get('active_model') in ('hr.employee', 'hr.employee.public') and 'active_id' in self.env.context:
            return self.env.context.get('active_id')
        elif self.env.context.get('active_model') == 'res.users' and 'active_id' in self.env.context:
            return self.env['res.users'].browse(self.env.context['active_id']).employee_id
        if not self.env.user.has_group('hr_appraisal.group_hr_appraisal_user'):
            return self.env.user.employee_id

    active = fields.Boolean(default=True)
    employee_id = fields.Many2one(
        'hr.employee', required=True, string='Employee', index=True,
        default=_get_default_employee, ondelete='cascade')
    employee_user_id = fields.Many2one('res.users', string="Employee User", related='employee_id.user_id')
    company_id = fields.Many2one('res.company', related='employee_id.company_id', store=True)
    department_id = fields.Many2one(
        'hr.department', compute='_compute_department_id', string='Department', store=True)
    job_id = fields.Many2one('hr.job', related="employee_id.job_id")
    image_128 = fields.Image(related='employee_id.image_128')
    image_1920 = fields.Image(related='employee_id.image_1920')
    avatar_128 = fields.Image(related='employee_id.avatar_128')
    avatar_1920 = fields.Image(related='employee_id.avatar_1920')
    last_appraisal_id = fields.Many2one('hr.appraisal', related='employee_id.last_appraisal_id')
    last_appraisal_date = fields.Date(related='employee_id.last_appraisal_date')
    employee_appraisal_count = fields.Integer(related='employee_id.appraisal_count')
    uncomplete_goals_count = fields.Integer(related='employee_id.uncomplete_goals_count')
    appraisal_template_id = fields.Many2one('hr.appraisal.template', string="Appraisal Template", compute="_compute_appraisal_template", check_company=True, store=True)
    employee_feedback_template = fields.Html(compute='_compute_feedback_templates', translate=True)
    manager_feedback_template = fields.Html(compute='_compute_feedback_templates', translate=True)

    date_close = fields.Date(
        string='Appraisal Date', help='Closing date of the current appraisal', required=True, index=True,
        default=lambda self: datetime.date.today() + relativedelta(months=+1))
    next_appraisal_date = fields.Date(related="employee_id.next_appraisal_date",
        help='Date where the new appraisal will be automatically created', readonly=False)
    previous_appraisal_date = fields.Date(
        string='Previous Appraisal Date', help='Closing date of the previous appraisal', compute="_compute_previous_appraisal_date", compute_sudo=True)
    state = fields.Selection(
        [('new', 'To Confirm'),
         ('pending', 'Confirmed'),
         ('done', 'Done'),
         ('cancel', "Cancelled")],
        string='Status', tracking=True, required=True, copy=False,
        default='new', index=True, group_expand=True)
    manager_ids = fields.Many2many(
        'hr.employee', 'appraisal_manager_rel', 'hr_appraisal_id',
        context={'active_test': False},
        domain="[('id', '!=', employee_id), ('active', '=', 'True'), '|', ('company_id', '=', False), ('company_id', 'in', allowed_company_ids)]")
    manager_user_ids = fields.Many2many('res.users', string="Manager Users", compute='_compute_user_manager_rights')
    meeting_ids = fields.Many2many('calendar.event', string='Meetings')
    meeting_count_display = fields.Char(string='Meeting Count', compute='_compute_meeting_count')
    date_final_interview = fields.Date(string="Final Interview", compute='_compute_final_interview')
    is_manager = fields.Boolean(compute='_compute_user_manager_rights')
    employee_autocomplete_ids = fields.Many2many('hr.employee', compute='_compute_user_manager_rights')
    waiting_feedback = fields.Boolean(
        string="Waiting Feedback from Employee/Managers", compute='_compute_waiting_feedback')
    employee_feedback = fields.Html(compute='_compute_employee_feedback', store=True, readonly=False, groups="hr_appraisal.group_hr_appraisal_user")
    accessible_employee_feedback = fields.Html(compute='_compute_accessible_employee_feedback', inverse="_inverse_accessible_employee_feedback")
    show_employee_feedback_full = fields.Boolean(compute='_compute_show_employee_feedback_full')
    manager_feedback = fields.Html(compute='_compute_manager_feedback', store=True, readonly=False, groups="hr_appraisal.group_hr_appraisal_user")
    accessible_manager_feedback = fields.Html(compute='_compute_accessible_manager_feedback', inverse="_inverse_accessible_manager_feedback")
    show_manager_feedback_full = fields.Boolean(compute='_compute_show_manager_feedback_full')
    employee_feedback_published = fields.Boolean(string="Employee Feedback Published", default=True, tracking=True)
    manager_feedback_published = fields.Boolean(string="Manager Feedback Published", default=True, tracking=True)
    can_see_employee_publish = fields.Boolean(compute='_compute_buttons_display')
    can_see_manager_publish = fields.Boolean(compute='_compute_buttons_display')
    assessment_note = fields.Many2one('hr.appraisal.note', string="Final Rating", help="This field is not visible to the Employee.", domain="[('company_id', '=', company_id)]")
    note = fields.Html(string="Private Note")
    appraisal_plan_posted = fields.Boolean()
    appraisal_properties = fields.Properties("Properties", definition="department_id.appraisal_properties_definition", precompute=False)
    duplicate_appraisal_id = fields.Many2one('hr.appraisal', compute='_compute_duplicate_appraisal_id', export_string_translation=False, store=False)

    @api.depends('employee_id', 'manager_ids')
    def _compute_duplicate_appraisal_id(self):
        """
        Note: We only care for duplicate_appraisal_id when we create a
        new appraisal. This field is currently only used in form view
        and for performance reasons it should rather stay that way.
        """
        ongoing_appraisals = self.search([
            ('state', 'in', ['new', 'pending']),
            ('employee_id', 'in', self.employee_id.ids),
            ('manager_ids', 'in', self.manager_ids.ids),
        ], order='date_close')
        self.duplicate_appraisal_id = False
        for appraisal in self:
            if not isinstance(appraisal.id, models.NewId)\
                    or appraisal.state != 'new':
                continue
            for ongoing_appraisal in ongoing_appraisals:
                if ongoing_appraisals.manager_ids == appraisal.manager_ids._origin\
                    and ongoing_appraisal.employee_id == appraisal.employee_id\
                        and ongoing_appraisal.id != appraisal.id:
                    appraisal.duplicate_appraisal_id = ongoing_appraisal.id
                    break

    @api.depends('employee_id')
    def _compute_department_id(self):
        for appraisal in self:
            if appraisal.employee_id:
                appraisal.department_id = appraisal.employee_id.department_id
            else:
                appraisal.department_id = False

    @api.depends('employee_id')
    def _compute_previous_appraisal_date(self):
        appraisals = self.env['hr.appraisal'].sudo().search([
            ('employee_id', 'in', self.employee_id.ids),
            ('state', '=', 'done'),
            ], order='date_close desc')
        for appraisal in self:
            appraisal.previous_appraisal_date = False
            previous_appraisals = appraisals.filtered_domain([('employee_id', '=', appraisal.employee_id.id), ('date_close', '<', appraisal.date_close)])
            if appraisal.id:
                previous_appraisals = previous_appraisals.filtered_domain([('id', '!=', appraisal.id)])
            if previous_appraisals:
                last_appraisal = previous_appraisals[0]
                appraisal.previous_appraisal_date = last_appraisal.date_close

    @api.depends_context('uid')
    @api.depends('employee_id', 'manager_ids')
    def _compute_buttons_display(self):
        new_appraisals = self.filtered(lambda a: a.state == 'new')
        new_appraisals.update({
            'can_see_employee_publish': False,
            'can_see_manager_publish': False,
        })
        user_employees = self.env.user.employee_ids
        is_manager = self.env.user.has_group('hr_appraisal.group_hr_appraisal_user')
        for appraisal in self:
            user_employee_in_appraisal_manager = bool(set(user_employees.ids) & set(appraisal.manager_ids.ids))
            # Appraisal manager can edit feedback in draft state
            appraisal.can_see_employee_publish = appraisal.employee_id in user_employees or \
                (user_employee_in_appraisal_manager and appraisal.state == 'new')
            appraisal.can_see_manager_publish = user_employee_in_appraisal_manager
        for appraisal in self - new_appraisals:
            if is_manager and not appraisal.can_see_employee_publish and not appraisal.can_see_manager_publish:
                appraisal.can_see_employee_publish, appraisal.can_see_manager_publish = True, True

    @api.depends_context('uid')
    @api.depends('manager_ids', 'employee_id', 'employee_id.parent_id')
    def _compute_user_manager_rights(self):
        self.employee_autocomplete_ids = self.env.user.get_employee_autocomplete_ids()
        for appraisal in self:
            appraisal.manager_user_ids = appraisal.manager_ids.user_id
            appraisal.is_manager =\
                self.env.user.has_group('hr_appraisal.group_hr_appraisal_user')\
                or self.env.user.employee_ids in (appraisal.manager_ids | appraisal.employee_id.parent_id)

    @api.depends_context('uid')
    @api.depends('employee_id', 'employee_feedback_published')
    def _compute_show_employee_feedback_full(self):
        for appraisal in self:
            is_appraisee = appraisal.employee_id.user_id == self.env.user
            appraisal.show_employee_feedback_full = is_appraisee and not appraisal.employee_feedback_published

    @api.depends_context('uid')
    @api.depends('manager_ids', 'manager_feedback_published')
    def _compute_show_manager_feedback_full(self):
        for appraisal in self:
            is_appraiser = self.env.user in appraisal.manager_ids.user_id
            appraisal.show_manager_feedback_full = is_appraiser and not appraisal.manager_feedback_published

    @api.depends('department_id', 'appraisal_template_id')
    def _compute_employee_feedback(self):
        for appraisal in self.filtered(lambda a: a.state in ['new', 'pending']):
            employee_template = appraisal._get_appraisal_template('employee')
            if appraisal.state == 'new':
                appraisal.employee_feedback = employee_template
            else:
                appraisal.employee_feedback = appraisal.employee_feedback or employee_template

    @api.depends('department_id', 'appraisal_template_id')
    def _compute_manager_feedback(self):
        for appraisal in self.filtered(lambda a: a.state in ['new', 'pending']):
            manager_template = appraisal._get_appraisal_template('manager')
            if appraisal.state == 'new':
                appraisal.manager_feedback = manager_template
            else:
                appraisal.manager_feedback = appraisal.manager_feedback or manager_template

    @api.depends('department_id', 'company_id', 'appraisal_template_id')
    def _compute_feedback_templates(self):
        for appraisal in self:
            appraisal.employee_feedback_template = appraisal._get_appraisal_template('employee')
            appraisal.manager_feedback_template = appraisal._get_appraisal_template('manager')

    @api.depends('department_id', 'company_id')
    def _compute_appraisal_template(self):
        for appraisal in self:
            appraisal.appraisal_template_id = appraisal.appraisal_template_id or \
                appraisal.department_id.custom_appraisal_template_id or \
                appraisal.company_id.appraisal_template_id

    @api.depends('employee_feedback_published', 'manager_feedback_published')
    def _compute_waiting_feedback(self):
        for appraisal in self:
            appraisal.waiting_feedback = not appraisal.employee_feedback_published or not appraisal.manager_feedback_published

    @api.depends_context('uid')
    @api.depends('meeting_ids.start')
    def _compute_final_interview(self):
        today = fields.Date.today()
        user_tz = self.env.user.tz or self.env.context.get('tz')
        user_pytz = pytz.timezone(user_tz) if user_tz else pytz.utc
        with_meeting = self.filtered('meeting_ids')
        (self - with_meeting).date_final_interview = False
        for appraisal in with_meeting:
            all_dates = appraisal.meeting_ids.mapped('start')
            min_date, max_date = min(all_dates), max(all_dates)
            if min_date.date() >= today:
                appraisal.date_final_interview = min_date.astimezone(user_pytz)
            else:
                appraisal.date_final_interview = max_date.astimezone(user_pytz)

    @api.depends_context('lang')
    @api.depends('meeting_ids')
    def _compute_meeting_count(self):
        today = fields.Date.today()
        for appraisal in self:
            count = len(appraisal.meeting_ids)
            if not count:
                appraisal.meeting_count_display = _('No Meeting')
            elif count == 1:
                appraisal.meeting_count_display = _('1 Meeting')
            elif appraisal.date_final_interview >= today:
                appraisal.meeting_count_display = _('Next Meeting')
            else:
                appraisal.meeting_count_display = _('Last Meeting')

    @api.depends('employee_id', 'date_close')
    @api.depends_context('include_date_in_name')
    def _compute_display_name(self):
        if not self.env.context.get('include_date_in_name'):
            return super()._compute_display_name()
        for appraisal in self:
            appraisal.display_name = _(
                "Appraisal for %(employee)s on %(date)s",
                employee=appraisal.employee_id.name, date=appraisal.date_close)

    @api.onchange('employee_id')
    def _onchange_employee_id(self):
        self = self.sudo()  # fields are not on the employee public
        if self.employee_id:
            manager = self.employee_id.parent_id
            self.manager_ids = manager if manager != self.employee_id else False
            # Allow indirect managers to request appraisals for employees
            if self.env.user.employee_id != self.employee_id and not self.env.user.has_group('hr_appraisal.group_hr_appraisal_user'):
                self.manager_ids |= self.env.user.employee_id
            self.department_id = self.employee_id.department_id

    def subscribe_employees(self):
        for appraisal in self:
            partners = appraisal.manager_ids.mapped('related_partner_id') | appraisal.employee_id.related_partner_id
            appraisal.message_subscribe(partner_ids=partners.ids)

    def send_appraisal(self):
        for appraisal in self:
            confirmation_mail_template = appraisal.company_id.appraisal_confirm_mail_template
            mapped_data = {
                **{appraisal.employee_id: confirmation_mail_template},
                **{manager: confirmation_mail_template for manager in appraisal.manager_ids}
            }
            for employee, mail_template in mapped_data.items():
                if not employee.work_email or not self.env.user.email or not mail_template:
                    continue
                ctx = {
                    'employee_to_name': appraisal.employee_id.name,
                    'recipient_users': employee.user_id,
                    'url': '/mail/view?model=%s&res_id=%s' % ('hr.appraisal', appraisal.id),
                }
                mail_template = mail_template.with_context(**ctx)
                subject = mail_template._render_field('subject', appraisal.ids)[appraisal.id]
                body = mail_template._render_field('body_html', appraisal.ids)[appraisal.id]
                # post the message
                mail_values = {
                    'email_from': self.env.user.email_formatted,
                    'author_id': self.env.user.partner_id.id,
                    'model': None,
                    'res_id': None,
                    'subject': subject,
                    'body_html': body,
                    'auto_delete': True,
                    'email_to': employee.work_email
                }
                template_ctx = {
                    'model_description': self.env['ir.model']._get('hr.appraisal').display_name,
                    'message': self.env['mail.message'].sudo().new(dict(body=mail_values['body_html'], record_name=_("Appraisal Request"))),
                    'company': self.env.company,
                    'record': self,
                }
                body = self.env['ir.qweb']._render('mail.mail_notification_light', template_ctx, minimal_qcontext=True, raise_if_not_found=False)
                if body:
                    mail_values['body_html'] = self.env['mail.render.mixin']._replace_local_links(body)
                else:
                    _logger.warning('QWeb template mail.mail_notification_light not found when sending appraisal confirmed mails. Sending without layouting.')

                self.env['mail.mail'].sudo().create(mail_values)

                from_cron = 'from_cron' in self.env.context
                # When cron creates appraisal, it creates specific activities
                # In this case, no need to create activities, not to be repetitive
                if employee.user_id and not from_cron:
                    appraisal.activity_schedule(
                        'mail.mail_activity_data_todo', appraisal.date_close,
                        summary=_('Appraisal Form to Fill'),
                        note=_('Fill appraisal for %s', appraisal.employee_id._get_html_link()),
                        user_id=employee.user_id.id)

    def action_cancel(self):
        self.state = 'cancel'

    @api.model_create_multi
    def create(self, vals_list):
        appraisals = super().create(vals_list)
        appraisals_to_send = self.env['hr.appraisal']
        current_date = datetime.date.today()
        for appraisal, vals in zip(appraisals, vals_list):
            if vals.get('state') and vals['state'] == 'pending':
                appraisals_to_send |= appraisal
            if vals.get('state') and vals['state'] == 'new':
                appraisal.employee_id.sudo().write({
                    'last_appraisal_id': appraisal.id,
                    'last_appraisal_date': current_date,
                })
        appraisals_to_send.send_appraisal()
        appraisals.subscribe_employees()
        return appraisals

    @api.depends('employee_feedback', 'can_see_employee_publish', 'employee_feedback_published')
    def _compute_accessible_employee_feedback(self):
        for appraisal in self:
            if appraisal.can_see_employee_publish or appraisal.employee_feedback_published:
                appraisal.accessible_employee_feedback = appraisal.sudo().employee_feedback
            else:
                appraisal.accessible_employee_feedback = _("Unpublished")

    def _inverse_accessible_employee_feedback(self):
        for appraisal in self:
            if appraisal.can_see_employee_publish:
                appraisal.sudo().employee_feedback = appraisal.accessible_employee_feedback
            else:
                raise UserError(_('The employee feedback cannot be changed by managers.'))

    @api.depends('manager_feedback', 'can_see_manager_publish', 'manager_feedback_published')
    def _compute_accessible_manager_feedback(self):
        for appraisal in self:
            if appraisal.can_see_manager_publish or appraisal.manager_feedback_published:
                appraisal.accessible_manager_feedback = appraisal.sudo().manager_feedback
            else:
                appraisal.accessible_manager_feedback = _("Unpublished")

    def _inverse_accessible_manager_feedback(self):
        for appraisal in self:
            if appraisal.can_see_manager_publish:
                appraisal.sudo().manager_feedback = appraisal.accessible_manager_feedback
            else:
                raise UserError(_('The manager feedback cannot be changed by an employee.'))

    def _get_appraisal_template(self, template):
        self.ensure_one()
        appraisal_template = self.appraisal_template_id or \
            self.department_id.custom_appraisal_template_id or \
            self.company_id.appraisal_template_id
        if not appraisal_template:
            return False
        if template == 'employee':
            return appraisal_template.appraisal_employee_feedback_template
        else:
            return appraisal_template.appraisal_manager_feedback_template

    def _find_previous_appraisals(self):
        result = {}
        all_appraisals = self.env['hr.appraisal'].search([
            ('employee_id', 'in', self.mapped('employee_id').ids),
            ('state', '!=', 'cancel'),
        ], order='employee_id, id desc')
        for appraisal in self:
            previous_appraisals = all_appraisals.filtered(lambda x: x.employee_id == appraisal.employee_id and x.id != appraisal.id and x.create_date < appraisal.create_date)
            if previous_appraisals:
                result[appraisal.id] = previous_appraisals[0]
        return result

    def write(self, vals):
        if 'manager_feedback_published' in vals and not all(a.can_see_manager_publish for a in self):
            raise UserError(_('The "Manager Feedback Published" cannot be changed by an employee.'))

        force_published = self.env['hr.appraisal']
        if vals.get('employee_feedback_published'):
            user_employees = self.env.user.employee_ids
            force_published = self.filtered(lambda a: (a.is_manager) and not (a.employee_feedback_published or a.employee_id in user_employees))
        if vals.get('state') in ['pending', 'done']:
            self.activity_ids.action_feedback()
            not_done_appraisal = self.env['hr.appraisal']
            for appraisal in self:
                appraisal.employee_id.sudo().write({
                    'last_appraisal_id': appraisal.id,
                    'last_appraisal_date': appraisal.date_close,
                })
                if appraisal.state != 'done':
                    not_done_appraisal |= appraisal
            if vals.get('state') == 'pending':
                vals['employee_feedback_published'] = False
                vals['manager_feedback_published'] = False
                not_done_appraisal.send_appraisal()
            else:
                vals['employee_feedback_published'] = True
                vals['manager_feedback_published'] = True
                self._appraisal_plan_post()
                body = _("The appraisal's status has been set to Done by %s", self.env.user.name)
                self.message_notify(
                    body=body,
                    subject=_("Your Appraisal has been completed"),
                    partner_ids=appraisal.message_partner_ids.ids,
                )
                self.message_post(body=body)
        elif vals.get('state') == 'cancel':
            self.meeting_ids.unlink()
            self.activity_unlink(['mail.mail_activity_data_meeting', 'mail.mail_activity_data_todo'])
            previous_appraisals = self._find_previous_appraisals()
            for appraisal in self:
                if appraisal.employee_id and appraisal.employee_id.last_appraisal_id == appraisal:
                    previous_appraisal = previous_appraisals.get(appraisal.id)
                    appraisal.employee_id.sudo().write({
                        'last_appraisal_id': previous_appraisal.id if previous_appraisal else False,
                        'last_appraisal_date': previous_appraisal.date_close if previous_appraisal else False,
                    })
        previous_managers = {}
        if 'manager_ids' in vals:
            previous_managers = {x: y for x, y in self.mapped(lambda a: (a.id, a.manager_ids))}
        result = super(HrAppraisal, self).write(vals)
        if force_published:
            for appraisal in force_published:
                role = _('Manager') if self.env.user.employee_id in appraisal.manager_ids else _('Appraisal Officer')
                appraisal.message_post(body=_('%(user)s decided, as %(role)s, to publish the employee\'s feedback', user=self.env.user.name, role=role))
        if 'manager_ids' in vals:
            self._sync_meeting_attendees(previous_managers)
        return result

    def unlink(self):
        previous_appraisals = self._find_previous_appraisals()
        for appraisal in self:
            # If current appraisal is the last_appraisal_id for the employee we should update last_appraisal_id bfore deleting
            if appraisal.employee_id and appraisal.employee_id.last_appraisal_id == appraisal:
                previous_appraisal = previous_appraisals.get(appraisal.id)
                appraisal.employee_id.sudo().write({
                    'last_appraisal_id': previous_appraisal.id if previous_appraisal else False,
                    'last_appraisal_date': previous_appraisal.date_close if previous_appraisal else False,
                })
        return super(HrAppraisal, self).unlink()

    def _appraisal_plan_post(self):
        odoobot = self.env.ref('base.partner_root')
        dates = self.employee_id.sudo()._upcoming_appraisal_creation_date()
        for appraisal in self:
            # The only ongoing appraisal is the current one
            if not appraisal.appraisal_plan_posted and appraisal.company_id.appraisal_plan and appraisal.employee_id.sudo().ongoing_appraisal_count == 1:
                date = dates[appraisal.employee_id.id]
                formated_date = format_date(self.env, date, date_format="MMM d y")
                body = _('Thanks to your Appraisal Plan, without any new manual Appraisal, the new Appraisal will be automatically created on %s.', formated_date)
                appraisal._message_log(body=body, author_id=odoobot.id)
                appraisal.appraisal_plan_posted = True

    def _generate_activities(self):
        today = fields.Date.today()
        for appraisal in self:
            employee = appraisal.employee_id
            managers = appraisal.manager_ids
            last_appraisal_months = employee.last_appraisal_date and (
                today.year - employee.last_appraisal_date.year)*12 + (today.month - employee.last_appraisal_date.month)
            if employee.user_id:
                # an appraisal has been just created
                if employee.appraisal_count == 1:
                    months = (appraisal.date_close.year - employee.create_date.year) * \
                        12 + (appraisal.date_close.month - employee.create_date.month)
                    note = _("You arrived %s months ago. Your appraisal is created and you can fill it here.", months)
                else:
                    note = _("Your last appraisal was %s months ago. Your appraisal is created and you can fill it here.", last_appraisal_months)
                appraisal.with_context(mail_activity_quick_update=True).activity_schedule(
                    'mail.mail_activity_data_todo', today,
                    summary=_('Appraisal to fill'),
                    note=note, user_id=employee.user_id.id)
                for manager in managers.filtered('user_id'):
                    if employee.appraisal_count == 1:
                        note = _(
                            "The employee %(employee)s arrived %(months)s months ago. The appraisal is created and you can fill it here.",
                            employee=employee._get_html_link(), months=months)
                    else:
                        note = _(
                            "The last appraisal of %(employee)s was %(months)s months ago. The appraisal is created and you can fill it here.",
                            employee=appraisal.employee_id._get_html_link(), months=last_appraisal_months)
                    appraisal.with_context(mail_activity_quick_update=True).activity_schedule(
                        'mail.mail_activity_data_todo', today,
                        summary=_('Appraisal for %s to fill', employee.name),
                        note=note, user_id=manager.user_id.id)

    def _sync_meeting_attendees(self, manager_ids):
        for appraisal in self.filtered('meeting_ids'):
            previous_managers = manager_ids.get(appraisal.id, self.env['hr.employee'])
            to_add = self.manager_ids - previous_managers
            to_del = previous_managers - self.manager_ids
            if to_add or to_del:
                appraisal.meeting_ids.write({
                    'partner_ids': [
                        *[(3, x) for x in to_del.mapped('related_partner_id').ids],
                        *[(4, x) for x in to_add.mapped('related_partner_id').ids],
                    ]
                })

    @api.ondelete(at_uninstall=False)
    def _unlink_if_new_or_cancel(self):
        if any(appraisal.state not in ['new', 'cancel'] for appraisal in self):
            raise UserError(_("You cannot delete appraisal which is not in draft or cancelled state"))

    def read(self, fields=None, load='_classic_read'):
        fields_set = set(fields) if fields is not None else set()
        check_feedback = fields_set & {'manager_feedback', 'employee_feedback'}
        check_notes = fields_set & {'note', 'assessment_note'}
        if check_feedback:
            fields = fields + ['can_see_employee_publish', 'can_see_manager_publish', 'employee_feedback_published', 'manager_feedback_published']
        if check_notes:
            fields = fields + ['employee_id']
        records = super().read(fields, load)
        if check_notes:
            for appraisal in records:
                if appraisal['employee_id'] == self.env.user.employee_id.id:
                    appraisal['note'] = _('Note')
                    appraisal['assessment_note'] = False
        return records

    def action_calendar_event(self):
        self.ensure_one()
        partners = self.manager_ids.mapped('related_partner_id') | self.employee_id.related_partner_id | self.env.user.partner_id
        action = self.env["ir.actions.actions"]._for_xml_id("calendar.action_calendar_event")
        action['context'] = {
            'default_partner_ids': partners.ids,
            'default_res_model': 'hr.appraisal',
            'default_res_id': self.id,
            'default_name': _('Appraisal of %s', self.employee_id.name),
        }
        return action

    def action_confirm(self):
        self.state = 'pending'

    def action_done(self):
        self.state = 'done'

    def action_back(self):
        self.state = 'new'

    def action_open_employee_appraisals(self):
        self.ensure_one()
        view_id = self.env.ref('hr_appraisal.hr_appraisal_view_tree_orderby_create_date').id
        return {
            'name': _('Previous Appraisals'),
            'res_model': 'hr.appraisal',
            'view_mode': 'list,kanban,form,gantt,calendar,activity',
            'views': [(view_id, 'list'), (False, 'kanban'), (False, 'form'), (False, 'gantt'), (False, 'calendar'), (False, 'activity')],
            'domain': [('employee_id', '=', self.employee_id.id)],
            'type': 'ir.actions.act_window',
            'target': 'current',
            'context': {
                'search_default_groupby_date_close': True,
            }
        }

    def action_open_goals(self):
        self.ensure_one()
        return {
            'name': _("%s's Goals", self.employee_id.name),
            'view_mode': 'kanban,list,form,graph',
            'res_model': 'hr.appraisal.goal',
            'type': 'ir.actions.act_window',
            'target': 'current',
            'domain': [('employee_id', '=', self.employee_id.id)],
            'context': {'default_employee_id': self.employee_id.id},
        }

    def action_send_appraisal_request(self):
        return {
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'request.appraisal',
            'target': 'new',
            'name': _('Appraisal Request'),
            'context': {'default_appraisal_id': self.id},
        }

    @api.model
    def has_demo_data(self):
        if not self.env.user.has_group("hr_appraisal.group_hr_appraisal_user"):
            return True
        # This record only exists if the scenario has been already launched
        goal_tag = self.env.ref('hr_appraisal.hr_appraisal_goal_tag_softskills', raise_if_not_found=False)
        if goal_tag:
            return True
        return bool(self.env['ir.module.module'].search_count([
            '&',
                ('state', 'in', ['installed', 'to upgrade', 'uninstallable']),
                ('demo', '=', True)
        ]))

    def _load_demo_data(self):
        if self.has_demo_data():
            return
        env_sudo = self.sudo().with_context({}).env
        env_sudo['hr.employee']._load_scenario()
        convert.convert_file(env_sudo, 'hr_appraisal', 'data/scenarios/hr_appraisal_scenario.xml', None, mode='init',
            kind='data')
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }
