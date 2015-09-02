# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp import api, fields, models


class RecruitmentSettings(models.TransientModel):
    _name = 'hr.recruitment.config.settings'
    _inherit = ['res.config.settings', 'fetchmail.config.settings']

    module_document = fields.Selection(selection=[
            (0, "Do not manage CVs and motivation letter"),
            (1, 'Allow the automatic indexation of resumes')
            ], string='Resumes',
            help='Manage your CV\'s and motivation letter related to all applicants.\n'
                            '-This installs the module document_ftp. This will install the knowledge management  module in order to allow you to search using specific keywords through  the content of all documents (PDF, .DOCx...)')
    alias_prefix = fields.Char(string='Default Alias Name for Jobs')
    alias_domain = fields.Char(string='Alias Domain',
                               default=lambda self: self.env["ir.config_parameter"].get_param("mail.catchall.domain"))

    @api.model
    def _find_default_job_alias_id(self):
        jobs_alias = self.env.ref('hr_recruitment.mail_alias_jobs')
        if not jobs_alias:
            aliases = self.env['mail.alias'].search([
                ('alias_model_id.model', '=', 'hr.applicant'),
                ('alias_force_thread_id', '=', False),
                ('alias_parent_model_id.model', '=', 'hr.job'),
                ('alias_parent_thread_id', '=', False),
                ('alias_defaults', '=', '{}')], limit=1)
            jobs_alias = aliases and aliases[0] or False
        return jobs_alias

    @api.multi
    def get_default_alias_prefix(self):
        alias = self._find_default_job_alias_id()
        return {'alias_prefix': alias and alias.alias_name or False}

    @api.multi
    def set_default_alias_prefix(self):
        for record in self:
            alias = self._find_default_job_alias_id()
            if not alias:
                alias = self.env['mail.alias'].with_context(alias_model_name='hr.applicant', alias_parent_model_name='hr.job').create({'alias_name': record.alias_prefix})
            else:
                alias.write({'alias_name': record.alias_prefix})
        return True
