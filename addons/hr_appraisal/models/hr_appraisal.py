# -*- coding: utf-8 -*-

from dateutil.relativedelta import relativedelta

from openerp import api, fields, models, _
from openerp.exceptions import UserError


class HrAppraisal(models.Model):
    _name = "hr.appraisal"
    _inherit = ['mail.thread']
    _description = "Employee Appraisal"
    _order = 'date_close, interview_deadline'

    APPRAISAL_STATE = [
        ('new', 'To Start'),
        ('pending', 'Appraisal Sent'),
        ('done', 'Done')
    ]

    @api.multi
    def _track_subtype(self, init_values):
        self.ensure_one()
        if 'state' in init_values and self.state == 'new':
            return 'hr_appraisal.mt_appraisal_new'
        if 'interview_deadline' in init_values and not self.meeting_id or self.env.context.get('meeting'):
            return 'hr_appraisal.mt_appraisal_meeting'
        return super(HrAppraisal, self)._track_subtype(init_values)

    action_plan = fields.Text(string="Action Plan", help="If the evaluation does not meet the expectations, you can propose an action plan")
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.user.company_id)
    color = fields.Integer(string='Color Index')
    department_id = fields.Many2one('hr.department', related='employee_id.department_id', string='Department', store=True)
    date_close = fields.Datetime(string='Appraisal Deadline', index=True, required=True)
    employee_id = fields.Many2one('hr.employee', required=True, string='Employee', index=True)
    state = fields.Selection(APPRAISAL_STATE, string='Status', track_visibility='onchange', required=True, readonly=True, copy=False, default='new', index=True)
    manager = fields.Boolean(string='Manager')
    manager_ids = fields.Many2many('hr.employee', 'appraisal_manager_rel', 'hr_appraisal_id')
    manager_survey_id = fields.Many2one('survey.survey', string="Manager's Appraisal")
    subordinates = fields.Boolean(string='Collaborator')
    subordinates_ids = fields.Many2many('hr.employee', 'appraisal_subordinates_rel', 'hr_appraisal_id')
    subordinates_survey_id = fields.Many2one('survey.survey', string="collaborate's Appraisal")
    colleagues = fields.Boolean(string='Colleagues')
    colleagues_ids = fields.Many2many('hr.employee', 'appraisal_colleagues_rel', 'hr_appraisal_id')
    colleagues_survey_id = fields.Many2one('survey.survey', string="Employee's Appraisal")
    appraisal_self = fields.Boolean(string='Employee')
    appraisal_employee = fields.Char(related='employee_id.name', string='Employee Name')
    appraisal_self_survey_id = fields.Many2one('survey.survey', string='Self Appraisal')
    user_input_ids = fields.One2many('survey.user_input', 'survey_res_id', string='Send Forms', auto_join=True, domain=lambda self: [('survey_model', '=', self._name)])
    completed_user_input_ids = fields.One2many('survey.user_input', 'survey_res_id', string='Answers', auto_join=True, domain=lambda self: [('survey_model', '=', self._name), ('state', '=', 'done')])
    mail_template_id = fields.Many2one('mail.template', string="Email Template For Appraisal", default=lambda self: self.env.ref('hr_appraisal.send_appraisal_template'))
    meeting_id = fields.Many2one('calendar.event', string='Meeting')
    interview_deadline = fields.Date(string="Final Interview", index=True, track_visibility='onchange')

    @api.onchange('employee_id')
    def onchange_employee_id(self):
        if self.employee_id:
            self.department_id = self.employee_id.department_id
            self.manager = self.employee_id.appraisal_manager
            self.manager_ids = self.employee_id.appraisal_manager_ids
            self.manager_survey_id = self.employee_id.appraisal_manager_survey_id
            self.colleagues = self.employee_id.appraisal_colleagues
            self.colleagues_ids = self.employee_id.appraisal_colleagues_ids
            self.colleagues_survey_id = self.employee_id.appraisal_colleagues_survey_id
            self.appraisal_self = self.employee_id.appraisal_self
            self.appraisal_self_survey_id = self.employee_id.appraisal_self_survey_id
            self.subordinates = self.employee_id.appraisal_subordinates
            self.subordinates_ids = self.employee_id.appraisal_subordinates_ids
            self.subordinates_survey_id = self.employee_id.appraisal_subordinates_survey_id

    @api.multi
    def subscribe_employee(self):
        for appraisal in self:
            emp_partner_ids = [emp.related_partner_id.id for emp in appraisal.manager_ids if emp.related_partner_id]
            if appraisal.employee_id.related_partner_id:
                emp_partner_ids.append(appraisal.employee_id.related_partner_id.id)
            if appraisal.employee_id.department_id.manager_id.related_partner_id:
                emp_partner_ids.append(appraisal.employee_id.department_id.manager_id.related_partner_id.id)
            if appraisal.employee_id.parent_id.related_partner_id:
                emp_partner_ids.append(appraisal.employee_id.parent_id.related_partner_id.id)
            appraisal.message_subscribe(partner_ids=emp_partner_ids)
        return True

    @api.multi
    def schedule_final_meeting(self, interview_deadline):
        """ Creates event when user enters date manually from the form view.
            If users edit the already entered date, created meeting is updated accordingly.
        """
        CalendarEvent = self.env['calendar.event']
        values = {'start_date': interview_deadline, 'stop_date': interview_deadline}
        for appraisal in self:
            if appraisal.meeting_id and appraisal.meeting_id.allday:
                appraisal.meeting_id.write(values)
            elif appraisal.meeting_id and not appraisal.meeting_id.allday:
                date = fields.Date.from_string(interview_deadline)
                meeting_date = fields.Datetime.to_string(date)
                appraisal.meeting_id.write({'start_datetime': meeting_date, 'stop_datetime': meeting_date})
            if not appraisal.meeting_id:
                attendee_ids = [(4, manager.related_partner_id.id) for manager in appraisal.manager_ids if manager.related_partner_id]
                if appraisal.employee_id.related_partner_id:
                    attendee_ids.append((4, appraisal.employee_id.related_partner_id.id))
                values['name'] = _('Appraisal Meeting For %s') % appraisal.employee_id.name_related
                values['allday'] = True
                values['partner_ids'] = attendee_ids
                appraisal.meeting_id = CalendarEvent.create(values)
        return True

    @api.model
    def create(self, vals):
        result = super(HrAppraisal, self.with_context(mail_create_nolog=True)).create(vals)
        result.subscribe_employee()
        interview_deadline = vals.get('interview_deadline')
        if interview_deadline:
            # creating employee meeting and interview date
            result.schedule_final_meeting(interview_deadline)
        return result

    @api.multi
    def write(self, vals):
        result = super(HrAppraisal, self).write(vals)
        self.subscribe_employee()
        interview_deadline = vals.get('interview_deadline')
        if interview_deadline:
            # creating employee meeting and interview date
            self.schedule_final_meeting(interview_deadline)
        if vals.get('state') == 'pending':
            self.send_appraisal()
        return result

    def _prepare_user_input_receivers(self):
        """
        @return: returns a list of tuple (survey, employee).
        """
        appraisal_receiver = []
        if self.manager and self.manager_ids and self.manager_survey_id:
            appraisal_receiver.append((self.manager_survey_id, self.manager_ids))
        if self.colleagues and self.colleagues_ids and self.colleagues_survey_id:
            appraisal_receiver.append((self.colleagues_survey_id, self.colleagues_ids))
        if self.subordinates and self.subordinates_ids and self.subordinates_survey_id:
            appraisal_receiver.append((self.subordinates_survey_id, self.subordinates_ids))
        if self.appraisal_self and self.appraisal_employee and self.appraisal_self_survey_id:
            appraisal_receiver.append((self.appraisal_self_survey_id, self.employee_id))
        return appraisal_receiver

    @api.multi
    def send_appraisal(self):
        ComposeMessage = self.env['survey.mail.compose.message']
        MailTemplate = self.env['mail.template']
        for appraisal in self:
            appraisal_receiver = appraisal._prepare_user_input_receivers()
            for survey, receivers in appraisal_receiver:
                for employee in receivers:
                    email = employee.related_partner_id.email or employee.work_email
                    render_template = MailTemplate.with_context(email=email, survey=survey, employee=employee).generate_email_batch(appraisal.mail_template_id.id, [appraisal.id])
                    values = {
                        'survey_id': survey.id,
                        'public': 'email_private',
                        'partner_ids': employee.related_partner_id and [(4, employee.related_partner_id.id)] or False,
                        'multi_email': email,
                        'subject': survey.title,
                        'body': render_template[appraisal.id]['body'],
                        'date_deadline': appraisal.date_close,
                        'model': appraisal._name,
                        'res_id': appraisal.id,
                    }
                    wizard = ComposeMessage.create(values)
                    wizard.send_mail()
            appraisal.message_post(body=_("Appraisal(s) form have been sent"), subtype="hr_appraisal.mt_appraisal_sent")
        return True

    @api.multi
    def button_send_appraisal(self):
        """ Changes 'To Start' state to 'Appraisal Sent'."""
        return self.write({'state': 'pending'})

    @api.multi
    def button_done_appraisal(self):
        """ Changes 'Appraisal Sent' state to 'Done'."""
        return self.write({'state': 'done'})

    @api.multi
    def name_get(self):
        result = []
        for appraisal in self:
            result.append((appraisal.id, '%s' % (appraisal.employee_id.name_related)))
        return result

    @api.multi
    def unlink(self):
        for appraisal in self:
            if appraisal.state != 'new':
                appraisal_state = dict(self.APPRAISAL_STATE)
                raise UserError(_("You cannot delete appraisal which is in '%s' state") % (appraisal_state[appraisal.state]))
        return super(HrAppraisal, self).unlink()

    def read_group(self, cr, uid, domain, fields, groupby, offset=0, limit=None, context=None, orderby=False, lazy=True):
        """ Override read_group to always display all states. """
        if groupby and groupby[0] == "state":
            states = self.APPRAISAL_STATE
            read_group_all_states = [{
                '__context': {'group_by': groupby[1:]},
                '__domain': domain + [('state', '=', state_value)],
                'state': state_value,
            } for state_value, state_name in states]
            read_group_res = super(HrAppraisal, self).read_group(cr, uid, domain, fields, groupby, offset, limit, context, orderby, lazy)
            result = []
            for state_value, state_name in states:
                res = filter(lambda x: x['state'] == state_value, read_group_res)
                if not res:
                    res = filter(lambda x: x['state'] == state_value, read_group_all_states)
                if res[0]['state'] == 'done':
                    res[0]['__fold'] = True
                result.append(res[0])
            return result
        return super(HrAppraisal, self).read_group(cr, uid, domain, fields, groupby, offset=offset, limit=limit, context=context, orderby=orderby, lazy=lazy)

    @api.multi
    def action_get_users_input(self):
        """ Link to open sent appraisal"""
        self.ensure_one()
        if self.env.context.get('answers'):
            users_input = self.completed_user_input_ids
        else:
            users_input = self.user_input_ids
        action = self.env.ref('survey.action_survey_user_input').read()[0]
        action['domain'] = str([('id', 'in', users_input.ids)])
        return action

    @api.multi
    def action_calendar_event(self):
        """ Link to open calendar view for creating employee interview/meeting"""
        self.ensure_one()
        partner_ids = [manager.related_partner_id.id for manager in self.manager_ids if manager.related_partner_id]
        if self.employee_id.related_partner_id:
            partner_ids.append(self.employee_id.related_partner_id.id)
        action = self.env.ref('calendar.action_calendar_event').read()[0]
        partner_ids.append(self.env.user.partner_id.id)
        action['context'] = {
            'default_partner_ids': partner_ids,
            'search_default_mymeetings': 1
        }
        return action


