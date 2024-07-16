# Part of Odoo. See LICENSE file for full copyright and licensing details.
import re

from markupsafe import Markup
from dateutil.relativedelta import relativedelta
from datetime import datetime

from odoo import api, fields, models, tools
from odoo.exceptions import AccessError, UserError
from odoo.osv import expression
from odoo.tools.translate import _


AVAILABLE_PRIORITIES = [
    ('0', 'Normal'),
    ('1', 'Good'),
    ('2', 'Very Good'),
    ('3', 'Excellent')
]


class Applicant(models.Model):
    _name = "hr.applicant"
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
    description = fields.Html("Description")

    candidate_id = fields.Many2one('hr.candidate', required=True, index=True)
    partner_id = fields.Many2one(related="candidate_id.partner_id")
    partner_name = fields.Char(related="candidate_id.partner_name", inverse="_inverse_name")
    email_from = fields.Char(related="candidate_id.email_from", readonly=False)
    email_normalized = fields.Char(related="candidate_id.email_normalized")
    partner_phone = fields.Char(related="candidate_id.partner_phone", readonly=False)
    partner_phone_sanitized = fields.Char(related="candidate_id.partner_phone_sanitized")
    partner_mobile = fields.Char(related="candidate_id.partner_mobile", readonly=False)
    partner_mobile_sanitized = fields.Char(related="candidate_id.partner_mobile_sanitized")
    linkedin_profile = fields.Char(related="candidate_id.linkedin_profile", readonly=False)
    type_id = fields.Many2one(related="candidate_id.type_id", readonly=False)
    availability = fields.Date(related="candidate_id.availability", readonly=False)
    color = fields.Integer(related="candidate_id.color")
    employee_id = fields.Many2one(related="candidate_id.employee_id", readonly=False)
    emp_is_active = fields.Boolean(related="candidate_id.emp_is_active")
    employee_name = fields.Char(related="candidate_id.employee_name")

    similar_candidates_count = fields.Integer(related="candidate_id.similar_candidates_count")

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
    date_closed = fields.Datetime("Hire Date", compute='_compute_date_closed', store=True, readonly=False, tracking=True)
    date_open = fields.Datetime("Assigned", readonly=True)
    date_last_stage_update = fields.Datetime("Last Stage Update", index=True, default=fields.Datetime.now)
    priority = fields.Selection(AVAILABLE_PRIORITIES, "Evaluation", default='0')
    job_id = fields.Many2one('hr.job', "Applied Job", domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]", tracking=True, index=True)
    salary_proposed_extra = fields.Char("Proposed Salary Extra", help="Salary Proposed by the Organisation, extra advantages", tracking=True, groups="hr_recruitment.group_hr_recruitment_user")
    salary_expected_extra = fields.Char("Expected Salary Extra", help="Salary Expected by Applicant, extra advantages", tracking=True, groups="hr_recruitment.group_hr_recruitment_user")
    salary_proposed = fields.Float("Proposed Salary", aggregator="avg", help="Salary Proposed by the Organisation", tracking=True, groups="hr_recruitment.group_hr_recruitment_user")
    salary_expected = fields.Float("Expected Salary", aggregator="avg", help="Salary Expected by Applicant", tracking=True, groups="hr_recruitment.group_hr_recruitment_user")
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
    medium_id = fields.Many2one(ondelete='set null')
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
    refuse_date = fields.Datetime('Refuse Date')

    def init(self):
        super().init()
        self.env.cr.execute("""
            CREATE INDEX IF NOT EXISTS hr_applicant_job_id_stage_id_idx
            ON hr_applicant(job_id, stage_id)
            WHERE active IS TRUE
        """)

    def _inverse_name(self):
        for applicant in self:
            if applicant.partner_name and not applicant.candidate_id:
                applicant.candidate_id = self.env['hr.candidate'].create({'partner_name': applicant.partner_name})
            else:
                applicant.candidate_id.partner_name = applicant.partner_name

    @api.depends('candidate_id')
    def _compute_other_applications_count(self):
        for applicant in self:
            applicant.other_applications_count = max(len(applicant.candidate_id.applicant_ids) - 1, 0)

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
            applicant.categ_ids = applicant.candidate_id.categ_ids

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
        return ['partner_mobile', 'partner_phone']

    @api.depends('stage_id.hired_stage')
    def _compute_date_closed(self):
        for applicant in self:
            if applicant.stage_id and applicant.stage_id.hired_stage and not applicant.date_closed:
                applicant.date_closed = fields.datetime.now()
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
        # Record creation through calendar, creates the calendar event directly, it will also create the activity.
        if 'default_activity_date_deadline' in self.env.context:
            deadline = fields.Datetime.to_datetime(self.env.context.get('default_activity_date_deadline'))
            for applicant in applicants:
                partners = applicant.partner_id | applicant.user_id.partner_id | applicant.department_id.manager_id.user_id.partner_id
                self.env['calendar.event'].sudo().with_context(default_applicant_id=applicant.id).create({
                    'applicant_id': applicant.id,
                    'partner_ids': [(6, 0, partners.ids)],
                    'user_id': self.env.uid,
                    'name': applicant.partner_name,
                    'start': deadline,
                    'stop': deadline + relativedelta(minutes=30),
                })
        # Copy CV from candidate to applicant at record creation
        attachments_result = self.env['ir.attachment'].read_group([
            ('res_id', 'in', applicants.candidate_id.ids),
            ('res_model', '=', "hr.candidate")
        ], ['ids:array_agg(id)'], groupby=['res_id'])
        attachments_by_candidate = {e['res_id']: e['ids'] for e in attachments_result}
        for applicant in applicants:
            candidate_id = applicant.candidate_id.id
            if candidate_id not in attachments_by_candidate:
                continue
            self.env['ir.attachment'].browse(attachments_by_candidate[candidate_id]).copy({
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
                res = super().write(vals)
        else:
            res = super().write(vals)
        if 'interviewer_ids' in vals:
            interviewers_to_clean = old_interviewers - self.interviewer_ids
            interviewers_to_clean._remove_recruitment_interviewers()
            self.sudo().interviewer_ids._create_recruitment_interviewers()
        if vals.get('date_closed'):
            for applicant in self:
                if applicant.job_id.date_to:
                    applicant.candidate_id.availability = applicant.job_id.date_to + relativedelta(days=1)
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
<p class="mb-0">%(para_1)s<br/>%(para_2)s</p>""") % {
            'help_title': _("No application found. Let's create one !"),
            'para_1': _('People can also apply by email to save time.'),
            'para_2': _("You can search into attachment's content, like resumes, with the searchbar."),
        }

        if hr_job:
            pattern = r'(.*)<a>(.*?)<\/a>(.*)'
            match = re.fullmatch(pattern, _('Have you tried to <a>add skills to your job position</a> and search into the Reserve ?'))
            nocontent_body += Markup("""
<p>%(para_1)s<a href="%(link)s">%(para_2)s</a>%(para_3)s</p>""") % {
            'para_1': match[1],
            'para_2': match[2],
            'para_3': match[3],
            'link': f'/odoo/recruitement/{hr_job.id}',
        }

        if hr_job.alias_email:
            nocontent_body += Markup('<p class="o_copy_paste_email oe_view_nocontent_alias">%(helper_email)s <a href="mailto:%(email)s">%(email)s</a></p>') % {
                'helper_email': _("Create new applications by sending an email to"),
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
            'view_mode': 'tree,form',
            'views': [
                (self.env.ref('hr_recruitment.ir_attachment_hr_recruitment_list_view').id, 'tree'),
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
        return {
            'name': _('Other Applications'),
            'type': 'ir.actions.act_window',
            'res_model': 'hr.applicant',
            'view_mode': 'tree,kanban,form,pivot,graph,calendar,activity',
            'domain': [('id', 'in', (self.candidate_id.applicant_ids - self).ids)],
            'context': {
                'active_test': False,
                'search_default_stage': 1,
            },
        }

    def action_open_similar_candidates(self):
        self.ensure_one()
        return self.candidate_id.action_open_similar_candidates()

    def _track_template(self, changes):
        res = super(Applicant, self)._track_template(changes)
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
        return super(Applicant, self)._track_subtype(init_values)

    def _notify_get_reply_to(self, default=None):
        """ Override to set alias of applicants to their job definition if any. """
        aliases = self.mapped('job_id')._notify_get_reply_to(default=default)
        res = {app.id: aliases.get(app.job_id.id) for app in self}
        leftover = self.filtered(lambda rec: not rec.job_id)
        if leftover:
            res.update(super(Applicant, leftover)._notify_get_reply_to(default=default))
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
        """ Overrides mail_thread message_new that is called by the mailgateway
            through message_process.
            This override updates the document according to the email.
        """
        # Remove default author when going through the mail gateway. Indeed, we
        # do not want to explicitly set user_id to False; however we do not
        # want the gateway user to be responsible if no other responsible is
        # found.
        self = self.with_context(default_user_id=False)
        stage = False
        if custom_values and 'job_id' in custom_values:
            stage = self.env['hr.job'].browse(custom_values['job_id'])._get_first_stage()
        partner_name, email_from_normalized = tools.parse_contact_from_email(msg.get('from'))
        candidate = self.env['hr.candidate'].create({'partner_name': partner_name or email_from_normalized})
        defaults = {
            'candidate_id': candidate.id,
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
        return super(Applicant, self)._message_post_after_hook(message, msg_vals)

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
        for job_id in self.mapped('job_id'):
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

    def toggle_active(self):
        self = self.with_context(just_unarchived=True)
        res = super(Applicant, self).toggle_active()
        active_applicants = self.filtered(lambda applicant: applicant.active)
        if active_applicants:
            active_applicants.reset_applicant()
        return res

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
