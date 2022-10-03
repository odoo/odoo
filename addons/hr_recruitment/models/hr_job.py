# Part of Odoo. See LICENSE file for full copyright and licensing details.

import ast
from collections import defaultdict

from odoo import api, fields, models, SUPERUSER_ID, _


class Job(models.Model):
    _name = "hr.job"
    _inherit = ["mail.alias.mixin", "hr.job"]
    _order = "sequence, name asc"

    @api.model
    def _default_address_id(self):
        return self.env.company.partner_id

    def _get_default_favorite_user_ids(self):
        return [(6, 0, [self.env.uid])]

    address_id = fields.Many2one(
        'res.partner', "Job Location", default=_default_address_id,
        domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]",
        help="Address where employees are working")
    application_ids = fields.One2many('hr.applicant', 'job_id', "Job Applications")
    application_count = fields.Integer(compute='_compute_application_count', string="Application Count")
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
    user_id = fields.Many2one('res.users', "Recruiter", domain="[('share', '=', False), ('company_ids', 'in', company_id)]", tracking=True)
    hr_responsible_id = fields.Many2one(
        'res.users', "HR Responsible", tracking=True,
        help="Person responsible of validating the employee's contracts.")
    document_ids = fields.One2many('ir.attachment', compute='_compute_document_ids', string="Documents")
    documents_count = fields.Integer(compute='_compute_document_ids', string="Document Count")
    alias_id = fields.Many2one(
        'mail.alias', "Alias", ondelete="restrict", required=True,
        help="Email alias for this job position. New emails will automatically create new applicants for this job position.")
    color = fields.Integer("Color Index")
    is_favorite = fields.Boolean(compute='_compute_is_favorite', inverse='_inverse_is_favorite')
    favorite_user_ids = fields.Many2many('res.users', 'job_favorite_user_rel', 'job_id', 'user_id', default=_get_default_favorite_user_ids)
    interviewer_ids = fields.Many2many('res.users', string='Interviewers', domain="[('share', '=', False), ('company_ids', 'in', company_id)]")
    extended_interviewer_ids = fields.Many2many('res.users', 'hr_job_extended_interviewer_res_users', compute='_compute_extended_interviewer_ids', store=True)

    activities_overdue = fields.Integer(compute='_compute_activities')
    activities_today = fields.Integer(compute='_compute_activities')

    @api.depends_context('uid')
    def _compute_activities(self):
        self.env.cr.execute("""
            SELECT
                app.job_id,
                COUNT(*) AS act_count,
                CASE
                    WHEN %(today)s::date - act.date_deadline::date = 0 THEN 'today'
                    WHEN %(today)s::date - act.date_deadline::date > 0 THEN 'overdue'
                END AS act_state
             FROM mail_activity act
             JOIN hr_applicant app ON app.id = act.res_id
             JOIN hr_recruitment_stage sta ON app.stage_id = sta.id
            WHERE act.user_id = %(user_id)s AND act.res_model = 'hr.applicant'
              AND act.date_deadline <= %(today)s::date AND app.active
              AND app.job_id IN %(job_ids)s
              AND sta.hired_stage IS NOT TRUE
            GROUP BY app.job_id, act_state
        """, {
            'today': fields.Date.context_today(self),
            'user_id': self.env.uid,
            'job_ids': tuple(self.ids),
        })
        job_activities = defaultdict(dict)
        for activity in self.env.cr.dictfetchall():
            job_activities[activity['job_id']][activity['act_state']] = activity['act_count']
        for job in self:
            job.activities_overdue = job_activities[job.id].get('overdue', 0)
            job.activities_today = job_activities[job.id].get('today', 0)

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
        applicants = self.mapped('application_ids').filtered(lambda self: not self.emp_id)
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
        ], ['job_id'], ['job_id'])
        result = dict((data['job_id'][0], data['job_id_count']) for data in read_group_result)
        for job in self:
            job.all_application_count = result.get(job.id, 0)

    def _compute_application_count(self):
        read_group_result = self.env['hr.applicant']._read_group([('job_id', 'in', self.ids)], ['job_id'], ['job_id'])
        result = dict((data['job_id'][0], data['job_id_count']) for data in read_group_result)
        for job in self:
            job.application_count = result.get(job.id, 0)

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
              GROUP BY s.job_id
            """, [tuple(self.ids), ]
        )

        new_applicant_count = dict(self.env.cr.fetchall())
        for job in self:
            job.new_application_count = new_applicant_count.get(job.id, 0)

    def _compute_applicant_hired(self):
        hired_stages = self.env['hr.recruitment.stage'].search([('hired_stage', '=', True)])
        hired_data = self.env['hr.applicant']._read_group([
            ('job_id', 'in', self.ids),
            ('stage_id', 'in', hired_stages.ids),
        ], ['job_id'], ['job_id'])
        job_hires = {data['job_id'][0]: data['job_id_count'] for data in hired_data}
        for job in self:
            job.applicant_hired = job_hires.get(job.id, 0)

    @api.depends('application_count', 'new_application_count')
    def _compute_old_application_count(self):
        for job in self:
            job.old_application_count = job.application_count - job.new_application_count

    def _alias_get_creation_values(self):
        values = super(Job, self)._alias_get_creation_values()
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
            vals['favorite_user_ids'] = vals.get('favorite_user_ids', []) + [(4, self.env.uid)]
        jobs = super().create(vals_list)
        utm_linkedin = self.env.ref("utm.utm_source_linkedin", raise_if_not_found=False)
        if utm_linkedin:
            source_vals = [{
                'source_id': utm_linkedin.id,
                'job_id': job.id,
            } for job in jobs]
            self.env['hr.recruitment.source'].create(source_vals)
        jobs.sudo().interviewer_ids._create_recruitment_interviewers()
        return jobs

    def write(self, vals):
        old_interviewers = self.interviewer_ids
        if 'active' in vals and not vals['active']:
            self.application_ids.active = False
        res = super().write(vals)
        if 'interviewer_ids' in vals:
            interviewers_to_clean = old_interviewers - self.interviewer_ids
            interviewers_to_clean._remove_recruitment_interviewers()
            self.sudo().interviewer_ids._create_recruitment_interviewers()

        # Since the alias is created upon record creation, the default values do not reflect the current values unless
        # specifically rewritten
        # List of fields to keep synched with the alias
        alias_fields = {'department_id', 'user_id'}
        if any(field for field in alias_fields if field in vals):
            for job in self:
                alias_default_vals = job._alias_get_creation_values().get('alias_defaults', '{}')
                job.alias_defaults = alias_default_vals
        return res

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
            'view_mode': 'tree,form',
            'views': [
                (self.env.ref('hr_recruitment.ir_attachment_hr_recruitment_list_view').id, 'tree'),
                (False, 'form'),
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
        return action

    def action_open_late_activities(self):
        action = self.action_open_activities()
        action['context'] = {
            'default_job_id': self.id,
            'search_default_job_id': self.id,
            'search_default_activities_overdue': True,
            'search_default_running_applicant_activities': True,
        }
        return action

    def action_open_today_activities(self):
        action = self.action_open_activities()
        action['context'] = {
            'default_job_id': self.id,
            'search_default_job_id': self.id,
            'search_default_activities_today': True,
        }
        return action

    def close_dialog(self):
        return {'type': 'ir.actions.act_window_close'}

    def edit_dialog(self):
        form_view = self.env.ref('hr.view_hr_job_form')
        return {
            'name': _('Job'),
            'res_model': 'hr.job',
            'res_id': self.id,
            'views': [(form_view.id, 'form'),],
            'type': 'ir.actions.act_window',
            'target': 'inline'
        }
