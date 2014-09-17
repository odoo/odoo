# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Business Applications
#    Copyright (C) 2004-Today OpenERP S.A. (<http://openerp.com>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from openerp import SUPERUSER_ID
from openerp.osv import fields, osv


class hr_applicant_settings(osv.TransientModel):
    _name = 'hr.config.settings'
    _inherit = ['hr.config.settings', 'fetchmail.config.settings']

    _columns = {
        'module_document': fields.boolean('Allow the automatic indexation of resumes',
            help='Manage your CV\'s and motivation letter related to all applicants.\n'
                 '-This installs the module document_ftp. This will install the knowledge management  module in order to allow you to search using specific keywords through  the content of all documents (PDF, .DOCx...)'),
        'alias_prefix': fields.char('Default Alias Name for Jobs'),
        'alias_domain': fields.char('Alias Domain'),
    }

    _defaults = {
        'alias_domain': lambda self, cr, uid, context: self.pool['mail.alias']._get_alias_domain(cr, SUPERUSER_ID, [1], None, None)[1],
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
