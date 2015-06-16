# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp import SUPERUSER_ID
from openerp.osv import fields, osv


class hr_applicant_settings(osv.TransientModel):
    _name = 'hr.recruitment.config.settings'
    _inherit = ['res.config.settings', 'fetchmail.config.settings']

    _columns = {
        'module_document': fields.boolean('Allow the automatic indexation of resumes',
            help='Manage your CV\'s and motivation letter related to all applicants.\n'
                 '-This installs the module document_ftp. This will install the knowledge management  module in order to allow you to search using specific keywords through  the content of all documents (PDF, .DOCx...)'),
        'alias_prefix': fields.char('Default Alias Name for Jobs'),
        'alias_domain': fields.char('Alias Domain'),
    }

    _defaults = {
        'alias_domain': lambda self, cr, uid, context: self.pool["ir.config_parameter"].get_param(cr, uid, "mail.catchall.domain", context),
    }

    def _find_default_job_alias_id(self, cr, uid, context=None):
        alias_id = self.pool['ir.model.data'].xmlid_to_res_id(cr, uid, 'hr_recruitment.mail_alias_jobs')
        if not alias_id:
            alias_ids = self.pool['mail.alias'].search(
                cr, uid, [
                    ('alias_model_id.model', '=', 'hr.applicant'),
                    ('alias_force_thread_id', '=', False),
                    ('alias_parent_model_id.model', '=', 'hr.job'),
                    ('alias_parent_thread_id', '=', False),
                    ('alias_defaults', '=', '{}')
                ], context=context)
            alias_id = alias_ids and alias_ids[0] or False
        return alias_id

    def get_default_alias_prefix(self, cr, uid, ids, context=None):
        alias_name = False
        alias_id = self._find_default_job_alias_id(cr, uid, context=context)
        if alias_id:
            alias_name = self.pool['mail.alias'].browse(cr, uid, alias_id, context=context).alias_name
        return {'alias_prefix': alias_name}

    def set_default_alias_prefix(self, cr, uid, ids, context=None):
        mail_alias = self.pool.get('mail.alias')
        for record in self.browse(cr, uid, ids, context=context):
            alias_id = self._find_default_job_alias_id(cr, uid, context=context)
            if not alias_id:
                create_ctx = dict(context, alias_model_name='hr.applicant', alias_parent_model_name='hr.job')
                alias_id = self.pool['mail.alias'].create(cr, uid, {'alias_name': record.alias_prefix}, context=create_ctx)
            else:
                mail_alias.write(cr, uid, alias_id, {'alias_name': record.alias_prefix}, context=context)
        return True
