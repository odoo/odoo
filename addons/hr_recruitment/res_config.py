# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Business Applications
#    Copyright (C) 2004-2012 OpenERP S.A. (<http://openerp.com>).
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

from openerp.osv import fields, osv

class hr_applicant_settings(osv.osv_memory):
    _name = 'hr.config.settings'
    _inherit = ['hr.config.settings', 'fetchmail.config.settings']

    _columns = {
        'module_document': fields.boolean('Allow the automatic indexation of resumes',
            help='Manage your CV\'s and motivation letter related to all applicants.\n'
                 '-This installs the module document_ftp. This will install the knowledge management  module in order to allow you to search using specific keywords through  the content of all documents (PDF, .DOCx...)'),
        'fetchmail_applicants': fields.boolean('Create applicants from an incoming email account',
            fetchmail_model='hr.applicant', fetchmail_name='Incoming HR Applications',   
            help='Allow applicants to send their job application to an email address (jobs@mycompany.com), '
                 'and create automatically application documents in the system.'),
        'alias_prefix': fields.char('Default Alias Name for Jobs'),
        'alias_domain' : fields.char('Alias Domain'),
    }

    _defaults = {
        'alias_domain': lambda self, cr, uid, context:self.pool.get("ir.config_parameter").get_param(cr, uid, "mail.catchall.domain", context=context),
    }

    def get_default_alias_prefix(self, cr, uid, ids, context=None):
        alias_name = ''
        mail_alias = self.pool.get('mail.alias')
        try:
            alias_name = self.pool.get('ir.model.data').get_object(cr, uid, 'hr_recruitment', 'mail_alias_jobs').alias_name
        except Exception:
            model_ids = self.pool.get('ir.model').search(cr, uid, [('model', '=', 'hr.applicant')], context=context)
            alias_ids = mail_alias.search(cr, uid, [('alias_model_id', '=', model_ids[0]),('alias_defaults', '=', '{}')], context=context)
            if alias_ids:
                alias_name = mail_alias.browse(cr, uid, alias_ids[0], context=context).alias_name
        return {'alias_prefix': alias_name}

    def set_default_alias_prefix(self, cr, uid, ids, context=None):
        mail_alias = self.pool.get('mail.alias')
        record = self.browse(cr, uid, ids[0], context=context)
        default_alias_prefix = self.get_default_alias_prefix(cr, uid, ids, context=context)['alias_prefix']
        if record.alias_prefix != default_alias_prefix:
            try:
                alias = self.pool.get('ir.model.data').get_object(cr, uid, 'hr_recruitment', 'mail_alias_jobs')
                if alias:
                    alias.write({'alias_name': record.alias_prefix})
            except Exception:
                model_ids = self.pool.get('ir.model').search(cr, uid, [('model', '=', 'hr.applicant')], context=context)
                alias_ids = mail_alias.search(cr, uid, [('alias_model_id', '=', model_ids[0]),('alias_defaults', '=', '{}')], context=context)
                if alias_ids:
                    mail_alias.write(cr, uid, alias_ids[0], {'alias_name': record.alias_prefix}, context=context)
                else:
                    mail_alias.create_unique_alias(cr, uid, {'alias_name': record.alias_prefix}, model_name="hr.applicant", context=context)
        return True
