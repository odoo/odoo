# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2009 Sharoon Thomas
#    Copyright (C) 2010-Today OpenERP SA (<http://www.openerp.com>)
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>
#
##############################################################################

from osv import osv, fields

class email_template_preview(osv.osv_memory):
    _inherit = "email.template"
    _name = "email_template.preview"
    _description = "Email Template Preview"

    def _get_records(self, cr, uid, context=None):
        """
        Return Records of particular Email Template's Model
        """
        if context is None:
            context = {}

        template_id = context.get('template_id', False)
        if not template_id:
            return []
        email_template = self.pool.get('email.template')
        template = email_template.browse(cr, uid, int(template_id), context=context)
        template_object = template.model_id
        model =  self.pool.get(template_object.model)
        record_ids = model.search(cr, uid, [], 0, 10, 'id', context=context)
        default_id = context.get('default_res_id')

        if default_id and default_id not in record_ids:
            record_ids.insert(0, default_id)

        return model.name_get(cr, uid, record_ids, context)


    def default_get(self, cr, uid, fields, context=None):
        if context is None:
            context = {}
        result = super(email_template_preview, self).default_get(cr, uid, fields, context=context)

        email_template = self.pool.get('email.template')
        template_id = context.get('template_id')
        if 'res_id' in fields and not result.get('res_id'):
            records = self._get_records(cr, uid, context=context)
            result['res_id'] = records and records[0][0] or False # select first record as a Default
        if template_id and 'model_id' in fields and not result.get('model_id'):
            result['model_id'] = email_template.read(cr, uid, int(template_id), ['model_id'], context).get('model_id', False)
        return result

    _columns = {
        'res_id':fields.selection(_get_records, 'Sample Document'),
    }

    def on_change_res_id(self, cr, uid, ids, res_id, context=None):
        if not res_id:
            return {}
        vals = {}
        email_template = self.pool.get('email.template')
        template_id = context and context.get('template_id')
        template = email_template.get_email_template(cr, uid, template_id=template_id, record_id=res_id, context=context)
        model = template.model
        vals['email_to'] = self.render_template(cr, uid, template.email_to, model, res_id, context)
        vals['email_cc'] = self.render_template(cr, uid, template.email_cc, model, res_id, context)
        vals['reply_to'] = self.render_template(cr, uid, template.reply_to, model, res_id, context)
        vals['subject'] = self.render_template(cr, uid, template.subject, model, res_id, context)
        description = self.render_template(cr, uid, template.body, model, res_id, context) or ''
        if template.user_signature:
            signature = self.pool.get('res.users').browse(cr, uid, uid, context).signature
            description += '\n' + signature
        vals['body'] = description
        if template.body_html:
            vals['body_html'] = self.render_template(cr, uid, template.body_html, model, res_id, context) or ''
        vals['report_name'] = self.render_template(cr, uid, template.report_name, model, res_id, context)
        return {'value': vals}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
