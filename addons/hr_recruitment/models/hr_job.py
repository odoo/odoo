# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp import _, api, fields, models


class Job(models.Model):
    _inherit = "hr.job"
    _name = "hr.job"
    _inherits = {'mail.alias': 'alias_id'}

    @api.model
    def _default_address_id(self):
        return self.env.user.company_id.partner_id

    address_id = fields.Many2one(
        'res.partner', "Job Location", default=_default_address_id,
        help="Address where employees are working")
    application_ids = fields.One2many('hr.applicant', 'job_id', "Applications")
    application_count = fields.Integer(compute='_compute_application_count', string="Applications")
    manager_id = fields.Many2one(
        'hr.employee', related='department_id.manager_id', string="Department Manager",
        readonly=True, store=True)
    user_id = fields.Many2one('res.users', "Recruitment Responsible", track_visibility='onchange')
    stage_ids = fields.Many2many(
        'hr.recruitment.stage', 'job_stage_rel', 'job_id', 'stage_id',
        'Job Stages',
        default=[(0, 0, {'name': _('New')})])
    document_ids = fields.One2many('ir.attachment', compute='_compute_document_ids', string="Applications")
    documents_count = fields.Integer(compute='_compute_document_ids', string="Documents")
    survey_id = fields.Many2one(
        'survey.survey', "Interview Form",
        help="Choose an interview form for this job position and you will be able to print/answer this interview from all applicants who apply for this job")
    alias_id = fields.Many2one(
        'mail.alias', "Alias", ondelete="restrict", required=True,
        help="Email alias for this job position. New emails will automatically create new applicants for this job position.")
    color = fields.Integer("Color Index")

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
            job.document_ids = result[job.id]
            job.documents_count = len(job.document_ids)

    @api.multi
    def _compute_application_count(self):
        read_group_result = self.env['hr.applicant'].read_group([('job_id', '=', self.id)], ['job_id'], ['job_id'])
        result = dict((data['job_id'][0], data['job_id_count']) for data in read_group_result)
        for job in self:
            job.application_count = result.get(job.id, 0)

    @api.model
    def create(self, vals):
        job = super(Job, self.with_context(alias_model_name='hr.applicant',
                                           mail_create_nolog=True,
                                           alias_parent_model_name=self._name)).create(vals)
        job.alias_id.write({'alias_parent_thread_id': job.id, "alias_defaults": {'job_id': job.id}})
        return job

    @api.multi
    def unlink(self):
        # Cascade-delete mail aliases as well, as they should not exist without the job position.
        aliases = self.mapped('alias_id')
        res = super(Job, self).unlink()
        aliases.unlink()
        return res

    def _auto_init(self, cr, context=None):
        """Installation hook to create aliases for all jobs and avoid constraint errors."""
        return self.pool.get('mail.alias').migrate_to_alias(
            cr, self._name, self._table, super(Job, self)._auto_init,
            'hr.applicant', self._columns['alias_id'], 'name',
            alias_prefix='job+', alias_defaults={'job_id': 'id'}, context=context)

    @api.multi
    def _track_subtype(self, init_values):
        if 'state' in init_values and self.state == 'open':
            return 'hr_recruitment.mt_job_new'
        return super(Job, self)._track_subtype(init_values)

    @api.multi
    def action_print_survey(self):
        return self.survey_id.action_print_survey()

    @api.multi
    def action_get_attachment_tree_view(self):
        action = self.env.ref('base.action_attachment').read()[0]
        action['context'] = {
            'default_res_model': self._name,
            'default_res_id': self.ids[0]
        }
        action['domain'] = ['|', '&', ('res_model', '=', 'hr.job'), ('res_id', 'in', self.ids), '&', ('res_model', '=', 'hr.applicant'), ('res_id', 'in', self.mapped('application_ids').ids)]
        return action

    @api.multi
    def action_set_no_of_recruitment(self, value):
        return self.write({'no_of_recruitment': value})
