# Part of Odoo. See LICENSE file for full copyright and licensing details.

import ast
from collections import defaultdict

from dateutil.relativedelta import relativedelta
from odoo import api, fields, models, SUPERUSER_ID, _
from odoo.tools import SQL
from odoo.tools.convert import convert_file


class HrJob(models.Model):
    _name = 'hr.job'
    _inherit = ["mail.alias.mixin", "hr.job", "mail.activity.mixin"]
    _order = "sequence, name asc"

    @api.model
    def _default_address_id(self):
        last_used_address = self.env['hr.job'].search([('company_id', 'in', self.env.companies.ids)], order='id desc', limit=1)
        if last_used_address:
            return last_used_address.address_id
        else:
            return self.env.company.partner_id

    def _address_id_domain(self):
        return ['|', '&', '&', ('type', '!=', 'contact'), ('type', '!=', 'private'),
                ('id', 'in', self.sudo().env.companies.partner_id.child_ids.ids),
                ('id', 'in', self.sudo().env.companies.partner_id.ids)]

    def _get_default_favorite_user_ids(self):
        return [(6, 0, [self.env.uid])]

    address_id = fields.Many2one(
        'res.partner', "Job Location", default=_default_address_id,
        domain=lambda self: self._address_id_domain(), tracking=True,
        help="Select the location where the applicant will work. Addresses listed here are defined on the company's contact information.")
    application_ids = fields.One2many('hr.applicant', 'job_id', "Job Applications")
    application_count = fields.Integer(compute='_compute_application_count', string="Application Count")
    open_application_count = fields.Integer(compute='_compute_open_application_count', string="Open Application Count",
                                            help="Number of applications that are still ongoing (not hired or refused)")
    all_application_count = fields.Integer(compute='_compute_all_application_count', string="All Application Count")
    new_application_count = fields.Integer(
        compute='_compute_new_application_count', string="New Application",
        help="Number of applications that are new in the flow (typically at first step of the flow)")
    old_application_count = fields.Integer(
        compute='_compute_old_application_count', string="Old Application")
    applicant_hired = fields.Integer(compute='_compute_applicant_hired', string="Applicants Hired")
    manager_id = fields.Many2one(
        'hr.employee', related='department_id.manager_id', string="Department Manager",
        readonly=True, store=True)
    user_id = fields.Many2one('res.users', "Recruiter",
        domain="[('share', '=', False), ('company_ids', 'in', company_id)]", default=lambda self: self.env.user,
        tracking=True, help="The Recruiter will be the default value for all Applicants in this job \
            position. The Recruiter is automatically added to all meetings with the Applicant.")
    document_ids = fields.One2many('ir.attachment', compute='_compute_document_ids', string="Documents", readonly=True)
    documents_count = fields.Integer(compute='_compute_document_ids', string="Document Count")
    employee_count = fields.Integer(compute='_compute_employee_count')
    alias_id = fields.Many2one(help="Email alias for this job position. New emails will automatically create new applicants for this job position.")
    color = fields.Integer("Color Index")
    is_favorite = fields.Boolean(compute='_compute_is_favorite', inverse='_inverse_is_favorite')
    favorite_user_ids = fields.Many2many('res.users', 'job_favorite_user_rel', 'job_id', 'user_id', default=_get_default_favorite_user_ids)
    interviewer_ids = fields.Many2many('res.users', string='Interviewers', domain="[('share', '=', False), ('company_ids', 'in', company_id)]", tracking=True, help="The Interviewers set on the job position can see all Applicants in it. They have access to the information, the attachments, the meeting management and they can refuse him. You don't need to have Recruitment rights to be set as an interviewer.")
    extended_interviewer_ids = fields.Many2many('res.users', 'hr_job_extended_interviewer_res_users', compute='_compute_extended_interviewer_ids', store=True)
    industry_id = fields.Many2one('res.partner.industry', 'Industry', tracking=True)
    currency_id = fields.Many2one("res.currency", related="company_id.currency_id", readonly=True)
    compensation = fields.Monetary(currency_field="currency_id")

    activity_count = fields.Integer(compute='_compute_activities')

    job_properties = fields.Properties('Properties', definition='company_id.job_properties_definition')

    applicant_properties_definition = fields.PropertiesDefinition('Applicant Properties')
    no_of_hired_employee = fields.Integer(
        compute='_compute_no_of_hired_employee',
        string='Hired', copy=False,
        help='Number of hired employees for this job position during recruitment phase.',
        store=True)

    job_source_ids = fields.One2many('hr.recruitment.source', 'job_id')

    @api.depends('application_ids.date_closed')
    def _compute_no_of_hired_employee(self):
        counts = dict(self.env['hr.applicant']._read_group(
            domain=[
                ('job_id', 'in', self.ids),
                ('date_closed', '!=', False),
                '|',
                    ('active', '=', False),
                    ('active', '=', True),
            ],
            groupby=['job_id'],
            aggregates=['__count']))
        for job in self:
            job.no_of_hired_employee = counts.get(job, 0)

    @api.depends_context('uid')
    def _compute_activities(self):
        self.env.cr.execute("""
            SELECT
                app.job_id,
                COUNT(*) AS act_count
             FROM mail_activity act
             JOIN hr_applicant app ON app.id = act.res_id
             JOIN hr_recruitment_stage sta ON app.stage_id = sta.id
            WHERE act.user_id = %(user_id)s AND act.res_model = 'hr.applicant'
              AND app.active
              AND app.job_id IN %(job_ids)s
              AND sta.hired_stage IS NOT TRUE
            GROUP BY app.job_id
        """, {
            'today': fields.Date.context_today(self),
            'user_id': self.env.uid,
            'job_ids': tuple(self.ids or [0]),
            # or [0] is used in case we only have newIds (web studio)
        })
        job_activities = defaultdict(dict)
        for activity in self.env.cr.dictfetchall():
            job_activities[activity['job_id']] = activity['act_count']
        for job in self:
            job.activity_count = job_activities[job.id]

    @api.depends('application_ids.interviewer_ids')
    def _compute_extended_interviewer_ids(self):
        # Use SUPERUSER_ID as the search_read is protected in hr_referral
        results_raw = self.env['hr.applicant'].with_user(SUPERUSER_ID).search_read([
            ('job_id', 'in', self.ids),
            ('interviewer_ids', '!=', False)
        ], ['interviewer_ids', 'job_id'])
        interviewers_by_job = defaultdict(set)
        for result_raw in results_raw:
            interviewers_by_job[result_raw['job_id'][0]] |= set(result_raw['interviewer_ids'])
        for job in self:
            job.extended_interviewer_ids = [(6, 0, list(interviewers_by_job[job.id]))]

    def _compute_is_favorite(self):
        for job in self:
            job.is_favorite = self.env.user in job.favorite_user_ids

    def _inverse_is_favorite(self):
        unfavorited_jobs = favorited_jobs = self.env['hr.job']
        for job in self:
            if self.env.user in job.favorite_user_ids:
                unfavorited_jobs |= job
            else:
                favorited_jobs |= job
        favorited_jobs.write({'favorite_user_ids': [(4, self.env.uid)]})
        unfavorited_jobs.write({'favorite_user_ids': [(3, self.env.uid)]})

    def _compute_document_ids(self):
        applicants = self.mapped('application_ids').filtered(lambda self: not self.employee_id)
        app_to_job = dict((applicant.id, applicant.job_id.id) for applicant in applicants)
        attachments = self.env['ir.attachment'].search([
            '|',
            '&', ('res_model', '=', 'hr.job'), ('res_id', 'in', self.ids),
            '&', ('res_model', '=', 'hr.applicant'), ('res_id', 'in', applicants.ids)])
        result = dict.fromkeys(self.ids, self.env['ir.attachment'])
        for attachment in attachments:
            if attachment.res_model == 'hr.applicant':
                result[app_to_job[attachment.res_id]] |= attachment
            else:
                result[attachment.res_id] |= attachment

        for job in self:
            job.document_ids = result.get(job.id, False)
            job.documents_count = len(job.document_ids)

    def _compute_all_application_count(self):
        read_group_result = self.env['hr.applicant'].with_context(active_test=False)._read_group([
            ('job_id', 'in', self.ids),
            '|',
                ('active', '=', True),
                '&',
                ('active', '=', False), ('refuse_reason_id', '!=', False),
        ], ['job_id'], ['__count'])
        result = {job.id: count for job, count in read_group_result}
        for job in self:
            job.all_application_count = result.get(job.id, 0)

    def _compute_application_count(self):
        read_group_result = self.env['hr.applicant']._read_group([('job_id', 'in', self.ids)], ['job_id'], ['__count'])
        result = {job.id: count for job, count in read_group_result}
        for job in self:
            job.application_count = result.get(job.id, 0)

    def _compute_open_application_count(self):
        hired_stages = self.env['hr.recruitment.stage'].search([('hired_stage', '=', True)])
        result = dict(self.env['hr.applicant']._read_group([
            ('job_id', 'in', self.ids),
            ('stage_id', 'not in', hired_stages.ids),
        ], ['job_id'], ['__count']))
        for job in self:
            job.open_application_count = result.get(job, 0)

    def _compute_employee_count(self):
        res = {
            job.id: count
            for job, count in self.env['hr.employee'].sudo()._read_group(
                domain=[
                    ('job_id', 'in', self.ids),
                ],
                groupby=['job_id'],
                aggregates=['__count'],
            )
        }
        for job in self:
            job.employee_count = res.get(job.id, 0)

    def _get_first_stage(self):
        self.ensure_one()
        return self.env['hr.recruitment.stage'].search([
            '|',
            ('job_ids', '=', False),
            ('job_ids', '=', self.id)], order='sequence asc', limit=1)

    def _compute_new_application_count(self):
        self.env.cr.execute(
            """
                WITH job_stage AS (
                    SELECT DISTINCT ON (j.id) j.id AS job_id, s.id AS stage_id, s.sequence AS sequence
                      FROM hr_job j
                 LEFT JOIN hr_job_hr_recruitment_stage_rel rel
                        ON rel.hr_job_id = j.id
                      JOIN hr_recruitment_stage s
                        ON s.id = rel.hr_recruitment_stage_id
                        OR s.id NOT IN (
                                        SELECT "hr_recruitment_stage_id"
                                          FROM "hr_job_hr_recruitment_stage_rel"
                                         WHERE "hr_recruitment_stage_id" IS NOT NULL
                                        )
                     WHERE j.id in %s
                  ORDER BY 1, 3 asc
                )
                SELECT s.job_id, COUNT(a.id) AS new_applicant
                  FROM hr_applicant a
                  JOIN job_stage s
                    ON s.job_id = a.job_id
                   AND a.stage_id = s.stage_id
                   AND a.active IS TRUE
                 WHERE a.company_id in %s
                    OR a.company_id is NULL
              GROUP BY s.job_id
            """, [tuple(self.ids or [0]), tuple(self.env.companies.ids)]
            # or [0] is used in case we only have newIds (web studio)
        )

        new_applicant_count = dict(self.env.cr.fetchall())
        for job in self:
            job.new_application_count = new_applicant_count.get(job.id, 0)

    def _compute_applicant_hired(self):
        hired_stages = self.env['hr.recruitment.stage'].search([('hired_stage', '=', True)])
        hired_data = self.env['hr.applicant']._read_group([
            ('job_id', 'in', self.ids),
            ('stage_id', 'in', hired_stages.ids),
        ], ['job_id'], ['__count'])
        job_hires = {job.id: count for job, count in hired_data}
        for job in self:
            job.applicant_hired = job_hires.get(job.id, 0)

    @api.depends('application_count', 'new_application_count')
    def _compute_old_application_count(self):
        for job in self:
            job.old_application_count = job.application_count - job.new_application_count

    def _alias_get_creation_values(self):
        values = super()._alias_get_creation_values()
        values['alias_model_id'] = self.env['ir.model']._get('hr.applicant').id
        if self.id:
            values['alias_defaults'] = defaults = ast.literal_eval(self.alias_defaults or "{}")
            defaults.update({
                'job_id': self.id,
                'department_id': self.department_id.id,
                'company_id': self.department_id.company_id.id if self.department_id else self.company_id.id,
                'user_id': self.user_id.id,
            })
        return values

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            vals["favorite_user_ids"] = vals.get("favorite_user_ids", [])
        jobs = super().create(vals_list)
        jobs.sudo().interviewer_ids._create_recruitment_interviewers()
        return jobs

    def write(self, vals):
        old_interviewers = self.interviewer_ids
        old_managers = {}
        old_recruiters = {}
        for job in self:
            old_managers[job] = job.manager_id
            old_recruiters[job] = job.user_id
        if 'active' in vals and not vals['active']:
            self.application_ids.active = False
        res = super().write(vals)
        if 'interviewer_ids' in vals:
            interviewers_to_clean = old_interviewers - self.interviewer_ids
            interviewers_to_clean._remove_recruitment_interviewers()
            self.sudo().interviewer_ids._create_recruitment_interviewers()

        # Subscribe the recruiter if it has changed.
        if "user_id" in vals:
            for job in self:
                to_unsubscribe = [
                    partner
                    for partner in old_recruiters[job].partner_id.ids
                    if partner not in job.manager_id._get_related_partners().ids
                ]
                job.message_unsubscribe(to_unsubscribe)
                application_ids = job.application_ids.filtered(
                    lambda x:
                        x.user_id == old_recruiters[job] and
                        x.application_status == 'ongoing'
                )
                if application_ids:
                    application_ids.message_unsubscribe(to_unsubscribe)
                    application_ids.with_context(mail_auto_subscribe_no_notify=True).user_id = job.user_id

        # Since the alias is created upon record creation, the default values do not reflect the current values unless
        # specifically rewritten
        # List of fields to keep synched with the alias
        alias_fields = {'department_id', 'user_id'}
        if any(field for field in alias_fields if field in vals):
            for job in self:
                alias_default_vals = job._alias_get_creation_values().get('alias_defaults', '{}')
                job.alias_defaults = alias_default_vals
        return res

    def _order_field_to_sql(self, alias, field_name, direction, nulls, query):
        if field_name == 'is_favorite':
            sql_field = SQL(
                "%s IN (SELECT job_id FROM job_favorite_user_rel WHERE user_id = %s)",
                SQL.identifier(alias, 'id'), self.env.uid,
            )
            return SQL("%s %s %s", sql_field, direction, nulls)

        return super()._order_field_to_sql(alias, field_name, direction, nulls, query)

    def _creation_subtype(self):
        return self.env.ref('hr_recruitment.mt_job_new')

    def action_open_attachments(self):
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'ir.attachment',
            'name': _('Documents'),
            'context': {
                'default_res_model': self._name,
                'default_res_id': self.ids[0],
                'show_partner_name': 1,
            },
            'view_mode': 'list',
            'views': [
                (self.env.ref('hr_recruitment.ir_attachment_hr_recruitment_list_view').id, 'list')
            ],
            'search_view_id': self.env.ref('hr_recruitment.ir_attachment_view_search_inherit_hr_recruitment').ids,
            'domain': ['|',
                '&', ('res_model', '=', 'hr.job'), ('res_id', 'in', self.ids),
                '&', ('res_model', '=', 'hr.applicant'), ('res_id', 'in', self.application_ids.ids),
            ],
        }

    def action_open_activities(self):
        action = self.env["ir.actions.actions"]._for_xml_id("hr_recruitment.action_hr_job_applications")
        views = ['activity'] + [view for view in action['view_mode'].split(',') if view != 'activity']
        action['view_mode'] = ','.join(views)
        action['views'] = [(False, view) for view in views]
        action['context'] = {
            'default_job_id': self.id,
            'search_default_job_id': self.id,
            'search_default_running_applicant_activities': True,
        }
        return action

    @api.model
    def _action_load_recruitment_scenario(self):

        convert_file(
            self.sudo().env,
            "hr_recruitment",
            "data/scenarios/hr_recruitment_scenario.xml",
            None,
            mode="init",
        )

        return {
            "type": "ir.actions.client",
            "tag": "reload",
        }

    def action_open_employees(self):
        self.ensure_one()
        if self.env['hr.employee'].has_access('read'):
            res_model = "hr.employee"
        else:
            res_model = "hr.employee.public"

        return {
            'name': _("Related Employees"),
            'type': 'ir.actions.act_window',
            'res_model': res_model,
            'view_mode': 'list,kanban,form',
            'views': [(False, 'list'), (False, 'kanban'), (False, 'form')],
            'context': {
                'default_job_id': self.id,
                'search_default_group_job': 1,
                'search_default_job_id': self.id,
                'expand': 1
            },
        }
