# Part of Odoo. See LICENSE file for full copyright and licensing details.
import re

from markupsafe import Markup
from collections import defaultdict
from datetime import datetime

from odoo import api, fields, models, tools
from odoo.exceptions import UserError, ValidationError
from odoo.fields import Domain
from odoo.tools import SQL, clean_context
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
               'mail.thread.blacklist',
               'mail.thread.phone',
               'mail.activity.mixin',
               'utm.mixin',
               'mail.tracking.duration.mixin',
    ]
    _rec_name = "partner_name"
    _mailing_enabled = True
    _primary_email = 'email_from'
    _track_duration_field = 'stage_id'
    _order = "sequence"

    sequence = fields.Integer(string='Sequence', index=True, default=10)
    active = fields.Boolean("Active", default=True, help="If the active field is set to false, it will allow you to hide the case without removing it.", index=True)

    partner_id = fields.Many2one('res.partner', "Contact", copy=False, index='btree_not_null')
    partner_name = fields.Char("Applicant's Name")
    email_from = fields.Char(
        string="Email",
        size=128,
        copy=True,
        index='trigram',
    )
    email_normalized = fields.Char(index='trigram')  # inherited via mail.thread.blacklist
    partner_phone = fields.Char(
        string="Phone",
        size=32,
        copy=True,
        index='btree_not_null',
    )
    partner_phone_sanitized = fields.Char(
        string="Sanitized Phone Number", compute='_compute_partner_phone_sanitized', store=True, index='btree_not_null'
    )
    linkedin_profile = fields.Char('LinkedIn Profile', index='btree_not_null')
    type_id = fields.Many2one('hr.recruitment.degree', "Degree")
    availability = fields.Date("Availability", help="The date at which the applicant will be available to start working", tracking=True)
    color = fields.Integer("Color Index", default=0)
    employee_id = fields.Many2one('hr.employee', string="Employee", help="Employee linked to the applicant.", copy=False, index='btree_not_null')
    emp_is_active = fields.Boolean(string="Employee Active", related='employee_id.active')
    employee_name = fields.Char(related='employee_id.name', string="Employee Name", readonly=False, tracking=False)

    probability = fields.Float("Probability")
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
    date_closed = fields.Datetime("Hire Date", compute='_compute_date_closed', store=True, readonly=False, tracking=True, copy=False)
    date_open = fields.Datetime("Assigned", readonly=True)
    date_last_stage_update = fields.Datetime("Last Stage Update", index=True, default=fields.Datetime.now)
    priority = fields.Selection(AVAILABLE_PRIORITIES, "Evaluation", default='0')
    job_id = fields.Many2one('hr.job', "Job Position", domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]", tracking=True, index=True, copy=False)
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
        string='Interviewers', index=True, tracking=True, copy=False,
        domain="[('share', '=', False), ('company_ids', 'in', company_id)]")
    application_status = fields.Selection([
        ('ongoing', 'Ongoing'),
        ('hired', 'Hired'),
        ('refused', 'Refused'),
        ('archived', 'Archived'),
    ], compute="_compute_application_status", search="_search_application_status")
    application_count = fields.Integer(compute='_compute_application_count', help='Applications with the same email or phone or mobile')
    applicant_properties = fields.Properties('Properties', definition='job_id.applicant_properties_definition', copy=True)
    applicant_notes = fields.Html()
    refuse_date = fields.Datetime('Refuse Date')
    talent_pool_ids = fields.Many2many(comodel_name="hr.talent.pool", string="Talent Pools", groups="base.group_user")
    pool_applicant_id = fields.Many2one("hr.applicant", index='btree_not_null')
    is_pool_applicant = fields.Boolean(compute="_compute_is_pool")
    is_applicant_in_pool = fields.Boolean(
        compute="_compute_is_applicant_in_pool", search="_search_is_applicant_in_pool"
    )
    talent_pool_count = fields.Integer(compute="_compute_talent_pool_count")

    _job_id_stage_id_idx = models.Index("(job_id, stage_id) WHERE active IS TRUE")

    @api.constrains("talent_pool_ids", "pool_applicant_id")
    def _check_talent_pool_required(self):
        for talent in self:
            if talent.pool_applicant_id == talent and not talent.talent_pool_ids:
                raise ValidationError(self.env._("Talent must belong to at least one Talent Pool."))

    @api.depends("email_normalized", "partner_phone_sanitized", "linkedin_profile", "pool_applicant_id.talent_pool_ids")
    def _compute_talent_pool_count(self):
        """
        This method will find the amount of talent pools the current application is associated with.
        An application can either be associated directly with a talent pool through talent_pool_ids
        and/or pool_applicant_id.talent_pool_ids or indirectly by having the same email, phone
        number or linkedin as a directly linked application.
        """
        pool_applicants = self.filtered("is_applicant_in_pool")
        (self - pool_applicants).talent_pool_count = 0

        if not pool_applicants:
            return

        directly_linked = pool_applicants.filtered("pool_applicant_id")
        for applicant in directly_linked:
            # All talents(applications with talent_pool_ids set) have a pool_applicant_id set to
            # themselves which is the reason we only look for that instead of searching for all
            # applications with talent_pool_ids and all applications with pool_applicant_id seperately
            applicant.talent_pool_count = len(applicant.pool_applicant_id.talent_pool_ids)

        indirectly_linked = pool_applicants - directly_linked
        if not indirectly_linked:
            return

        all_emails = {a.email_normalized for a in indirectly_linked if a.email_normalized}
        all_phones = {a.partner_phone_sanitized for a in indirectly_linked if a.partner_phone_sanitized}
        all_linkedins = {a.linkedin_profile for a in indirectly_linked if a.linkedin_profile}

        epl_domain = Domain.FALSE
        if all_emails:
            epl_domain |= Domain("email_normalized", "in", list(all_emails))
        if all_phones:
            epl_domain |= Domain("partner_phone_sanitized", "in", list(all_phones))
        if all_linkedins:
            epl_domain |= Domain("linkedin_profile", "in", list(all_linkedins))

        pool_domain = Domain(["|", ("talent_pool_ids", "!=", False), ("pool_applicant_id", "!=", False)])
        domain = pool_domain & epl_domain
        in_pool_applicants = self.env["hr.applicant"].with_context(active_test=True).search(domain)

        in_pool_emails = defaultdict(int)
        in_pool_phones = defaultdict(int)
        in_pool_linkedins = defaultdict(int)

        for applicant in in_pool_applicants:
            talent_pool_count = len(applicant.pool_applicant_id.talent_pool_ids)
            if applicant.email_normalized:
                in_pool_emails[applicant.email_normalized] = talent_pool_count
            if applicant.partner_phone_sanitized:
                in_pool_phones[applicant.partner_phone_sanitized] = talent_pool_count
            if applicant.linkedin_profile:
                in_pool_linkedins[applicant.linkedin_profile] = talent_pool_count

        for applicant in indirectly_linked:
            if applicant.email_from and in_pool_emails[applicant.email_normalized]:
                applicant.talent_pool_count = in_pool_emails[applicant.email_normalized]
            elif applicant.partner_phone_sanitized and in_pool_phones[applicant.partner_phone_sanitized]:
                applicant.talent_pool_count = in_pool_phones[applicant.partner_phone_sanitized]
            elif applicant.linkedin_profile and in_pool_linkedins[applicant.linkedin_profile]:
                applicant.talent_pool_count = in_pool_linkedins[applicant.linkedin_profile]
            else:
                applicant.talent_pool_count = 0

    @api.depends("partner_phone")
    def _compute_partner_phone_sanitized(self):
        for applicant in self:
            applicant.partner_phone_sanitized = (
                applicant._phone_format(fname="partner_phone") or applicant.partner_phone
            )

    def _update_partner_phone_email(self):
        for applicant in self:
            if not applicant.partner_id:
                continue
            applicant.email_from = applicant.partner_id.email
            if not applicant.partner_phone:
                applicant.partner_phone = applicant.partner_id.phone

    def _generate_related_partner(self):
        for applicant in self:
            email_normalized = tools.email_normalize(applicant.email_from or '')
            if not email_normalized:
                continue
            if not applicant.partner_id:
                if not applicant.partner_name:
                    raise UserError(_("You must define a Contact Name for this applicant."))
                applicant.partner_id = applicant._partner_find_from_emails_single(
                    [applicant.email_from], no_create=False,
                    additional_values={
                        email_normalized: {'lang': self.env.lang}
                    },
                )
            if applicant.partner_name and not applicant.partner_id.name:
                applicant.partner_id.name = applicant.partner_name
            if email_normalized and not applicant.partner_id.email:
                applicant.partner_id.email = applicant.email_from
            if applicant.partner_phone and not applicant.partner_id.phone:
                applicant.partner_id.phone = applicant.partner_phone

    @api.depends("email_normalized", "partner_phone_sanitized", "linkedin_profile")
    def _compute_application_count(self):
        """
        This method will calculate the number of applications that are either
        directly or indirectly linked to the current application(s)
        - An application is considered directly linked if it shares the same
          pool_applicant_id
        - An application is considered indirectly_linked if it has the same
          value as the current application(s) in any of the following field:
          email, phone number or linkedin

        Note: If self has pool_applicant_id, email, phone number or linkedin set
        this method will include self in the returned count
        """
        all_emails = {a.email_normalized for a in self if a.email_normalized}
        all_phones = {a.partner_phone_sanitized for a in self if a.partner_phone_sanitized}
        all_linkedins = {a.linkedin_profile for a in self if a.linkedin_profile}
        all_pool_applicants = {a.pool_applicant_id.id for a in self if a.pool_applicant_id}

        domain = Domain.FALSE
        if all_emails:
            domain |= Domain("email_normalized", "in", list(all_emails))
        if all_phones:
            domain |= Domain("partner_phone_sanitized", "in", list(all_phones))
        if all_linkedins:
            domain |= Domain("linkedin_profile", "in", list(all_linkedins))
        if all_pool_applicants:
            domain |= Domain("pool_applicant_id", "in", list(all_pool_applicants))

        domain &= Domain("talent_pool_ids", "=", False)
        matching_applicants = self.env["hr.applicant"].with_context(active_test=False).search(domain)

        email_map = defaultdict(set)
        phone_map = defaultdict(set)
        linkedin_map = defaultdict(set)
        pool_applicant_map = defaultdict(set)
        for app in matching_applicants:
            if app.email_normalized:
                email_map[app.email_normalized].add(app.id)
            if app.partner_phone_sanitized:
                phone_map[app.partner_phone_sanitized].add(app.id)
            if app.linkedin_profile:
                linkedin_map[app.linkedin_profile].add(app.id)
            if app.pool_applicant_id:
                pool_applicant_map[app.pool_applicant_id].add(app.id)

        for applicant in self:
            related_ids = set()
            if applicant.email_normalized:
                related_ids.update(email_map.get(applicant.email_normalized, set()))
            if applicant.partner_phone_sanitized:
                related_ids.update(phone_map.get(applicant.partner_phone_sanitized, set()))
            if applicant.linkedin_profile:
                related_ids.update(linkedin_map.get(applicant.linkedin_profile, set()))
            if applicant.pool_applicant_id:
                related_ids.update(pool_applicant_map.get(applicant.pool_applicant_id, set()))

            count = len(related_ids)

            applicant.application_count = max(0, count)

    @api.depends("talent_pool_ids")
    def _compute_is_pool(self):
        for applicant in self:
            applicant.is_pool_applicant = applicant.talent_pool_ids

    def _get_similar_applicants_domain(self, ignore_talent=False, only_talent=False):
        """
        This method returns a domain for the applicants whitch match with the
        current applicant according to email_from, partner_phone or linkedin_profile.
        Thus, search on the domain will return the current applicant as well
        if any of the following fields are filled.

        Args:
            ignore_talent: if you want the domain to only include applicants not belonging to a talent pool
            only_talent: if you want the domain to only include applicants belonging to a talent pool

        Returns:
            Domain()
        """
        domain = Domain.AND([
            Domain('company_id', 'in', self.mapped('company_id.id')),
            Domain.OR([
                Domain("id", "in", self.ids),
                Domain("email_normalized", "in", [email for email in self.mapped("email_normalized") if email]),
                Domain("partner_phone_sanitized", "in", [phone for phone in self.mapped("partner_phone_sanitized") if phone]),
                Domain("linkedin_profile", "in", [linkedin_profile for linkedin_profile in self.mapped("linkedin_profile") if linkedin_profile]),
            ])
        ])
        if ignore_talent:
            domain &= Domain("talent_pool_ids", "=", False)
        if only_talent:
            domain &= Domain("talent_pool_ids", "!=", False)
        return domain

    @api.depends(
        "talent_pool_ids", "pool_applicant_id", "email_normalized", "partner_phone_sanitized", "linkedin_profile"
    )
    def _compute_is_applicant_in_pool(self):
        """
        Computes if an application is linked to a talent pool or not.
        An application can either be directly or indirectly linked to a talent pool.
        Direct link:
            - 1. Application has talent_pool_ids set, meaning this application
                is a talent pool application, or talent for short.
            - 2. Application has pool_applicant_id set, meaning this application
            is a copy or directly linked to a talent (scenario 1)

        Indirect link:
            - 3. Application shares a phone number, email, or linkedin with a
                direclty linked application.

        Note: While possible, linking an application to a pool through linking
        it to an indirect link is currently excluded from the implementation
        for technical reasons.
        """
        direct = self.filtered(lambda a: a.talent_pool_ids or a.pool_applicant_id)
        direct.is_applicant_in_pool = True
        indirect = self - direct

        if not indirect:
            return

        all_emails = {a.email_normalized for a in indirect if a.email_normalized}
        all_phones = {a.partner_phone_sanitized for a in indirect if a.partner_phone_sanitized}
        all_linkedins = {a.linkedin_profile for a in indirect if a.linkedin_profile}

        epl_domain = Domain.FALSE
        if all_emails:
            epl_domain |= Domain("email_normalized", "in", list(all_emails))
        if all_phones:
            epl_domain |= Domain("partner_phone_sanitized", "in", list(all_phones))
        if all_linkedins:
            epl_domain |= Domain("linkedin_profile", "in", list(all_linkedins))

        pool_domain = Domain(["|", ("talent_pool_ids", "!=", False), ("pool_applicant_id", "!=", False)])
        domain = pool_domain & epl_domain
        in_pool_applicants = self.env["hr.applicant"].with_context(active_test=True).search(domain)
        in_pool_data = {"emails": set(), "phones": set(), "linkedins": set()}

        for applicant in in_pool_applicants:
            if applicant.email_normalized:
                in_pool_data["emails"].add(applicant.email_normalized)
            if applicant.partner_phone_sanitized:
                in_pool_data["phones"].add(applicant.partner_phone_sanitized)
            if applicant.linkedin_profile:
                in_pool_data["linkedins"].add(applicant.linkedin_profile)

        for applicant in indirect:
            applicant.is_applicant_in_pool = (
                applicant.email_normalized in in_pool_data["emails"]
                or applicant.partner_phone_sanitized in in_pool_data["phones"]
                or applicant.linkedin_profile in in_pool_data["linkedins"]
            )

    def _search_is_applicant_in_pool(self, operator, value):
        """
        This function is needed to hide duplicates when adding applicants/talents to a talent pool.
        All applications that have either talent_pool_ids or pool_applicant_id set are considered
        directly in a pool. Furthermore, any application with the same phone number, email or linkedin
        as the first applications, that are directly in the pool, are also considered to belong to
        the same talent pool.

        Returns:
            returns a domain with ids of applications that are either directly or indirectly linked to a pool
        """
        if operator != 'in':
            return NotImplemented

        return [('id', 'in', SQL("""
                WITH talent_pool_applicants AS (
                    SELECT
                           a.id as id,
                           email_normalized,
                           partner_phone_sanitized,
                           linkedin_profile
                      FROM hr_applicant a
                 LEFT JOIN hr_applicant_hr_talent_pool_rel rel
                        ON a.id = rel.hr_applicant_id
                     WHERE pool_applicant_id IS NOT NULL
                        OR hr_talent_pool_id IS NOT NULL
                )
                SELECT a.id
                FROM hr_applicant a
                WHERE
                    -- Check if directly linked to a pool
                    (a.id IN (
                        SELECT DISTINCT id
                        from talent_pool_applicants
                    ))
                    OR
                    -- Check if email matches any talent pool applicant
                    (a.email_normalized IN (
                        SELECT DISTINCT email_normalized
                        FROM talent_pool_applicants
                        WHERE email_normalized IS NOT NULL
                    ))
                    OR
                    -- Check if phone matches any talent pool applicant
                    (a.partner_phone_sanitized IN (
                        SELECT DISTINCT partner_phone_sanitized
                        FROM talent_pool_applicants
                        WHERE partner_phone_sanitized IS NOT NULL
                    ))
                    OR
                    -- Check if LinkedIn profile matches any talent pool applicant
                    (a.linkedin_profile IN (
                        SELECT DISTINCT linkedin_profile
                        FROM talent_pool_applicants
                        WHERE linkedin_profile IS NOT NULL
                    ))
        """))]

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
        if operator != 'in':
            return NotImplemented

        domains = []
        # Map statuses to domain filters
        if 'refused' in value:
            domains.append([('active', '=', True), ('refuse_reason_id', '!=', None)])
        if 'hired' in value:
            domains.append([('active', '=', True), ('date_closed', '!=', False)])
        if 'archived' in value or False in value:
            domains.append([('active', '=', False)])
        if 'ongoing' in value:
            domains.append([('active', '=', True), ('date_closed', '=', False)])

        return Domain.OR(domains)

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
        job_id = self.env.context.get('default_job_id')
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

    def copy_data(self, default=None):
        vals_list = super().copy_data(default=default)

        # Avoid adding `(copy)` to partner_name when an applicant is created trough the talent pool mechanism
        if not self.env.context.get("no_copy_in_partner_name"):
            vals_list = [
                dict(vals, partner_name=self.env._("%s (copy)", applicant.partner_name))
                for applicant, vals in zip(self, vals_list)
            ]
        return vals_list

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
                    model_description="Applicant",
                )
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

        self._generate_related_partner()

        for applicant in self:
            if applicant.pool_applicant_id and applicant != applicant.pool_applicant_id and (not applicant.is_pool_applicant):
                if 'email_from' in vals:
                    applicant.pool_applicant_id.email_from = vals['email_from']
                if 'partner_phone' in vals:
                    applicant.pool_applicant_id.partner_phone = vals['partner_phone']
                if 'linkedin_profile' in vals:
                    applicant.pool_applicant_id.linkedin_profile = vals['linkedin_profile']
                if 'type_id' in vals:
                    applicant.pool_applicant_id.type_id = vals['type_id']

        if 'interviewer_ids' in vals:
            interviewers_to_clean = old_interviewers - self.interviewer_ids
            interviewers_to_clean._remove_recruitment_interviewers()
            self.sudo().interviewer_ids._create_recruitment_interviewers()

            new_interviewers = self.interviewer_ids - old_interviewers - self.env.user
            if new_interviewers:
                for applicant in self:
                    notification_subject = _("You have been assigned as an interviewer for %s", applicant.display_name)
                    notification_body = _("You have been assigned as an interviewer for the Applicant %s", applicant.partner_name)
                    applicant.message_notify(
                        res_id=applicant.id,
                        model=applicant._name,
                        partner_ids=new_interviewers.partner_id.ids,
                        author_id=self.env.user.partner_id.id,
                        email_from=self.env.user.email_formatted,
                        subject=notification_subject,
                        body=notification_body,
                        email_layout_xmlid="mail.mail_notification_layout",
                        model_description="Applicant",
                    )
        return res

    @api.model
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
            'help_title': _("No applications found."),
        }

        if hr_job.alias_email:
            nocontent_body += Markup('<p class="o_copy_paste_email oe_view_nocontent_alias">%(helper_email)s <a href="mailto:%(email)s">%(email)s</a></p>') % {
                'helper_email': _("Send applications to"),
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
        return {
            'name': _('Employee'),
            'type': 'ir.actions.act_window',
            'res_model': 'hr.employee',
            'view_mode': 'form',
            'res_id': self.employee_id.id,
        }

    def action_open_applications(self):
        self.ensure_one()
        similar_applicants = (
            self.env["hr.applicant"]
            .with_context(active_test=False)
            .search(
                self._get_similar_applicants_domain(ignore_talent=True),
            )
        )
        return {
            "name": _("Applications"),
            "type": "ir.actions.act_window",
            "res_model": "hr.applicant",
            "view_mode": "list,form",
            "domain": [("id", "in", similar_applicants.ids)],
            "context": {
                "active_test": False,
                "search_default_stage": 1,
                "default_applicant_ids": self.ids,
                "no_create_application_button": True,
            },
        }

    def action_talent_pool_stat_button(self):
        self.ensure_one()
        # If the applicant has other applications linked to pool but for some
        # reason this applicant is not linked to that account then link it
        if not self.pool_applicant_id:
            self.link_applicant_to_talent()
        return {
            "type": "ir.actions.act_window",
            "res_model": "hr.applicant",
            "view_mode": "form",
            "target": "current",
            "res_id": self.pool_applicant_id.id,
        }

    def link_applicant_to_talent(self):
        talent = self.env["hr.applicant"].search(domain=self._get_similar_applicants_domain(only_talent=True))
        self.pool_applicant_id = talent

    def action_talent_pool_add_applicants(self):
        return {
            "name": _("Add applicant(s) to the pool"),
            "type": "ir.actions.act_window",
            "res_model": "talent.pool.add.applicants",
            "target": "new",
            "views": [[False, "form"]],
            "context": {
                "is_modal": True,
                "dialog_size": "medium",
                "default_talent_pool_ids": self.env.context.get(
                    "default_talent_pool_ids"
                )
                or [],
                "default_applicant_ids": self.ids,
            },
        }

    def action_job_add_applicants(self):
        return {
            "name": _("Create Applications"),
            "type": "ir.actions.act_window",
            "res_model": "job.add.applicants",
            "target": "new",
            "views": [[False, "form"]],
            "context": {
                "is_modal": True,
                "dialog_size": "medium",
                "default_applicant_ids": self.ids
                or self.env.context.get("default_applicant_ids"),
            },
        }

    def _track_template(self, changes):
        res = super()._track_template(changes)
        applicant = self[0]
        # When applcant is unarchived, they are put back to the default stage automatically. In this case,
        # don't post automated message related to the stage change.
        if 'stage_id' in changes and applicant.exists()\
            and applicant.stage_id.template_id\
            and not applicant.env.context.get('just_moved')\
            and not applicant.env.context.get('just_unarchived'):
            res['stage_id'] = (applicant.stage_id.template_id, {
                'auto_delete_keep_log': False,
                'subtype_id': self.env['ir.model.data']._xmlid_to_res_id('mail.mt_note'),
                'email_layout_xmlid': 'hr_recruitment.mail_notification_light_without_background'
            })
        return res

    def _creation_subtype(self):
        self.ensure_one()
        if self.is_pool_applicant:
            return self.env.ref('hr_recruitment.mt_talent_new', raise_if_not_found=False)
        return self.env.ref('hr_recruitment.mt_applicant_new')

    def _track_subtype(self, init_values):
        record = self[0]
        if 'stage_id' in init_values and record.stage_id:
            return self.env.ref('hr_recruitment.mt_applicant_stage_changed')
        return super()._track_subtype(init_values)

    def _notify_get_reply_to(self, default=None, author_id=False):
        """ Override to set alias of applicants to their job definition if any. """
        aliases = self.mapped('job_id')._notify_get_reply_to(default=default, author_id=author_id)
        res = {app.id: aliases.get(app.job_id.id) for app in self}
        leftover = self.filtered(lambda rec: not rec.job_id)
        if leftover:
            res.update(super(HrApplicant, leftover)._notify_get_reply_to(default=default, author_id=author_id))
        return res

    def _get_customer_information(self):
        email_keys_to_values = super()._get_customer_information()

        for applicant in self:
            email_key = tools.email_normalize(applicant.email_from) or applicant.email_from
            # do not fill Falsy with random data, unless monorecord (= always correct)
            if not email_key and len(self) > 1:
                continue
            email_keys_to_values.setdefault(email_key, {}).update({
                'name': applicant.partner_name or tools.parse_contact_from_email(applicant.email_from)[0] or applicant.email_from,
                'phone': applicant.partner_phone,
            })
        return email_keys_to_values

    @api.depends('partner_name')
    @api.depends_context('show_partner_name')
    def _compute_display_name(self):
        if not self.env.context.get('show_partner_name'):
            return super()._compute_display_name()
        for applicant in self:
            applicant.display_name = applicant.partner_name

    @api.model
    def message_new(self, msg_dict, custom_values=None):
        # Remove default author when going through the mail gateway. Indeed, we
        # do not want to explicitly set user_id to False; however we do not
        # want the gateway user to be responsible if no other responsible is
        # found.
        self = self.with_context(default_user_id=False)
        stage = False
        if custom_values and 'job_id' in custom_values:
            job = self.env['hr.job'].browse(custom_values['job_id'])
            stage = job._get_first_stage()

        partner_name, email_from_normalized = tools.parse_contact_from_email(msg_dict.get('from'))

        defaults = {
            'partner_name': partner_name,
        }
        job_platform = self.env['hr.job.platform'].search([('email', '=', email_from_normalized)], limit=1)

        if msg_dict.get('from') and not job_platform:
            defaults['email_from'] = msg_dict.get('from')
            defaults['partner_id'] = msg_dict.get('author_id', False)
        if msg_dict.get('email_from') and job_platform:
            subject_pattern = re.compile(job_platform.regex or '')
            regex_results = re.findall(subject_pattern, msg_dict.get('subject')) + re.findall(subject_pattern, msg_dict.get('body'))
            defaults['partner_name'] = regex_results[0] if regex_results else partner_name
            del msg_dict['email_from']
        if msg_dict.get('priority'):
            defaults['priority'] = msg_dict.get('priority')
        if stage and stage.id:
            defaults['stage_id'] = stage.id
        if custom_values:
            defaults.update(custom_values)
        res = super().message_new(msg_dict, custom_values=defaults)
        res._update_partner_phone_email()
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
        employee = self.env['hr.employee'].with_context(clean_context(self.env.context)).create(self._get_employee_create_vals())
        action['res_id'] = employee.id
        employee_attachments = self.env['ir.attachment'].search([('res_model', '=','hr.employee'), ('res_id', '=', employee.id)])
        unique_attachments = self.attachment_ids.filtered(
            lambda attachment: attachment.datas not in employee_attachments.mapped('datas')
        )
        unique_attachments.copy({'res_model': 'hr.employee', 'res_id': employee.id})
        employee.write({
            'job_id': self.job_id.id,
            'job_title': self.job_id.name,
            'department_id': self.department_id.id,
            'work_email': self.department_id.company_id.email or self.email_from, # To have a valid email address by default
            'work_phone': self.department_id.company_id.phone,
        })
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
            'work_email': self.department_id.company_id.email or self.email_from,  # To have a valid email address by default
            'work_phone': self.department_id.company_id.phone,
            'applicant_ids': self.ids,
            'phone': self.partner_phone
        }

    def _check_interviewer_access(self):
        if self.env.user.has_group('hr_recruitment.group_hr_recruitment_interviewer') and not self.env.user.has_group('hr_recruitment.group_hr_recruitment_user'):
            raise UserError(_('You are not allowed to perform this action.'))

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

    def action_archive(self):
        return super(HrApplicant, self.with_context(just_unarchived=True)).action_archive()

    def action_unarchive(self):
        res = super(HrApplicant, self.with_context(just_unarchived=True)).action_unarchive()
        self.reset_applicant()
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
