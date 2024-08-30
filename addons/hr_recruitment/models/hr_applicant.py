# Part of Odoo. See LICENSE file for full copyright and licensing details.
import re

from markupsafe import Markup
from dateutil.relativedelta import relativedelta
from datetime import datetime

from odoo import api, fields, models, tools
from odoo.exceptions import UserError, ValidationError
from odoo.osv import expression
from odoo.tools.translate import _


AVAILABLE_PRIORITIES = [
    ('0', 'Normal'),
    ('1', 'Good'),
    ('2', 'Very Good'),
    ('3', 'Excellent')
]


class HrApplicant(models.Model):
    _name = 'hr.applicant'
    _description = "Applicant"
    _order = "priority desc, id desc"
    _inherit = ['mail.thread.cc',
               'mail.thread.main.attachment',
               'mail.activity.mixin',
               'utm.mixin',
               'mail.tracking.duration.mixin',
    ]
    _rec_name = "partner_name"
    _mailing_enabled = True
    _primary_email = 'email_from'
    _track_duration_field = 'stage_id'

    active = fields.Boolean("Active", default=True, help="If the active field is set to false, it will allow you to hide the case without removing it.", index=True)

    candidate_id = fields.Many2one('hr.candidate', required=True, index=True)
    partner_id = fields.Many2one(related="candidate_id.partner_id")
    partner_name = fields.Char(compute="_compute_partner_name", search="_search_partner_name", inverse="_inverse_name", compute_sudo=True)
    email_from = fields.Char(related="candidate_id.email_from", readonly=False)
    email_normalized = fields.Char(related="candidate_id.email_normalized")
    partner_phone = fields.Char(related="candidate_id.partner_phone", readonly=False)
    partner_phone_sanitized = fields.Char(related="candidate_id.partner_phone_sanitized")
    linkedin_profile = fields.Char(related="candidate_id.linkedin_profile", readonly=False)
    type_id = fields.Many2one(related="candidate_id.type_id", readonly=False)
    availability = fields.Date(related="candidate_id.availability", readonly=False)
    color = fields.Integer(related="candidate_id.color")
    employee_id = fields.Many2one(related="candidate_id.employee_id", readonly=False)
    emp_is_active = fields.Boolean(related="candidate_id.emp_is_active")
    employee_name = fields.Char(related="candidate_id.employee_name")

    probability = fields.Float("Probability")
    create_date = fields.Datetime("Applied on", readonly=True)
    stage_id = fields.Many2one('hr.recruitment.stage', 'Stage', ondelete='restrict', tracking=True,
                               compute='_compute_stage', store=True, readonly=False,
                               domain="['|', ('job_ids', '=', False), ('job_ids', '=', job_id)]",
                               copy=False, index=True,
                               group_expand='_read_group_stage_ids')
    last_stage_id = fields.Many2one('hr.recruitment.stage', "Last Stage",
                                    help="Stage of the applicant before being in the current stage. Used for lost cases analysis.")
    categ_ids = fields.Many2many('hr.applicant.category', string="Tags", compute='_compute_categ_ids', store=True, readonly=False)
    company_id = fields.Many2one('res.company', "Company", compute='_compute_company', store=True, readonly=False, tracking=True)
    user_id = fields.Many2one(
        'res.users', "Recruiter", compute='_compute_user', domain="[('share', '=', False), ('company_ids', 'in', company_id)]",
        tracking=True, store=True, readonly=False)
    date_closed = fields.Datetime("Hire Date", compute='_compute_date_closed', store=True, readonly=False, tracking=True, copy=False)
    date_open = fields.Datetime("Assigned", readonly=True)
    date_last_stage_update = fields.Datetime("Last Stage Update", index=True, default=fields.Datetime.now)
    priority = fields.Selection(AVAILABLE_PRIORITIES, "Evaluation", default='0')
    job_id = fields.Many2one('hr.job', "Job Position", domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]", tracking=True, index=True)
    salary_proposed_extra = fields.Char("Proposed Salary Extra", help="Salary Proposed by the Organisation, extra advantages", tracking=True, groups="hr_recruitment.group_hr_recruitment_user")
    salary_expected_extra = fields.Char("Expected Salary Extra", help="Salary Expected by Applicant, extra advantages", tracking=True, groups="hr_recruitment.group_hr_recruitment_user")
    salary_proposed = fields.Float("Proposed", aggregator="avg", help="Salary Proposed by the Organisation", tracking=True, groups="hr_recruitment.group_hr_recruitment_user")
    salary_expected = fields.Float("Expected", aggregator="avg", help="Salary Expected by Applicant", tracking=True, groups="hr_recruitment.group_hr_recruitment_user")
    department_id = fields.Many2one(
        'hr.department', "Department", compute='_compute_department', store=True, readonly=False,
        domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]", tracking=True)
    day_open = fields.Float(compute='_compute_day', string="Days to Open", compute_sudo=True)
    day_close = fields.Float(compute='_compute_day', string="Days to Close", compute_sudo=True)
    delay_close = fields.Float(compute="_compute_delay", string='Delay to Close', readonly=True, aggregator="avg", help="Number of days to close", store=True)
    user_email = fields.Char(related='user_id.email', string="User Email", readonly=True)
    attachment_number = fields.Integer(compute='_get_attachment_number', string="Number of Attachments")
    attachment_ids = fields.One2many('ir.attachment', 'res_id', domain=[('res_model', '=', 'hr.applicant')], string='Attachments')
    kanban_state = fields.Selection([
        ('normal', 'Grey'),
        ('done', 'Green'),
        ('blocked', 'Red')], string='Kanban State',
        copy=False, default='normal', required=True)
    legend_blocked = fields.Char(related='stage_id.legend_blocked', string='Kanban Blocked')
    legend_done = fields.Char(related='stage_id.legend_done', string='Kanban Valid')
    legend_normal = fields.Char(related='stage_id.legend_normal', string='Kanban Ongoing')
    refuse_reason_id = fields.Many2one('hr.applicant.refuse.reason', string='Refuse Reason', tracking=True)
    meeting_ids = fields.One2many('calendar.event', 'applicant_id', 'Meetings')
    meeting_display_text = fields.Char(compute='_compute_meeting_display')
    meeting_display_date = fields.Date(compute='_compute_meeting_display')
    # UTMs - enforcing the fact that we want to 'set null' when relation is unlinked
    campaign_id = fields.Many2one(ondelete='set null')
    medium_id = fields.Many2one(ondelete='set null', help="This displays how the applicant has reached out, e.g. via Email, LinkedIn, Website, etc.")
    source_id = fields.Many2one(ondelete='set null')
    interviewer_ids = fields.Many2many('res.users', 'hr_applicant_res_users_interviewers_rel',
        string='Interviewers', index=True, tracking=True,
        domain="[('share', '=', False), ('company_ids', 'in', company_id)]")
    application_status = fields.Selection([
        ('ongoing', 'Ongoing'),
        ('hired', 'Hired'),
        ('refused', 'Refused'),
        ('archived', 'Archived'),
    ], compute="_compute_application_status", search="_search_application_status")
    other_applications_count = fields.Integer(compute='_compute_other_applications_count', compute_sudo=True)
    applicant_properties = fields.Properties('Properties', definition='job_id.applicant_properties_definition', copy=True)
    applicant_notes = fields.Html()
    refuse_date = fields.Datetime('Refuse Date')

    _job_id_stage_id_idx = models.Index("(job_id, stage_id) WHERE active IS TRUE")

    @api.depends("candidate_id.partner_name")
    def _compute_partner_name(self):
        for applicant in self:
            applicant.partner_name = applicant.candidate_id.partner_name

    def _search_partner_name(self, operator, value):
        return [('candidate_id.partner_name', operator, value)]

    def _inverse_name(self):
        for applicant in self:
            if applicant.partner_name and not applicant.candidate_id:
                applicant.candidate_id = self.env['hr.candidate'].create({'partner_name': applicant.partner_name})
            else:
                applicant.candidate_id.partner_name = applicant.partner_name

    @api.depends('candidate_id')
    def _compute_other_applications_count(self):
        for applicant in self:
            same_candidate_applications = max(len(applicant.candidate_id.applicant_ids) - 1, 0)
            if applicant.candidate_id:
                domain = applicant.candidate_id._get_similar_candidates_domain()
                similar_candidates = self.env['hr.candidate'].with_context(active_test=False).search(domain) - applicant.candidate_id
                similar_candidate_applications = sum(len(candidate.applicant_ids) for candidate in similar_candidates)
                applicant.other_applications_count = similar_candidate_applications + same_candidate_applications
            else:
                applicant.other_applications_count = same_candidate_applications

    @api.depends('date_open', 'date_closed')
    def _compute_day(self):
        for applicant in self:
            if applicant.date_open:
                date_create = applicant.create_date
                date_open = applicant.date_open
                applicant.day_open = (date_open - date_create).total_seconds() / (24.0 * 3600)
            else:
                applicant.day_open = False
            if applicant.date_closed:
                date_create = applicant.create_date
                date_closed = applicant.date_closed
                applicant.day_close = (date_closed - date_create).total_seconds() / (24.0 * 3600)
            else:
                applicant.day_close = False

    @api.depends('day_open', 'day_close')
    def _compute_delay(self):
        for applicant in self:
            if applicant.date_open and applicant.day_close:
                applicant.delay_close = applicant.day_close - applicant.day_open
            else:
                applicant.delay_close = False

    @api.depends_context('lang')
    @api.depends('meeting_ids', 'meeting_ids.start')
    def _compute_meeting_display(self):
        applicant_with_meetings = self.filtered('meeting_ids')
        (self - applicant_with_meetings).update({
            'meeting_display_text': _('No Meeting'),
            'meeting_display_date': ''
        })
        today = fields.Date.today()
        for applicant in applicant_with_meetings:
            count = len(applicant.meeting_ids)
            dates = applicant.meeting_ids.mapped('start')
            min_date, max_date = min(dates).date(), max(dates).date()
            if min_date >= today:
                applicant.meeting_display_date = min_date
            else:
                applicant.meeting_display_date = max_date
            if count == 1:
                applicant.meeting_display_text = _('1 Meeting')
            elif applicant.meeting_display_date >= today:
                applicant.meeting_display_text = _('Next Meeting')
            else:
                applicant.meeting_display_text = _('Last Meeting')

    @api.depends('candidate_id')
    def _compute_categ_ids(self):
        for applicant in self:
            applicant.categ_ids = applicant.candidate_id.categ_ids.ids + applicant.categ_ids.ids

    @api.depends('refuse_reason_id', 'date_closed')
    def _compute_application_status(self):
        for applicant in self:
            if applicant.refuse_reason_id:
                applicant.application_status = 'refused'
            elif not applicant.active:
                applicant.application_status = 'archived'
            elif applicant.date_closed:
                applicant.application_status = 'hired'
            else:
                applicant.application_status = 'ongoing'

    def _search_application_status(self, operator, value):
        supported_operators = ['=', '!=', 'in', 'not in']
        if operator not in supported_operators:
            raise UserError(_('Operation not supported'))

        # Normalize value to be a list to simplify processing
        if isinstance(value, (str, bool)):
            value = [value]

        # Ensure all values are either correct strings or False
        valid_statuses = ['ongoing', 'hired', 'refused', 'archived']
        if not all(v in valid_statuses or v is False for v in value):
            raise UserError(_('Some values do not exist in the application status'))

        # Map statuses to domain filters
        for status in value:
            if status == 'refused':
                domain = [('refuse_reason_id', '!=', None)]
            elif status == 'hired':
                domain = [('date_closed', '!=', False)]
            elif status == 'archived' or status is False:
                domain = [('active', '=', False)]
            elif status == 'ongoing':
                domain = ['&', ('active', '=', True), ('date_closed', '=', False)]

        # Invert the domain for '!=' and 'not in' operators
        if operator in expression.NEGATIVE_TERM_OPERATORS:
            domain.insert(0, expression.NOT_OPERATOR)
            domain = expression.distribute_not(domain)
        return domain

    def _get_attachment_number(self):
        read_group_res = self.env['ir.attachment']._read_group(
            [('res_model', '=', 'hr.applicant'), ('res_id', 'in', self.ids)],
            ['res_id'], ['__count'])
        attach_data = dict(read_group_res)
        for record in self:
            record.attachment_number = attach_data.get(record.id, 0)

    @api.model
    def _read_group_stage_ids(self, stages, domain):
        # retrieve job_id from the context and write the domain: ids + contextual columns (job or default)
        job_id = self._context.get('default_job_id')
        search_domain = [('job_ids', '=', False)]
        if job_id:
            search_domain = ['|', ('job_ids', '=', job_id)] + search_domain
        if stages:
            search_domain = ['|', ('id', 'in', stages.ids)] + search_domain

        stage_ids = stages.sudo()._search(search_domain, order=stages._order)
        return stages.browse(stage_ids)

    @api.depends('job_id', 'department_id')
    def _compute_company(self):
        for applicant in self:
            company_id = False
            if applicant.department_id:
                company_id = applicant.department_id.company_id.id
            if not company_id and applicant.job_id:
                company_id = applicant.job_id.company_id.id
            applicant.company_id = company_id or self.env.company.id

    @api.depends('job_id')
    def _compute_department(self):
        for applicant in self:
            applicant.department_id = applicant.job_id.department_id.id

    @api.depends('job_id')
    def _compute_stage(self):
        for applicant in self:
            if applicant.job_id:
                if not applicant.stage_id:
                    stage_ids = self.env['hr.recruitment.stage'].search([
                        '|',
                        ('job_ids', '=', False),
                        ('job_ids', '=', applicant.job_id.id),
                        ('fold', '=', False)
                    ], order='sequence asc', limit=1).ids
                    applicant.stage_id = stage_ids[0] if stage_ids else False
            else:
                applicant.stage_id = False

    @api.depends('job_id')
    def _compute_user(self):
        for applicant in self:
            applicant.user_id = applicant.job_id.user_id.id

    def _phone_get_number_fields(self):
        """ This method returns the fields to use to find the number to use to
        send an SMS on a record. """
        return ['partner_phone']

    @api.depends('stage_id.hired_stage')
    def _compute_date_closed(self):
        for applicant in self:
            if applicant.stage_id and applicant.stage_id.hired_stage and not applicant.date_closed:
                applicant.date_closed = fields.Datetime.now()
            if not applicant.stage_id.hired_stage:
                applicant.date_closed = False

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('user_id'):
                vals['date_open'] = fields.Datetime.now()
            if vals.get('email_from'):
                vals['email_from'] = vals['email_from'].strip()
        applicants = super().create(vals_list)
        applicants.sudo().interviewer_ids._create_recruitment_interviewers()

        if (applicants.interviewer_ids.partner_id - self.env.user.partner_id):
            for applicant in applicants:
                interviewers_to_notify = applicant.interviewer_ids.partner_id - self.env.user.partner_id
                notification_subject = _("You have been assigned as an interviewer for %s", applicant.display_name)
                notification_body = _("You have been assigned as an interviewer for the Applicant %s", applicant.partner_name)
                applicant.message_notify(
                    res_id=applicant.id,
                    model=applicant._name,
                    partner_ids=interviewers_to_notify.ids,
                    author_id=self.env.user.partner_id.id,
                    email_from=self.env.user.email_formatted,
                    subject=notification_subject,
                    body=notification_body,
                    email_layout_xmlid="mail.mail_notification_layout",
                    record_name=applicant.display_name,
                    model_description="Applicant",
                )
        # Copy CV from candidate to applicant at record creation
        attachments_by_candidate = dict(self.env['ir.attachment']._read_group([
            ('res_id', 'in', applicants.candidate_id.ids),
            ('res_model', '=', "hr.candidate")
        ], groupby=['res_id'], aggregates=['id:recordset']))
        for applicant in applicants:
            if applicant.company_id != applicant.candidate_id.company_id:
                raise ValidationError(_("You cannot create an applicant in a different company than the candidate"))
            candidate_id = applicant.candidate_id.id
            if candidate_id not in attachments_by_candidate:
                continue
            attachments_by_candidate[candidate_id].copy({
                'res_id': applicant.id,
                'res_model': 'hr.applicant'
            })
        return applicants

    def write(self, vals):
        # user_id change: update date_open
        if vals.get('user_id'):
            vals['date_open'] = fields.Datetime.now()
        old_interviewers = self.interviewer_ids
        # stage_id: track last stage before update
        if 'stage_id' in vals:
            vals['date_last_stage_update'] = fields.Datetime.now()
            if 'kanban_state' not in vals:
                vals['kanban_state'] = 'normal'
            for applicant in self:
                vals['last_stage_id'] = applicant.stage_id.id
                new_stage = self.env['hr.recruitment.stage'].browse(vals['stage_id'])
                if new_stage.hired_stage and not applicant.stage_id.hired_stage:
                    if applicant.job_id.no_of_recruitment > 0:
                        applicant.job_id.no_of_recruitment -= 1
                elif not new_stage.hired_stage and applicant.stage_id.hired_stage:
                    applicant.job_id.no_of_recruitment += 1
        res = super().write(vals)

        if 'interviewer_ids' in vals:
            interviewers_to_clean = old_interviewers - self.interviewer_ids
            interviewers_to_clean._remove_recruitment_interviewers()
            self.sudo().interviewer_ids._create_recruitment_interviewers()
            self.message_unsubscribe(partner_ids=interviewers_to_clean.partner_id.ids)

            new_interviewers = self.interviewer_ids - old_interviewers - self.env.user
            if new_interviewers:
                notification_subject = _("You have been assigned as an interviewer for %s", self.display_name)
                notification_body = _("You have been assigned as an interviewer for the Applicant %s", self.partner_name)
                self.message_notify(
                    res_id=self.id,
                    model=self._name,
                    partner_ids=new_interviewers.partner_id.ids,
                    author_id=self.env.user.partner_id.id,
                    email_from=self.env.user.email_formatted,
                    subject=notification_subject,
                    body=notification_body,
                    email_layout_xmlid="mail.mail_notification_layout",
                    record_name=self.display_name,
                    model_description="Applicant",
                )
        if vals.get('date_closed'):
            for applicant in self:
                if applicant.job_id.date_to:
                    applicant.candidate_id.availability = applicant.job_id.date_to + relativedelta(days=1)

        if vals.get("company_id") and not self.env.context.get('do_not_propagate_company', False):
            self.candidate_id.with_context(do_not_propagate_company=True).write({"company_id": vals["company_id"]})
            self.candidate_id.applicant_ids.with_context(do_not_propagate_company=True).write({"company_id": vals["company_id"]})

        return res

    def get_empty_list_help(self, help_message):
        if 'active_id' in self.env.context and self.env.context.get('active_model') == 'hr.job':
            hr_job = self.env['hr.job'].browse(self.env.context['active_id'])
        elif self.env.context.get('default_job_id'):
            hr_job = self.env['hr.job'].browse(self.env.context['default_job_id'])
        else:
            hr_job = self.env['hr.job']

        nocontent_body = Markup("""
<p class="o_view_nocontent_smiling_face">%(help_title)s</p>
""") % {
            'help_title': _("No application found. Let's create one !"),
        }

        if hr_job:
            pattern = r'(.*)<a>(.*?)<\/a>(.*)'
            match = re.fullmatch(pattern, _('Have you tried to <a>add skills to your job position</a> and search into the Reserve ?'))
            nocontent_body += Markup("""
<p>%(para_1)s<a href="%(link)s">%(para_2)s</a>%(para_3)s</p>""") % {
            'para_1': match[1],
            'para_2': match[2],
            'para_3': match[3],
            'link': f'/odoo/recruitment/{hr_job.id}',
        }

        if hr_job.alias_email:
            nocontent_body += Markup('<p class="o_copy_paste_email oe_view_nocontent_alias">%(helper_email)s <a href="mailto:%(email)s">%(email)s</a></p>') % {
                'helper_email': _("Try creating an application by sending an email to"),
                'email': hr_job.alias_email,
            }

        return super().get_empty_list_help(nocontent_body)

    @api.model
    def get_view(self, view_id=None, view_type='form', **options):
        if view_type == 'form' and self.env.user.has_group('hr_recruitment.group_hr_recruitment_interviewer')\
            and not self.env.user.has_group('hr_recruitment.group_hr_recruitment_user'):
            view_id = self.env.ref('hr_recruitment.hr_applicant_view_form_interviewer').id
        return super().get_view(view_id, view_type, **options)

    def action_create_meeting(self):
        """ This opens Meeting's calendar view to schedule meeting on current applicant
            @return: Dictionary value for created Meeting view
        """
        self.ensure_one()
        if not self.partner_id:
            if not self.partner_name:
                raise UserError(_('You must define a Contact Name for this applicant.'))
            self.partner_id = self.env['res.partner'].create({
                'is_company': False,
                'name': self.partner_name,
                'email': self.email_from,
            })

        partners = self.partner_id | self.department_id.manager_id.user_id.partner_id
        if self.env.user.has_group('hr_recruitment.group_hr_recruitment_interviewer') and not self.env.user.has_group('hr_recruitment.group_hr_recruitment_user'):
            partners |= self.env.user.partner_id
        else:
            partners |= self.user_id.partner_id

        res = self.env['ir.actions.act_window']._for_xml_id('calendar.action_calendar_event')
        # As we are redirected from the hr.applicant, calendar checks rules on "hr.applicant",
        # in order to decide whether to allow creation of a meeting.
        # As interviewer does not have create right on the hr.applicant, in order to allow them
        # to create a meeting for an applicant, we pass 'create': True to the context.
        res['context'] = {
            'create': True,
            'default_applicant_id': self.id,
            'default_candidate_id': self.candidate_id.id,
            'default_partner_ids': partners.ids,
            'default_user_id': self.env.uid,
            'default_name': self.partner_name,
            'attachment_ids': self.attachment_ids.ids
        }
        return res

    def action_open_attachments(self):
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'ir.attachment',
            'name': _('Documents'),
            'context': {
                'default_res_model': 'hr.applicant',
                'default_res_id': self.ids[0],
                'show_partner_name': 1,
            },
            'view_mode': 'list,form',
            'views': [
                (self.env.ref('hr_recruitment.ir_attachment_hr_recruitment_list_view').id, 'list'),
                (False, 'form'),
            ],
            'search_view_id': self.env.ref('hr_recruitment.ir_attachment_view_search_inherit_hr_recruitment').ids,
            'domain': [('res_model', '=', 'hr.applicant'), ('res_id', 'in', self.ids), ],
        }

    def action_open_employee(self):
        self.ensure_one()
        return self.candidate_id.action_open_employee()

    def action_open_other_applications(self):
        self.ensure_one()
        similar_candidates = (
            self.env["hr.candidate"]
            .with_context(active_test=False)
            .search(self.candidate_id._get_similar_candidates_domain())
            - self.candidate_id
        )
        return {
            'name': _('Other Applications'),
            'type': 'ir.actions.act_window',
            'res_model': 'hr.applicant',
            'view_mode': 'list,kanban,form,pivot,graph,calendar,activity',
            'domain': [('id', 'in', (self.candidate_id.applicant_ids - self + similar_candidates.applicant_ids).ids)],
            'context': {
                'active_test': False,
                'search_default_stage': 1,
            },
        }

    def _track_template(self, changes):
        res = super()._track_template(changes)
        applicant = self[0]
        # When applcant is unarchived, they are put back to the default stage automatically. In this case,
        # don't post automated message related to the stage change.
        if 'stage_id' in changes and applicant.exists()\
            and applicant.stage_id.template_id\
            and not applicant._context.get('just_moved')\
            and not applicant._context.get('just_unarchived'):
            res['stage_id'] = (applicant.stage_id.template_id, {
                'auto_delete_keep_log': False,
                'subtype_id': self.env['ir.model.data']._xmlid_to_res_id('mail.mt_note'),
                'email_layout_xmlid': 'hr_recruitment.mail_notification_light_without_background'
            })
        return res

    def _creation_subtype(self):
        return self.env.ref('hr_recruitment.mt_applicant_new')

    def _track_subtype(self, init_values):
        record = self[0]
        if 'stage_id' in init_values and record.stage_id:
            return self.env.ref('hr_recruitment.mt_applicant_stage_changed')
        return super()._track_subtype(init_values)

    def _notify_get_reply_to(self, default=None):
        """ Override to set alias of applicants to their job definition if any. """
        aliases = self.job_id._notify_get_reply_to(default=default)
        res = {app.id: aliases.get(app.job_id.id) for app in self}
        leftover = self.filtered(lambda rec: not rec.job_id)
        if leftover:
            res.update(super(HrApplicant, leftover)._notify_get_reply_to(default=default))
        return res

    def _message_get_suggested_recipients(self):
        recipients = super()._message_get_suggested_recipients()
        if self.partner_id:
            self._message_add_suggested_recipient(recipients, partner=self.partner_id.sudo(), reason=_('Contact'))
        elif self.email_from:
            email_from = tools.email_normalize(self.email_from)
            if email_from and self.partner_name:
                email_from = tools.formataddr((self.partner_name, email_from))
                self._message_add_suggested_recipient(recipients, email=email_from, reason=_('Contact Email'))
        return recipients

    @api.depends('partner_name')
    @api.depends_context('show_partner_name')
    def _compute_display_name(self):
        if not self.env.context.get('show_partner_name'):
            return super()._compute_display_name()
        for applicant in self:
            applicant.display_name = applicant.partner_name or applicant.name

    @api.model
    def message_new(self, msg, custom_values=None):
        # Remove default author when going through the mail gateway. Indeed, we
        # do not want to explicitly set user_id to False; however we do not
        # want the gateway user to be responsible if no other responsible is
        # found.
        self = self.with_context(default_user_id=False, mail_notify_author=True)  # Allows sending stage updates to the author
        stage = False
        candidate_defaults = {}
        if custom_values and 'job_id' in custom_values:
            job = self.env['hr.job'].browse(custom_values['job_id'])
            stage = job._get_first_stage()
            candidate_defaults['company_id'] = job.company_id.id

        partner_name, email_from_normalized = tools.parse_contact_from_email(msg.get('from'))
        candidate = self.env["hr.candidate"].search(
            [
                ("email_from", "=", email_from_normalized),
            ],
            limit=1,
        ) or self.env["hr.candidate"].create(
            {
                "partner_name": partner_name or email_from_normalized,
                **candidate_defaults,
            }
        )

        defaults = {
            'candidate_id': candidate.id,
            'partner_name': partner_name,
        }
        job_platform = self.env['hr.job.platform'].search([('email', '=', email_from_normalized)], limit=1)
        if msg.get('from') and not job_platform:
            candidate.email_from = msg.get('from')
            candidate.partner_id = msg.get('author_id', False)
        if msg.get('email_from') and job_platform:
            subject_pattern = re.compile(job_platform.regex or '')
            regex_results = re.findall(subject_pattern, msg.get('subject')) + re.findall(subject_pattern, msg.get('body'))
            candidate.partner_name = regex_results[0] if regex_results else partner_name
            defaults["partner_name"] = candidate.partner_name
            del msg['email_from']
        if msg.get('priority'):
            defaults['priority'] = msg.get('priority')
        if stage and stage.id:
            defaults['stage_id'] = stage.id
        if custom_values:
            defaults.update(custom_values)
        res = super().message_new(msg, custom_values=defaults)
        candidate._compute_partner_phone_email()
        return res

    def _message_post_after_hook(self, message, msg_vals):
        if self.email_from and not self.partner_id:
            # we consider that posting a message with a specified recipient (not a follower, a specific one)
            # on a document without customer means that it was created through the chatter using
            # suggested recipients. This heuristic allows to avoid ugly hacks in JS.
            email_normalized = tools.email_normalize(self.email_from)
            new_partner = message.partner_ids.filtered(
                lambda partner: partner.email == self.email_from or (email_normalized and partner.email_normalized == email_normalized)
            )
            if new_partner:
                if new_partner[0].create_date.date() == fields.Date.today():
                    new_partner[0].write({
                        'name': self.partner_name or self.email_from,
                    })
                if new_partner[0].email_normalized:
                    email_domain = ('email_from', 'in', [new_partner[0].email, new_partner[0].email_normalized])
                else:
                    email_domain = ('email_from', '=', new_partner[0].email)
                self.search([
                    ('partner_id', '=', False), email_domain, ('stage_id.fold', '=', False)
                ]).write({'partner_id': new_partner[0].id})
        return super()._message_post_after_hook(message, msg_vals)

    def create_employee_from_applicant(self):
        self.ensure_one()
        action = self.candidate_id.create_employee_from_candidate()
        employee = self.env['hr.employee'].browse(action['res_id'])
        employee.write({
            'job_id': self.job_id.id,
            'job_title': self.job_id.name,
            'department_id': self.department_id.id,
            'work_email': self.department_id.company_id.email or self.email_from, # To have a valid email address by default
            'work_phone': self.department_id.company_id.phone,
        })
        return action

    def archive_applicant(self):
        return {
            'type': 'ir.actions.act_window',
            'name': _('Refuse Reason'),
            'res_model': 'applicant.get.refuse.reason',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_applicant_ids': self.ids, 'active_test': False},
            'views': [[False, 'form']]
        }

    def reset_applicant(self):
        """ Reinsert the applicant into the recruitment pipe in the first stage"""
        default_stage = dict()
        for job_id in self.job_id:
            default_stage[job_id.id] = self.env['hr.recruitment.stage'].search(
                [
                    '|',
                    ('job_ids', '=', False),
                    ('job_ids', '=', job_id.id),
                    ('fold', '=', False)
                ], order='sequence asc', limit=1).id
        for applicant in self:
            applicant.write(
                {'stage_id': applicant.job_id.id and default_stage[applicant.job_id.id],
                 'refuse_reason_id': False})

    def action_archive(self):
        return super(HrApplicant, self.with_context(just_unarchived=True)).action_archive()

    def action_unarchive(self):
        active_applicants = super(HrApplicant, self.with_context(just_unarchived=True)).action_unarchive()
        if active_applicants:
            active_applicants.reset_applicant()
        return active_applicants

    def action_send_email(self):
        return {
            'name': _('Send Email'),
            'type': 'ir.actions.act_window',
            'target': 'new',
            'view_mode': 'form',
            'res_model': 'applicant.send.mail',
            'context': {
                'default_applicant_ids': self.ids,
            }
        }

    def _get_duration_from_tracking(self, trackings):
        json = super()._get_duration_from_tracking(trackings)
        now = datetime.now()
        for applicant in self:
            if applicant.refuse_reason_id and applicant.refuse_date:
                json[applicant.stage_id.id] -= (now - applicant.refuse_date).total_seconds()
        return json
