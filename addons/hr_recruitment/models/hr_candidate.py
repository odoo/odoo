# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict

from odoo.addons.hr_recruitment.models.hr_applicant import AVAILABLE_PRIORITIES

from odoo import api, models, fields, SUPERUSER_ID, tools, _
from odoo.exceptions import UserError
from odoo.osv import expression


class HrCandidate(models.Model):
    _name = "hr.candidate"
    _description = "Candidate"
    _inherit = ['mail.thread.cc',
               'mail.thread.main.attachment',
               'mail.thread.blacklist',
               'mail.thread.phone',
               'mail.activity.mixin',
    ]
    _order = "priority desc, availability asc, id desc"
    _mailing_enabled = True
    _primary_email = 'email_from'
    _rec_name = 'partner_name'

    active = fields.Boolean("Active", default=True, index=True)
    company_id = fields.Many2one('res.company', "Company", default=lambda self: self.env.company)
    applicant_ids = fields.One2many('hr.applicant', 'candidate_id')
    application_count = fields.Integer(compute="_compute_application_count")
    partner_id = fields.Many2one('res.partner', "Contact", copy=False, index='btree_not_null')
    partner_name = fields.Char("Candidates's Name")
    email_from = fields.Char(
        string="Email",
        size=128,
        compute='_compute_partner_phone_email',
        inverse='_inverse_partner_email',
        store=True,
        index='trigram')
    email_normalized = fields.Char(index='trigram')  # inherited via mail.thread.blacklist
    partner_phone = fields.Char(
        string="Phone",
        size=32,
        compute='_compute_partner_phone_email',
        inverse='_inverse_partner_email',
        store=True,
        index='btree_not_null')
    partner_phone_sanitized = fields.Char(
        string='Sanitized Phone Number',
        compute='_compute_partner_phone_sanitized',
        store=True,
        index='btree_not_null')
    linkedin_profile = fields.Char('LinkedIn Profile')
    type_id = fields.Many2one('hr.recruitment.degree', "Degree")
    availability = fields.Date("Availability", help="The date at which the applicant will be available to start working", tracking=True)
    categ_ids = fields.Many2many('hr.applicant.category', string="Tags")
    color = fields.Integer("Color Index", default=0)
    priority = fields.Selection(AVAILABLE_PRIORITIES, string="Evaluation", compute="_compute_priority", store=True)
    user_id = fields.Many2one(
        'res.users',
        string="Candidate Manager",
        default=lambda self: self.env.user if self.env.user.id != SUPERUSER_ID else False,
        domain="[('share', '=', False), ('company_ids', 'in', company_id)]",
        tracking=True)
    employee_id = fields.Many2one('hr.employee', string="Employee", help="Employee linked to the candidate.", copy=False)
    emp_is_active = fields.Boolean(string="Employee Active", related='employee_id.active')
    employee_name = fields.Char(related='employee_id.name', string="Employee Name", readonly=False, tracking=False)

    similar_candidates_count = fields.Integer(
        compute='_compute_similar_candidates_count',
        help='Candidates with the same email or phone or mobile')
    applications_count = fields.Integer(string="# Offers", compute='_compute_applications_count')
    refused_applications_count = fields.Integer(string="# Refused Offers", compute='_compute_applications_count')
    accepted_applications_count = fields.Integer(string="# Accepted Offers", compute='_compute_applications_count')

    meeting_ids = fields.One2many('calendar.event', 'candidate_id', 'Meetings')
    meeting_display_text = fields.Char(compute='_compute_meeting_display')
    meeting_display_date = fields.Date(compute='_compute_meeting_display')
    attachment_count = fields.Integer(
        string="Number of Attachments",
        compute='_compute_attachment_count')
    candidate_properties = fields.Properties('Properties', definition='company_id.candidate_properties_definition', copy=True)
    attachment_ids = fields.One2many('ir.attachment', 'res_id', domain=[('res_model', '=', 'hr.candidate')], string='Attachments')

    def init(self):
        self.env.cr.execute("""
            CREATE INDEX IF NOT EXISTS hr_candidate_email_partner_phone_mobile
            ON hr_candidate(email_normalized, partner_phone_sanitized);
        """)

    @api.depends('partner_name')
    def _compute_display_name(self):
        for candidate in self:
            candidate.display_name = candidate.partner_name or candidate.partner_id.name

    @api.depends('partner_phone')
    def _compute_partner_phone_sanitized(self):
        for candidate in self:
            candidate.partner_phone_sanitized = candidate._phone_format(fname='partner_phone') or candidate.partner_phone

    @api.depends('partner_id')
    def _compute_partner_phone_email(self):
        for candidate in self:
            if not candidate.partner_id:
                continue
            candidate.email_from = candidate.partner_id.email
            if not candidate.partner_phone:
                candidate.partner_phone = candidate.partner_id.phone
    
    def _phone_get_number_fields(self):
        return ['partner_phone']

    def _inverse_partner_email(self):
        for candidate in self:
            if not candidate.email_from:
                continue
            if not candidate.partner_id:
                if not candidate.partner_name:
                    raise UserError(_('You must define a Contact Name for this candidate.'))
                contact_email_normalized = tools.email_normalize(candidate.email_from)
                contact_name_email = tools.formataddr((candidate.partner_name, contact_email_normalized))
                candidate.partner_id = self.env['res.partner'].with_context(default_lang=self.env.lang).find_or_create(contact_name_email)
            if candidate.partner_name and not candidate.partner_id.name:
                candidate.partner_id.name = candidate.partner_name
            if tools.email_normalize(candidate.email_from) != tools.email_normalize(candidate.partner_id.email):
                # change email on a partner will trigger other heavy code, so avoid to change the email when
                # it is the same. E.g. "email@example.com" vs "My Email" <email@example.com>""
                candidate.partner_id.email = candidate.email_from
            if candidate.partner_phone:
                candidate.partner_id.phone = candidate.partner_phone

    @api.depends('email_from', 'partner_phone_sanitized')
    def _compute_similar_candidates_count(self):
        """
            The field similar_candidates_count is only used on the form view.
            Thus, using ORM rather then querying, should not make much
            difference in terms of performance, while being more readable and secure.
        """
        if not any(self._ids):
            for candidate in self:
                domain = candidate._get_similar_candidates_domain()
                if domain:
                    candidate.similar_candidates_count = max(0, self.env["hr.candidate"].with_context(active_test=False).search_count(domain) - 1)
                else:
                    candidate.similar_candidates_count = 0
            return
        self.flush_recordset(['email_normalized', 'partner_phone_sanitized'])
        self.env.cr.execute("""
            SELECT
                id,
                (
                    SELECT COUNT(*)
                    FROM hr_candidate AS sub
                    WHERE c.id != sub.id
                     AND ((coalesce(c.email_normalized, '') <> '' AND sub.email_normalized = c.email_normalized)
                       OR (coalesce(c.partner_phone_sanitized, '') <> '' AND c.partner_phone_sanitized = sub.partner_phone_sanitized))
                      AND c.company_id = sub.company_id
                ) AS similar_candidates
            FROM hr_candidate AS c
            WHERE id IN %(ids)s
        """, {'ids': tuple(self._origin.ids)})
        query_results = self.env.cr.dictfetchall()
        mapped_data = {result['id']: result['similar_candidates'] for result in query_results}
        for candidate in self:
            candidate.similar_candidates_count = mapped_data.get(candidate.id, 0)

    def _get_similar_candidates_domain(self):
        """
            This method returns a domain for the applicants whitch match with the
            current candidate according to email_from, partner_phone.
            Thus, search on the domain will return the current candidate as well if any of
            the following fields are filled.
        """
        self.ensure_one()
        if not self:
            return []
        domain = [('id', 'in', self.ids)]
        if self.email_normalized:
            domain = expression.OR([domain, [('email_normalized', '=', self.email_normalized)]])
        if self.partner_phone_sanitized:
            domain = expression.OR([domain, [('partner_phone_sanitized', '=', self.partner_phone_sanitized)]])
        domain = expression.AND([domain, [('company_id', '=', self.company_id.id)]])
        return domain

    def _compute_attachment_count(self):
        read_group_res = self.env['ir.attachment']._read_group(
            [('res_model', '=', 'hr.candidate'), ('res_id', 'in', self.ids)],
            ['res_id'], ['__count'])
        attach_data = dict(read_group_res)
        for candidate in self:
            candidate.attachment_count = attach_data.get(candidate.id, 0)

    def _compute_application_count(self):
        read_group_res = self.env['hr.applicant'].with_context(active_test=False)._read_group(
            [('candidate_id', 'in', self.ids)],
            ['candidate_id'], ['__count'])
        application_data = dict(read_group_res)
        for candidate in self:
            candidate.application_count = application_data.get(candidate, 0)

    @api.depends('applicant_ids.priority')
    def _compute_priority(self):
        for candidate in self:
            if not candidate.applicant_ids:
                candidate.priority = "0"
            else:
                candidate.priority = str(round(sum(int(a.priority) for a in candidate.applicant_ids) / len(candidate.applicant_ids)))

    def _compute_applications_count(self):
        result = defaultdict(lambda: {"total": 0, "refused": 0, "accepted": 0})
        for applicant in self.with_context(active_test=False).applicant_ids:
            result[applicant.candidate_id.id]["total"] += 1
            if applicant.application_status == "refused":
                result[applicant.candidate_id.id]["refused"] += 1
            elif applicant.application_status == "hired":
                result[applicant.candidate_id.id]["accepted"] += 1
        for candidate in self:
            candidate.applications_count = result[candidate.id]['total']
            candidate.refused_applications_count = result[candidate.id]['refused']
            candidate.accepted_applications_count = result[candidate.id]['accepted']

    @api.depends_context('lang')
    @api.depends('meeting_ids', 'meeting_ids.start')
    def _compute_meeting_display(self):
        candidate_with_meetings = self.filtered('meeting_ids')
        (self - candidate_with_meetings).update({
            'meeting_display_text': _('No Meeting'),
            'meeting_display_date': ''
        })
        today = fields.Date.today()
        for candidate in candidate_with_meetings:
            count = len(candidate.meeting_ids)
            dates = candidate.meeting_ids.mapped('start')
            min_date, max_date = min(dates).date(), max(dates).date()
            if min_date >= today:
                candidate.meeting_display_date = min_date
            else:
                candidate.meeting_display_date = max_date
            if count == 1:
                candidate.meeting_display_text = _('1 Meeting')
            elif candidate.meeting_display_date >= today:
                candidate.meeting_display_text = _('Next Meeting')
            else:
                candidate.meeting_display_text = _('Last Meeting')

    def write(self, vals):
        res = super().write(vals)

        if vals.get("company_id") and not self.env.context.get('do_not_propagate_company', False):
            self.applicant_ids.with_context(do_not_propagate_company=True).write({"company_id": vals["company_id"]})
        return res

    def action_open_similar_candidates(self):
        self.ensure_one()
        domain = self._get_similar_candidates_domain()
        similar_candidates = self.env['hr.candidate'].with_context(active_test=False).search(domain)
        return {
            'type': 'ir.actions.act_window',
            'name': _('Similar Candidates'),
            'res_model': self._name,
            'view_mode': 'list,kanban,form,activity',
            'domain': [('id', 'in', similar_candidates.ids)],
            'context': {
                'active_test': False,
            },
        }

    def action_open_applications(self):
        self.ensure_one()
        return {
            'name': _('Applications'),
            'type': 'ir.actions.act_window',
            'res_model': 'hr.applicant',
            'view_mode': 'list,kanban,form,pivot,graph,calendar,activity',
            'domain': [('id', 'in', self.applicant_ids.ids)],
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
            'res_id': self.employee_id.id,
        }

    def action_create_meeting(self):
        """ This opens Meeting's calendar view to schedule meeting on current candidate
            @return: Dictionary value for created Meeting view
        """
        self.ensure_one()
        if not self.partner_id:
            if not self.partner_name:
                raise UserError(_('You must define a Contact Name for this candidate.'))
            self.partner_id = self.env['res.partner'].create({
                'is_company': False,
                'name': self.partner_name,
                'email': self.email_from,
            })

        partners = self.partner_id
        if self.env.user.has_group('hr_recruitment.group_hr_recruitment_interviewer') and not self.env.user.has_group('hr_recruitment.group_hr_recruitment_user'):
            partners |= self.env.user.partner_id
        else:
            partners |= self.user_id.partner_id

        res = self.env['ir.actions.act_window']._for_xml_id('calendar.action_calendar_event')
        # As we are redirected from the hr.candidate, calendar checks rules on "hr.applicant",
        # in order to decide whether to allow creation of a meeting.
        # As interviewer does not have create right on the hr.applicant, in order to allow them
        # to create a meeting for an applicant, we pass 'create': True to the context.
        res['context'] = {
            'create': True,
            'default_candidate_id': self.id,
            'default_partner_ids': partners.ids,
            'default_user_id': self.env.uid,
            'default_name': self.partner_name,
            'attachment_ids': self.attachment_ids.ids
        }
        return res

    @api.ondelete(at_uninstall=False)
    def _unlink_except_linked_employee(self):
        if self.employee_id:
            raise UserError(_("The candidate is linked to an employee, to avoid losing information, archive it instead."))

    def create_employee_from_candidate(self):
        self.ensure_one()
        self._check_interviewer_access()

        if not self.partner_id:
            if not self.partner_name:
                raise UserError(_('Please provide an candidate name.'))
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
            'private_street': address_sudo.street,
            'private_street2': address_sudo.street2,
            'private_city': address_sudo.city,
            'private_state_id': address_sudo.state_id.id,
            'private_zip': address_sudo.zip,
            'private_country_id': address_sudo.country_id.id,
            'private_phone': address_sudo.phone,
            'private_email': address_sudo.email,
            'lang': address_sudo.lang,
            'address_id': self.company_id.partner_id.id,
            'candidate_id': self.ids,
            'phone': self.partner_phone
        }

    def _check_interviewer_access(self):
        if self.env.user.has_group('hr_recruitment.group_hr_recruitment_interviewer') and not self.env.user.has_group('hr_recruitment.group_hr_recruitment_user'):
            raise UserError(_('You are not allowed to perform this action.'))

    def action_open_attachments(self):
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'ir.attachment',
            'name': _('Documents'),
            'context': {
                'default_res_model': 'hr.candidate',
                'default_res_id': self.ids[0],
                'show_partner_name': 1,
            },
            'view_mode': 'list,form',
            'views': [
                (self.env.ref('hr_recruitment.ir_attachment_hr_recruitment_list_view').id, 'list'),
                (False, 'form'),
            ],
            'search_view_id': self.env.ref('hr_recruitment.ir_attachment_view_search_inherit_hr_recruitment').ids,
            'domain': [('res_model', '=', 'hr.candidate'), ('res_id', 'in', self.ids)],
        }

    def action_send_email(self):
        return {
            'name': _('Send Email'),
            'type': 'ir.actions.act_window',
            'target': 'new',
            'view_mode': 'form',
            'res_model': 'candidate.send.mail',
            'context': {
                'default_candidate_ids': self.ids,
            }
        }
