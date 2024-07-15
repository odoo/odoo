# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from markupsafe import Markup

from odoo import api, fields, models, tools, SUPERUSER_ID
from odoo.exceptions import AccessError, UserError
from odoo.osv import expression
from odoo.tools import Query
from odoo.tools.translate import _

from dateutil.relativedelta import relativedelta

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
               'mail.thread.blacklist',
               'mail.thread.phone',
               'mail.activity.mixin',
               'utm.mixin']
    _mailing_enabled = True
    _primary_email = 'email_from'

    name = fields.Char("Subject / Application", required=True, help="Email subject for applications sent via email", index='trigram')
    active = fields.Boolean("Active", default=True, help="If the active field is set to false, it will allow you to hide the case without removing it.", index=True)
    description = fields.Html("Description")
    email_from = fields.Char("Email", size=128, compute='_compute_partner_phone_email',
        inverse='_inverse_partner_email', store=True, index='trigram')
    email_normalized = fields.Char(index='trigram')  # inherited via mail.thread.blacklist
    probability = fields.Float("Probability")
    partner_id = fields.Many2one('res.partner', "Contact", copy=False, index='btree_not_null')
    create_date = fields.Datetime("Applied on", readonly=True)
    stage_id = fields.Many2one('hr.recruitment.stage', 'Stage', ondelete='restrict', tracking=True,
                               compute='_compute_stage', store=True, readonly=False,
                               domain="['|', ('job_ids', '=', False), ('job_ids', '=', job_id)]",
                               copy=False, index=True,
                               group_expand='_read_group_stage_ids')
    last_stage_id = fields.Many2one('hr.recruitment.stage', "Last Stage",
                                    help="Stage of the applicant before being in the current stage. Used for lost cases analysis.")
    categ_ids = fields.Many2many('hr.applicant.category', string="Tags")
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
    salary_proposed = fields.Float("Proposed Salary", group_operator="avg", help="Salary Proposed by the Organisation", tracking=True, groups="hr_recruitment.group_hr_recruitment_user")
    salary_expected = fields.Float("Expected Salary", group_operator="avg", help="Salary Expected by Applicant", tracking=True, groups="hr_recruitment.group_hr_recruitment_user")
    availability = fields.Date("Availability", help="The date at which the applicant will be available to start working", tracking=True)
    partner_name = fields.Char("Applicant's Name")
    partner_phone = fields.Char("Phone", size=32, compute='_compute_partner_phone_email',
        store=True, readonly=False, index='btree_not_null', inverse='_inverse_partner_email')
    partner_phone_sanitized = fields.Char(string='Sanitized Phone Number', compute='_compute_partner_phone_sanitized', store=True, index='btree_not_null')
    partner_mobile = fields.Char("Mobile", size=32, compute='_compute_partner_phone_email',
        store=True, readonly=False, index='btree_not_null', inverse='_inverse_partner_email')
    partner_mobile_sanitized = fields.Char(string='Sanitized Mobile Number', compute='_compute_partner_mobile_sanitized', store=True, index='btree_not_null')
    type_id = fields.Many2one('hr.recruitment.degree', "Degree")
    department_id = fields.Many2one(
        'hr.department', "Department", compute='_compute_department', store=True, readonly=False,
        domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]", tracking=True)
    day_open = fields.Float(compute='_compute_day', string="Days to Open", compute_sudo=True)
    day_close = fields.Float(compute='_compute_day', string="Days to Close", compute_sudo=True)
    delay_close = fields.Float(compute="_compute_delay", string='Delay to Close', readonly=True, group_operator="avg", help="Number of days to close", store=True)
    color = fields.Integer("Color Index", default=0)
    emp_id = fields.Many2one('hr.employee', string="Employee", help="Employee linked to the applicant.", copy=False)
    emp_is_active = fields.Boolean(string="Employee Active", related='emp_id.active')
    user_email = fields.Char(related='user_id.email', string="User Email", readonly=True)
    attachment_number = fields.Integer(compute='_get_attachment_number', string="Number of Attachments")
    employee_name = fields.Char(related='emp_id.name', string="Employee Name", readonly=False, tracking=False)
    attachment_ids = fields.One2many('ir.attachment', 'res_id', domain=[('res_model', '=', 'hr.applicant')], string='Attachments')
    kanban_state = fields.Selection([
        ('normal', 'Grey'),
        ('done', 'Green'),
        ('blocked', 'Red')], string='Kanban State',
        copy=False, default='normal', required=True)
    legend_blocked = fields.Char(related='stage_id.legend_blocked', string='Kanban Blocked')
    legend_done = fields.Char(related='stage_id.legend_done', string='Kanban Valid')
    legend_normal = fields.Char(related='stage_id.legend_normal', string='Kanban Ongoing')
    application_count = fields.Integer(compute='_compute_application_count', help='Applications with the same email or phone or mobile')
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
    linkedin_profile = fields.Char('LinkedIn Profile')
    application_status = fields.Selection([
        ('ongoing', 'Ongoing'),
        ('hired', 'Hired'),
        ('refused', 'Refused'),
        ('archived', 'Archived'),
    ], compute="_compute_application_status")
    applicant_properties = fields.Properties('Properties', definition='job_id.applicant_properties_definition', copy=True)

    def init(self):
        super().init()
        self.env.cr.execute("""
            CREATE INDEX IF NOT EXISTS hr_applicant_job_id_stage_id_idx
            ON hr_applicant(job_id, stage_id)
            WHERE active IS TRUE
        """)
        self.env.cr.execute("""
            CREATE INDEX IF NOT EXISTS hr_applicant_email_partner_phone_mobile
            ON hr_applicant(email_normalized, partner_mobile_sanitized, partner_phone_sanitized);
        """)

    @api.onchange('job_id')
    def _onchange_job_id(self):
        for applicant in self:
            if applicant.job_id.name:
                applicant.name = applicant.job_id.name

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

    @api.depends('email_from', 'partner_mobile_sanitized', 'partner_phone_sanitized')
    def _compute_application_count(self):
        """
            The field application_count is only used on the form view.
            Thus, using ORM rather then querying, should not make much
            difference in terms of performance, while being more readable and secure.
        """
        if not any(self._ids):
            for applicant in self:
                domain = applicant._get_similar_applicants_domain()
                if domain:
                    applicant.application_count = max(0, self.env["hr.applicant"].with_context(active_test=False).search_count(domain) - 1)
                else:
                    applicant.application_count = 0
            return
        self.flush_recordset(['email_normalized', 'partner_phone_sanitized', 'partner_mobile_sanitized'])
        self.env.cr.execute("""
            SELECT
                id,
                (
                    SELECT COUNT(*)
                    FROM hr_applicant AS sub
                    WHERE a.id != sub.id
                     AND ((a.email_normalized <> '' AND sub.email_normalized = a.email_normalized)
                       OR (a.partner_mobile_sanitized <> '' AND a.partner_mobile_sanitized = sub.partner_mobile_sanitized)
                       OR (a.partner_mobile_sanitized <> '' AND a.partner_mobile_sanitized = sub.partner_phone_sanitized)
                       OR (a.partner_phone_sanitized <> '' AND a.partner_phone_sanitized = sub.partner_mobile_sanitized)
                       OR (a.partner_phone_sanitized <> '' AND a.partner_phone_sanitized = sub.partner_phone_sanitized))
                ) AS similar_applicants
            FROM hr_applicant AS a
            WHERE id IN %(ids)s
        """, {'ids': tuple(self._origin.ids)})
        query_results = self.env.cr.dictfetchall()
        mapped_data = {result['id']: result['similar_applicants'] for result in query_results}
        for applicant in self:
            applicant.application_count = mapped_data.get(applicant.id, 0)

    def _get_similar_applicants_domain(self):
        """
            This method returns a domain for the applicants whitch match with the
            current applicant according to email_from, partner_phone or partner_mobile.
            Thus, search on the domain will return the current applicant as well if any of
            the following fields are filled.
        """
        self.ensure_one()
        if not self:
            return None
        domain = []
        if self.email_normalized:
            domain = expression.OR([domain, [('email_normalized', '=', self.email_normalized)]])
        if self.partner_phone_sanitized:
            domain = expression.OR([domain, ['|', ('partner_phone_sanitized', '=', self.partner_phone_sanitized), ('partner_mobile_sanitized', '=', self.partner_phone_sanitized)]])
        if self.partner_mobile_sanitized:
            domain = expression.OR([domain, ['|', ('partner_mobile_sanitized', '=', self.partner_mobile_sanitized), ('partner_phone_sanitized', '=', self.partner_mobile_sanitized)]])
        return domain if domain else None

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

    def _get_attachment_number(self):
        read_group_res = self.env['ir.attachment']._read_group(
            [('res_model', '=', 'hr.applicant'), ('res_id', 'in', self.ids)],
            ['res_id'], ['__count'])
        attach_data = dict(read_group_res)
        for record in self:
            record.attachment_number = attach_data.get(record.id, 0)

    @api.model
    def _read_group_stage_ids(self, stages, domain, order):
        # retrieve job_id from the context and write the domain: ids + contextual columns (job or default)
        job_id = self._context.get('default_job_id')
        search_domain = [('job_ids', '=', False)]
        if job_id:
            search_domain = ['|', ('job_ids', '=', job_id)] + search_domain
        if stages:
            search_domain = ['|', ('id', 'in', stages.ids)] + search_domain

        stage_ids = stages._search(search_domain, order=order, access_rights_uid=SUPERUSER_ID)
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

    @api.depends('partner_id')
    def _compute_partner_phone_email(self):
        for applicant in self:
            if not applicant.partner_id:
                continue
            applicant.email_from = applicant.partner_id.email
            if not applicant.partner_phone:
                applicant.partner_phone = applicant.partner_id.phone
            if not applicant.partner_mobile:
                applicant.partner_mobile = applicant.partner_id.mobile

    def _inverse_partner_email(self):
        for applicant in self:
            if not applicant.email_from:
                continue
            if not applicant.partner_id:
                if not applicant.partner_name:
                    raise UserError(_('You must define a Contact Name for this applicant.'))
                applicant.partner_id = self.env['res.partner'].with_context(default_lang=self.env.lang).find_or_create(applicant.email_from)
            if applicant.partner_name and not applicant.partner_id.name:
                applicant.partner_id.name = applicant.partner_name
            if tools.email_normalize(applicant.email_from) != tools.email_normalize(applicant.partner_id.email):
                # change email on a partner will trigger other heavy code, so avoid to change the email when
                # it is the same. E.g. "email@example.com" vs "My Email" <email@example.com>""
                applicant.partner_id.email = applicant.email_from
            if applicant.partner_mobile:
                applicant.partner_id.mobile = applicant.partner_mobile
            if applicant.partner_phone:
                applicant.partner_id.phone = applicant.partner_phone

    @api.depends('partner_phone')
    def _compute_partner_phone_sanitized(self):
        for applicant in self:
            applicant.partner_phone_sanitized = applicant._phone_format(fname='partner_phone') or applicant.partner_phone

    @api.depends('partner_mobile')
    def _compute_partner_mobile_sanitized(self):
        for applicant in self:
            applicant.partner_mobile_sanitized = applicant._phone_format(fname='partner_mobile') or applicant.partner_mobile

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

    def _check_interviewer_access(self):
        if self.user_has_groups('hr_recruitment.group_hr_recruitment_interviewer') and not self.user_has_groups('hr_recruitment.group_hr_recruitment_user'):
            raise AccessError(_('You are not allowed to perform this action.'))

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
            category = self.env.ref('hr_recruitment.categ_meet_interview')
            for applicant in applicants:
                partners = applicant.partner_id | applicant.user_id.partner_id | applicant.department_id.manager_id.user_id.partner_id
                self.env['calendar.event'].sudo().with_context(default_applicant_id=applicant.id).create({
                    'applicant_id': applicant.id,
                    'partner_ids': [(6, 0, partners.ids)],
                    'user_id': self.env.uid,
                    'name': applicant.name,
                    'categ_ids': [category.id],
                    'start': deadline,
                    'stop': deadline + relativedelta(minutes=30),
                })
        return applicants

    def write(self, vals):
        # user_id change: update date_open
        if vals.get('user_id'):
            vals['date_open'] = fields.Datetime.now()
        if vals.get('email_from'):
            vals['email_from'] = vals['email_from'].strip()
            if self._email_is_blacklisted(vals['email_from']):
                del vals['email_from']
        old_interviewers = self.interviewer_ids
        # stage_id: track last stage before update
        if 'stage_id' in vals:
            vals['date_last_stage_update'] = fields.Datetime.now()
            if 'kanban_state' not in vals:
                vals['kanban_state'] = 'normal'
            for applicant in self:
                vals['last_stage_id'] = applicant.stage_id.id
                res = super(Applicant, self).write(vals)
        else:
            res = super(Applicant, self).write(vals)
        if 'interviewer_ids' in vals:
            interviewers_to_clean = old_interviewers - self.interviewer_ids
            interviewers_to_clean._remove_recruitment_interviewers()
            self.sudo().interviewer_ids._create_recruitment_interviewers()
        if vals.get('emp_id'):
            self._update_employee_from_applicant()
        return res

    def _email_is_blacklisted(self, mail):
        normalized_mail = tools.email_normalize(mail)
        return normalized_mail in [m.strip() for m in self.env['ir.config_parameter'].sudo().get_param('hr_recruitment.blacklisted_emails', '').split(',')]

    def get_empty_list_help(self, help_message):
        if 'active_id' in self.env.context and self.env.context.get('active_model') == 'hr.job':
            hr_job = self.env['hr.job'].browse(self.env.context['active_id'])
        elif self.env.context.get('default_job_id'):
            hr_job = self.env['hr.job'].browse(self.env.context['default_job_id'])
        else:
            hr_job = self.env['hr.job']

        nocontent_body = Markup("""
<p class="o_view_nocontent_smiling_face">%(help_title)s</p>
<p>%(para_1)s<br/>%(para_2)s</p>""") % {
            'help_title': _("No application found. Let's create one !"),
            'para_1': _('People can also apply by email to save time.'),
            'para_2': _("You can search into attachment's content, like resumes, with the searchbar."),
        }

        if hr_job.alias_email:
            nocontent_body += Markup('<p class="o_copy_paste_email oe_view_nocontent_alias">%(helper_email)s <a href="mailto:%(email)s">%(email)s</a></p>') % {
                'helper_email': _("Create new applications by sending an email to"),
                'email': hr_job.alias_email,
            }

        return super().get_empty_list_help(nocontent_body)

    @api.model
    def get_view(self, view_id=None, view_type='form', **options):
        if view_type == 'form' and self.user_has_groups('hr_recruitment.group_hr_recruitment_interviewer')\
            and not self.user_has_groups('hr_recruitment.group_hr_recruitment_user'):
            view_id = self.env.ref('hr_recruitment.hr_applicant_view_form_interviewer').id
        return super().get_view(view_id, view_type, **options)

    def action_makeMeeting(self):
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
        if self.user_has_groups('hr_recruitment.group_hr_recruitment_interviewer') and not self.user_has_groups('hr_recruitment.group_hr_recruitment_user'):
            partners |= self.env.user.partner_id
        else:
            partners |= self.user_id.partner_id

        category = self.env.ref('hr_recruitment.categ_meet_interview')
        res = self.env['ir.actions.act_window']._for_xml_id('calendar.action_calendar_event')
        # As we are redirected from the hr.applicant, calendar checks rules on "hr.applicant",
        # in order to decide whether to allow creation of a meeting.
        # As interviewer does not have create right on the hr.applicant, in order to allow them
        # to create a meeting for an applicant, we pass 'create': True to the context.
        res['context'] = {
            'create': True,
            'default_applicant_id': self.id,
            'default_partner_ids': partners.ids,
            'default_user_id': self.env.uid,
            'default_name': self.name,
            'default_categ_ids': category and [category.id] or False,
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

    def action_applications_email(self):
        self.ensure_one()
        other_applicants = self.env['hr.applicant']
        domain = self._get_similar_applicants_domain()
        if domain:
            other_applicants = self.env['hr.applicant'].with_context(active_test=False).search(domain)
        return {
            'type': 'ir.actions.act_window',
            'name': _('Job Applications'),
            'res_model': self._name,
            'view_mode': 'tree,kanban,form,pivot,graph,calendar,activity',
            'domain': [('id', 'in', other_applicants.ids)],
            'context': {
                'active_test': False,
                'search_default_stage': 1,
            },
        }

    def action_open_employee(self):
        self.ensure_one()
        return {
            'name': _('Employee'),
            'type': 'ir.actions.act_window',
            'res_model': 'hr.employee',
            'view_mode': 'form',
            'res_id': self.emp_id.id,
        }

    def _track_template(self, changes):
        res = super(Applicant, self)._track_template(changes)
        applicant = self[0]
        # When applcant is unarchived, they are put back to the default stage automatically. In this case,
        # don't post automated message related to the stage change.
        if 'stage_id' in changes and applicant.exists() and applicant.stage_id.template_id and not applicant._context.get('just_unarchived'):
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
        recipients = super(Applicant, self)._message_get_suggested_recipients()
        for applicant in self:
            if applicant.partner_id:
                applicant._message_add_suggested_recipient(recipients, partner=applicant.partner_id.sudo(), reason=_('Contact'))
            elif applicant.email_from:
                email_from = tools.email_normalize(applicant.email_from)
                if email_from and applicant.partner_name:
                    email_from = tools.formataddr((applicant.partner_name, email_from))
                    applicant._message_add_suggested_recipient(recipients, email=email_from, reason=_('Contact Email'))
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
        defaults = {
            'name': msg.get('subject') or _("No Subject"),
            'partner_name': partner_name or email_from_normalized,
        }
        if msg.get('from') and not self._email_is_blacklisted(msg.get('from')):
            defaults['email_from'] = msg.get('from')
            defaults['partner_id'] = msg.get('author_id', False)
        if msg.get('email_from') and self._email_is_blacklisted(msg.get('email_from')):
            del msg['email_from']
        if msg.get('priority'):
            defaults['priority'] = msg.get('priority')
        if stage and stage.id:
            defaults['stage_id'] = stage.id
        if custom_values:
            defaults.update(custom_values)
        res = super().message_new(msg, custom_values=defaults)
        res._compute_partner_phone_email()
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
        """ Create an employee from applicant """
        self.ensure_one()
        self._check_interviewer_access()

        if not self.partner_id:
            if not self.partner_name:
                raise UserError(_('Please provide an applicant name.'))
            self.partner_id = self.env['res.partner'].create({
                'is_company': False,
                'name': self.partner_name,
                'email': self.email_from,
            })

        action = self.env['ir.actions.act_window']._for_xml_id('hr.open_view_employee_list')
        employee = self.env['hr.employee'].create(self._get_employee_create_vals())
        action['res_id'] = employee.id
        return action

    def _get_employee_create_vals(self):
        self.ensure_one()
        address_id = self.partner_id.address_get(['contact'])['contact']
        address_sudo = self.env['res.partner'].sudo().browse(address_id)
        return {
            'name': self.partner_name or self.partner_id.display_name,
            'work_contact_id': self.partner_id.id,
            'job_id': self.job_id.id,
            'job_title': self.job_id.name,
            'private_street': address_sudo.street,
            'private_street2': address_sudo.street2,
            'private_city': address_sudo.city,
            'private_state_id': address_sudo.state_id.id,
            'private_zip': address_sudo.zip,
            'private_country_id': address_sudo.country_id.id,
            'private_phone': address_sudo.phone,
            'private_email': address_sudo.email,
            'lang': address_sudo.lang,
            'department_id': self.department_id.id,
            'address_id': self.company_id.partner_id.id,
            'work_email': self.department_id.company_id.email or self.email_from, # To have a valid email address by default
            'work_phone': self.department_id.company_id.phone,
            'applicant_id': self.ids,
            'private_phone': self.partner_phone or self.partner_mobile
        }

    def _update_employee_from_applicant(self):
        # This method is to be overriden
        return

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
