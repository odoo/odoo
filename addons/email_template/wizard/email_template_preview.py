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

from openerp.osv import fields, osv

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
        model =  self.pool[template_object.model]
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
        'res_id': fields.selection(_get_records, 'Sample Document'),
        'partner_ids': fields.many2many('res.partner', string='Recipients'),
    }

    def on_change_res_id(self, cr, uid, ids, res_id, context=None):
        if context is None:
            context = {'value': {}}
        if not res_id or not context.get('template_id'):
            return {'value': {}}

        email_template = self.pool.get('email.template')
        template_id = context.get('template_id')
        template = email_template.browse(cr, uid, template_id, context=context)

        # generate and get template values
        mail_values = email_template.generate_email(cr, uid, template_id, res_id, context=context)
        vals = dict((field, mail_values.get(field, False)) for field in ('email_from', 'email_to', 'email_cc', 'reply_to', 'subject', 'body_html', 'partner_to', 'partner_ids', 'attachment_ids'))
        vals['name'] = template.name
        return {'value': vals}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