class HrEmployee(models.Model):
    _inherit = "hr.employee"

    @api.one
    def _compute_related_partner(self):
        self.related_partner_id = self.user_id.partner_id or self.address_home_id

    appraisal_date = fields.Date(string='Next Appraisal Date', help="The date of the next appraisal is computed by the appraisal plan's dates (first appraisal + periodicity).")
    appraisal_manager = fields.Boolean(string='Manager')
    appraisal_manager_ids = fields.Many2many('hr.employee', 'emp_appraisal_manager_rel', 'hr_appraisal_id')
    appraisal_manager_survey_id = fields.Many2one('survey.survey', string="Manager's Appraisal")
    appraisal_colleagues = fields.Boolean(string='Colleagues')
    appraisal_colleagues_ids = fields.Many2many('hr.employee', 'emp_appraisal_colleagues_rel', 'hr_appraisal_id')
    appraisal_colleagues_survey_id = fields.Many2one('survey.survey', string="Employee's Appraisal")
    appraisal_self = fields.Boolean(string='Employee')
    appraisal_employee = fields.Char(string='Employee Name')
    appraisal_self_survey_id = fields.Many2one('survey.survey', string='Self Appraisal')
    appraisal_subordinates = fields.Boolean(string='Collaborator')
    appraisal_subordinates_ids = fields.Many2many('hr.employee', 'emp_appraisal_subordinates_rel', 'hr_appraisal_id')
    appraisal_subordinates_survey_id = fields.Many2one('survey.survey', string="collaborate's Appraisal")
    appraisal_repeat = fields.Boolean(string='Periodic Appraisal', default=False)
    appraisal_repeat_number = fields.Integer(string='Repeat Every', default=1)
    appraisal_repeat_delay = fields.Selection([('year', 'Year'), ('month', 'Month')], string='Repeat Every', copy=False, default='year')
    appraisal_ids = fields.One2many('hr.appraisal', 'employee_id', string='Appraisals')
    related_partner_id = fields.Many2one('res.partner', compute='_compute_related_partner')

    @api.onchange('appraisal_manager', 'parent_id')
    def onchange_manager_appraisal(self):
        if self.appraisal_manager:
            self.appraisal_manager_ids = [self.parent_id.id]

    @api.onchange('appraisal_self')
    def onchange_self_employee(self):
        self.appraisal_employee = self.name

    @api.onchange('appraisal_colleagues')
    def onchange_colleagues(self):
        if self.department_id:
            self.appraisal_colleagues_ids = self.search([('department_id', '=', self.department_id.id), ('parent_id', '!=', False)])

    @api.onchange('appraisal_subordinates')
    def onchange_subordinates(self):
        self.appraisal_subordinates_ids = self.search([('parent_id', '!=', False)]).mapped('parent_id')

    @api.model
    def run_employee_appraisal(self, automatic=False, use_new_cursor=False):  # cronjob
        current_date = fields.Date.from_string(fields.Date.today())
        next_date = fields.Date.today()
        for employee in self.search([('appraisal_date', '<=', current_date)]):
            if employee.appraisal_repeat_delay == 'month':
                next_date = fields.Date.to_string(current_date + relativedelta(months=employee.appraisal_repeat_number))
            else:
                next_date = fields.Date.to_string(current_date + relativedelta(months=employee.appraisal_repeat_number * 12))
            employee.write({'appraisal_date': next_date})
            vals = {'employee_id': employee.id,
                    'date_close': current_date,
                    'manager': employee.appraisal_manager,
                    'manager_ids': [(4, manager.id) for manager in employee.appraisal_manager_ids] or [(4, employee.parent_id.id)],
                    'manager_survey_id': employee.appraisal_manager_survey_id.id,
                    'colleagues': employee.appraisal_colleagues,
                    'colleagues_ids': [(4, colleagues.id) for colleagues in employee.appraisal_colleagues_ids],
                    'colleagues_survey_id': employee.appraisal_colleagues_survey_id.id,
                    'appraisal_self': employee.appraisal_self,
                    'appraisal_employee': employee.appraisal_employee or employee.name,
                    'appraisal_self_survey_id': employee.appraisal_self_survey_id.id,
                    'subordinates': employee.appraisal_subordinates,
                    'subordinates_ids': [(4, subordinates.id) for subordinates in employee.appraisal_subordinates_ids],
                    'subordinates_survey_id': employee.appraisal_subordinates_survey_id.id}
            self.env['hr.appraisal'].create(vals)
        return True
