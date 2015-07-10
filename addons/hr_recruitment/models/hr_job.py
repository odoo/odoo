# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp.osv import fields, osv


class hr_job(osv.osv):
    _inherit = "hr.job"
    _name = "hr.job"
    _inherits = {'mail.alias': 'alias_id'}

    def _track_subtype(self, cr, uid, ids, init_values, context=None):
        record = self.browse(cr, uid, ids[0], context=context)
        if 'state' in init_values and record.state == 'open':
            return 'hr_recruitment.mt_job_new'
        return super(hr_job, self)._track_subtype(cr, uid, ids, init_values, context=context)

    def _get_attached_docs(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        attachment_obj = self.pool.get('ir.attachment')
        for job_id in ids:
            applicant_ids = self.pool.get('hr.applicant').search(cr, uid, [('job_id', '=', job_id)], context=context)
            res[job_id] = attachment_obj.search(
                cr, uid, [
                    '|',
                    '&', ('res_model', '=', 'hr.job'), ('res_id', '=', job_id),
                    '&', ('res_model', '=', 'hr.applicant'), ('res_id', 'in', applicant_ids)
                ], context=context)
        return res

    def _count_all(self, cr, uid, ids, field_name, arg, context=None):
        Applicant = self.pool['hr.applicant']
        return {
            job_id: {
                'application_count': Applicant.search_count(cr,uid, [('job_id', '=', job_id)], context=context),
                'documents_count': len(self._get_attached_docs(cr, uid, [job_id], field_name, arg, context=context)[job_id])
            }
            for job_id in ids
        }

    _columns = {
        'survey_id': fields.many2one('survey.survey', 'Interview Form', help="Choose an interview form for this job position and you will be able to print/answer this interview from all applicants who apply for this job"),
        'alias_id': fields.many2one('mail.alias', 'Alias', ondelete="restrict", required=True,
                                    help="Email alias for this job position. New emails will automatically "
                                         "create new applicants for this job position."),
        'address_id': fields.many2one('res.partner', 'Job Location', help="Address where employees are working"),
        'application_ids': fields.one2many('hr.applicant', 'job_id', 'Applications'),
        'application_count': fields.function(_count_all, type='integer', string='Applications', multi=True),
        'manager_id': fields.related('department_id', 'manager_id', type='many2one', string='Department Manager', relation='hr.employee', readonly=True, store=True),
        'stage_ids': fields.many2many('hr.recruitment.stage', 'job_stage_rel', 'job_id', 'stage_id', 'Job Stages'),
        'document_ids': fields.function(_get_attached_docs, type='one2many', relation='ir.attachment', string='Applications'),
        'documents_count': fields.function(_count_all, type='integer', string='Documents', multi=True),
        'user_id': fields.many2one('res.users', 'Recruitment Responsible', track_visibility='onchange'),
        'color': fields.integer('Color Index'),
    }

    def _address_get(self, cr, uid, context=None):
        user = self.pool.get('res.users').browse(cr, uid, uid, context=context)
        return user.company_id.partner_id.id

    _defaults = {
        'address_id': _address_get,
    }

    def _auto_init(self, cr, context=None):
        """Installation hook to create aliases for all jobs and avoid constraint errors."""
        return self.pool.get('mail.alias').migrate_to_alias(cr, self._name, self._table, super(hr_job, self)._auto_init,
            'hr.applicant', self._columns['alias_id'], 'name', alias_prefix='job+', alias_defaults={'job_id': 'id'}, context=context)

    def create(self, cr, uid, vals, context=None):
        create_context = dict(context,
            alias_model_name='hr.applicant',
            mail_create_nolog=True,
            alias_parent_model_name=self._name)
        job_id = super(hr_job, self).create(cr, uid, vals, context=create_context)
        job = self.browse(cr, uid, job_id, context=context)
        self.pool.get('mail.alias').write(cr, uid, [job.alias_id.id], {'alias_parent_thread_id': job_id, "alias_defaults": {'job_id': job_id}}, context)
        return job_id

    def unlink(self, cr, uid, ids, context=None):
        # Cascade-delete mail aliases as well, as they should not exist without the job position.
        mail_alias = self.pool.get('mail.alias')
        alias_ids = [job.alias_id.id for job in self.browse(cr, uid, ids, context=context) if job.alias_id]
        res = super(hr_job, self).unlink(cr, uid, ids, context=context)
        mail_alias.unlink(cr, uid, alias_ids, context=context)
        return res

    def action_print_survey(self, cr, uid, ids, context=None):
        job = self.browse(cr, uid, ids, context=context)[0]
        survey_id = job.survey_id.id
        return self.pool.get('survey.survey').action_print_survey(cr, uid, [survey_id], context=context)

    def action_get_attachment_tree_view(self, cr, uid, ids, context=None):
        #open attachments of job and related applicantions.
        model, action_id = self.pool.get('ir.model.data').get_object_reference(cr, uid, 'base', 'action_attachment')
        action = self.pool.get(model).read(cr, uid, action_id, context=context)
        applicant_ids = self.pool.get('hr.applicant').search(cr, uid, [('job_id', 'in', ids)], context=context)
        action['context'] = {'default_res_model': self._name, 'default_res_id': ids[0]}
        action['domain'] = str(['|', '&', ('res_model', '=', 'hr.job'), ('res_id', 'in', ids), '&', ('res_model', '=', 'hr.applicant'), ('res_id', 'in', applicant_ids)])
        return action

    def action_set_no_of_recruitment(self, cr, uid, id, value, context=None):
        return self.write(cr, uid, [id], {'no_of_recruitment': value}, context=context)