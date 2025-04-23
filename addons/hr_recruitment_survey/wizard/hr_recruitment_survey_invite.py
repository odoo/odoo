# Part of Odoo. See LICENSE file for full copyright and licensing details.
import re

from markupsafe import Markup
from odoo import api, fields, models
from odoo.tools.misc import clean_context
from odoo.tools.urls import urljoin
from odoo.exceptions import UserError
from odoo.tools.mail import email_split_and_format
from odoo.fields import Domain
from odoo.tools import html_sanitize

emails_split = re.compile(r"[;,\n\r]+")


class HrRecruitmentSurveyInvite(models.TransientModel):
    _name = 'hr.recruitment.survey.invite'
    _inherit = ["survey.invite"]
    _description = 'Wizard for sending interview invitations to job applicants during recruitment process'

    # Allow multiple applicants with different survey_ids
    applicant_ids = fields.Many2many('hr.applicant', string='Applicant')
    survey_ids = fields.Many2many('survey.survey', string='Surveys')
    single_survey_id = fields.Many2one('survey.survey', compute='_compute_single_survey', store=False)  # If all applicants associate with the same survey, otherwise False
    has_many_applicants = fields.Boolean(compute="_compute_has_many_applicants", store=False)
    hide_url = fields.Boolean(compute="_compute_hide_url", store=False)

    # Overrides
    survey_id = fields.Many2one('survey.survey', default=False, required=False)    # Make it optional, default it to False
    survey_access_mode = fields.Char(compute="_compute_survey_access_mode")
    survey_start_url = fields.Char('Survey URL', compute='_compute_survey_start_url')

    attachment_ids = fields.Many2many(
        'ir.attachment', 'hr_recruitment_survey_mail_compose_message_ir_attachments_rel', 'wizard_id', 'attachment_id',
        string='Attachments', compute='_compute_attachment_ids', store=True, readonly=False)

    partner_ids = fields.Many2many(
        'res.partner', 'hr_recruitment_survey_invite_partner_ids', 'invite_id', 'partner_id', string='Recipients'
    )

    # Security
    accessible_by_current_user = fields.Boolean(store=False, compute='_compute_accessible_by_current_user', search='_search_accessible_by_current_user')
    accessible_by_interviewer_user = fields.Boolean(store=False, compute='_compute_accessible_by_interviewer_user', search='_search_accessible_by_interviewer_user')
    all_surveys_are_recruitment = fields.Boolean(store=False, compute='_compute_all_surveys_are_recruitment', search='_search_all_surveys_are_recruitment')

    @api.depends('survey_ids')
    def _compute_single_survey(self):
        for invite in self:
            if invite.survey_ids and len(invite.survey_ids) == 1:
                invite.single_survey_id = invite.survey_ids
            else:
                invite.single_survey_id = False

    @api.depends('applicant_ids')
    def _compute_has_many_applicants(self):
        for invite in self:
            invite.has_many_applicants = len(invite.applicant_ids) > 1

    @api.depends('survey_access_mode', 'survey_ids')
    def _compute_hide_url(self):
        for invite in self:
            invite.hide_url = invite.survey_access_mode != 'public' or len(invite.survey_ids) > 1

    @api.depends('survey_ids', 'survey_ids.access_mode', 'single_survey_id')
    def _compute_survey_access_mode(self):
        for invite in self:
            if not invite.single_survey_id:
                invite.survey_access_mode = 'token'
            else:
                invite.survey_access_mode = self.single_survey_id.access_mode

    @api.depends('survey_ids', 'survey_id')
    def _compute_survey_start_url(self):
        for invite in self:
            if invite.single_survey_id:
                invite.survey_start_url = urljoin(invite.single_survey_id.get_base_url(), invite.single_survey_id.get_start_url())
            else:
                invite.survey_start_url = False

    @api.depends('survey_ids')
    def _compute_survey_users_login_required(self):
        for invite in self:
            invite.survey_users_login_required = any(s.users_login_required for s in invite.survey_ids)

    @api.depends('survey_ids')
    def _compute_survey_users_can_signup(self):
        for invite in self:
            invite.survey_users_can_signup = any(s.users_can_signup for s in invite.survey_ids)

    def _partners_access(self):
        # Filter applicants with surveys needing validation
        applicants_with_login_only_surveys = self.applicant_ids.filtered(
            lambda a: a.survey_id.users_login_required and not a.survey_id.users_can_signup
        )

        partner_survey_applicant_map = {(a.partner_id.id, a.survey_id.id): a for a in applicants_with_login_only_surveys}
        if partner_survey_applicant_map:
            # find partners with no linked users
            unlinked_partner_domain = Domain.FALSE
            for (partner_id, survey_id), _ in partner_survey_applicant_map.items():
                unlinked_partner_domain = Domain.OR(
                    [
                        unlinked_partner_domain,
                        Domain.AND(
                            [
                                Domain("id", "=", partner_id),
                                Domain("user_ids", "=", False),
                            ],
                        ),
                    ]
                )

            unlinked_partners = self.env['res.partner'].search(unlinked_partner_domain)
            if unlinked_partners:
                raise UserError(self.env._(
                    'The following recipients have no user account: %s. You should create user accounts for them or allow external signup in configuration.',
                    ', '.join(unlinked_partners.mapped('name'))
                ))

    @api.constrains('partner_ids')
    def _check_partners_access(self):
        self._partners_access()

    @api.onchange('partner_ids')
    def _onchange_partner_ids(self):
        self._partners_access()

    @api.onchange('emails')
    def _onchange_emails(self):
        if not self.single_survey_id or not self.emails:
            return
        if self.single_survey_id.users_login_required and not self.single_survey_id.users_can_signup:
            raise UserError(self.env._('This survey does not allow external people to participate. You should create user accounts or update survey access mode accordingly.'))

        valid, error = [], []
        emails = list(set(emails_split.split(self.emails or "")))
        for email in emails:
            email_check = email_split_and_format(email)
            if not email_check:
                error.append(email)
            else:
                valid.extend(email_check)
        if error:
            raise UserError(self.env._(
                "The following emails you just entered are invalid:\n%s"
            ) % '\n'.join(error))

        self.emails = '\n'.join(valid)

    def _prepare_answers(self, partners, emails):
        self.ensure_one()

        all_answers_domain = Domain.FALSE
        for applicant in self.applicant_ids:
            all_answers_domain = Domain.OR([
                all_answers_domain,
                Domain.AND([
                    Domain('survey_id', '=', applicant.survey_id.id),
                    Domain('partner_id', '=', applicant.partner_id.id)
                ])
            ])

        all_answers = self.env['survey.user_input'].search(all_answers_domain)

        # Index by (survey_id, partner_id)
        answers_by_applicant = all_answers.grouped(lambda ans: (ans.survey_id.id, ans.partner_id.id))

        total_answers = self.env['survey.user_input']
        for applicant in self.applicant_ids:
            key = (applicant.survey_id.id, applicant.partner_id.id)
            existing_answers = answers_by_applicant.get(key)

            _, _, answers = self._get_done_partners_emails(existing_answers)
            survey = applicant.survey_id

            if applicant.response_ids.filtered(lambda res: res.survey_id.id == survey.id):
                if not existing_answers or self.existing_mode != 'resend':
                    answers |= survey._create_answer(partner=applicant.partner_id, check_attempts=False, **self._get_answers_values())
            else:
                answers |= survey._create_answer(partner=applicant.partner_id, check_attempts=False, **self._get_answers_values())

            total_answers |= answers

        return total_answers

    def action_invite(self):
        self.ensure_one()
        if self.applicant_ids:
            for applicant_id in self.applicant_ids:
                survey = applicant_id.survey_id.with_context(clean_context(self.env.context))
                if not applicant_id.response_ids.filtered(lambda res: res.survey_id.id == survey.id):
                    applicant_id.sudo().write({
                        'response_ids': (applicant_id.response_ids | survey.sudo()._create_answer(partner=applicant_id.partner_id,
                            **self._get_answers_values())).ids
                    })
                partner = applicant_id.partner_id
                survey_link = survey._get_html_link(title=survey.title)
                partner_link = partner._get_html_link()
                content = self.env._('The survey %(survey_link)s has been sent to %(partner_link)s',
                    survey_link=survey_link,
                    partner_link=partner_link,
                )
                body = Markup('<p>%s</p>') % content
                applicant_id.message_post(body=body)
        return super().action_invite()

    # Mail compose overrides
    @api.depends('template_id', 'survey_ids')
    def _compute_subject(self):
        for invite in self:
            if invite.subject:
                continue
            else:
                if len(invite.survey_ids.ids) == 1:
                    invite.subject = self.env._("Interview Invitation: %(survey_name)s", survey_name=invite.single_survey_id.display_name)
                else:
                    invite.subject = self.env._("Interview Invitation")

    def _send_mail(self, answer):
        mail = super()._send_mail(answer)
        if answer.applicant_id:
            sanitized_html = html_sanitize(mail.body_html)
            answer.applicant_id.message_post(body=sanitized_html)
            if not self.scheduled_date or self.scheduled_date < fields.Datetime.now():
                mail.send()
        return mail

    # Security
    @api.depends('survey_ids.restrict_user_ids')
    def _compute_accessible_by_current_user(self):
        current_user = self.env.user
        for record in self:
            record.accessible_by_current_user = all(
                not survey.restrict_user_ids or current_user in survey.restrict_user_ids
                for survey in record.survey_ids
            )

    @api.depends('survey_ids.survey_type')
    def _compute_all_surveys_are_recruitment(self):
        for record in self:
            record.all_surveys_are_recruitment = all(
                survey.survey_type == 'recruitment'
                for survey in record.survey_ids
            )

    @api.depends('survey_ids.hr_job_ids.interviewer_ids', 'survey_ids.hr_job_ids.application_ids.interviewer_ids')
    def _compute_accessible_by_interviewer_user(self):
        current_user = self.env.user
        for record in self:
            record.accessible_by_interviewer_user = all(
                any(
                    current_user in (job.interviewer_ids | job.application_ids.interviewer_ids)
                    for job in survey.hr_job_ids
                )
                for survey in record.survey_ids
            )

    def _search_accessible_by_current_user(self, operator, value):
        if operator != 'in':
            return NotImplemented

        current_user = self.env.user

        accessible_survey_ids = self.env['survey.survey']._search([
            '|',
            ('restrict_user_ids', '=', False),
            ('restrict_user_ids', 'any', [('id', '=', current_user.id)])
        ])

        inaccessible_self_records = self.env['hr.recruitment.survey.invite']._search([
            ('survey_ids', '!=', False),
            ('survey_ids', 'any', [('id', 'not in', accessible_survey_ids)])  # True if one ore more survey(s) are NOT accessible
        ])

        domain = [('id', 'not in', inaccessible_self_records)] if value else [('id', 'in', inaccessible_self_records)]
        return domain

    def _search_all_surveys_are_recruitment(self, operator, value):
        if operator != 'in':
            return NotImplemented

        recruitment_survey_ids = self.env['survey.survey']._search([
            ('survey_type', '=', 'recruitment'),
        ])

        inaccessible_self_records = self.env['hr.recruitment.survey.invite']._search([
            ('survey_ids', '!=', False),
            ('survey_ids', 'any', [('id', 'not in', recruitment_survey_ids)])  # returns True if one or more survey(s) are NOT of type recruitment
        ])

        domain = [('id', 'not in', inaccessible_self_records)] if value else [('id', 'in', inaccessible_self_records)]
        return domain

    def _search_accessible_by_interviewer_user(self, operator, value):
        if operator != 'in':
            return NotImplemented

        current_user = self.env.user

        accessible_applications_by_interviewer = self.env['hr.applicant']._search([
            ('interviewer_ids', 'any', [('id', '=', current_user.id)])
        ])

        accessible_jobs_by_interviewer = self.env['hr.job']._search([
            '|',
            ('interviewer_ids', 'any', [('id', '=', current_user.id)]),
            ('application_ids', 'any', [('id', 'in', accessible_applications_by_interviewer)])
        ])

        accessible_survey_ids_by_interviewer = self.env['survey.survey']._search([
            ('hr_job_ids', 'any', [('id', 'in', accessible_jobs_by_interviewer)])
        ])

        inaccessible_self_records = self.env['hr.recruitment.survey.invite']._search([
            ('survey_ids', '!=', False),
            ('survey_ids', 'any', [('id', 'not in', accessible_survey_ids_by_interviewer)])  # True if one ore more survey(s) are NOT accessible
        ])

        domain = [('id', 'not in', inaccessible_self_records)] if value else [('id', 'in', inaccessible_self_records)]
        return domain
