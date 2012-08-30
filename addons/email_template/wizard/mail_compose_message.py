# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
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

import base64
import tools

from osv import osv
from osv import fields
from tools.translate import _

class mail_compose_message(osv.osv_memory):
    """ Inherit mail_compose_message to add email template feature in the
        message composer. """

    _inherit = 'mail.compose.message'

    def _get_templates(self, cr, uid, context=None):
        """ Return Email Template of particular  Model. """
        if context is None:
            context = {}
        model = False
        email_template_obj= self.pool.get('email.template')

        if context.get('default_composition_mode') == 'reply' and context.get('active_id'):
            message_data = self.pool.get('mail.message').browse(cr, uid, int(context.get('active_id')), context)
            if message_data:
                model = message_data.model
        else:
            model = context.get('default_model', context.get('active_model'))

        if model:
            record_ids = email_template_obj.search(cr, uid, [('model', '=', model)], context=context)
            return email_template_obj.name_get(cr, uid, record_ids, context) + [(False, '')]
        return []

    def default_get(self, cr, uid, fields, context=None):
        """ Override to handle templates. """
        if context is None:
            context = {}
        result = super(mail_compose_message, self).default_get(cr, uid, fields, context=context)
        result['template_id'] = context.get('default_template_id', context.get('mail.compose.template_id', False))
        return result

    _columns = {
        'use_template': fields.boolean('Use Template'),
        # incredible hack of the day: size=-1 means we want an int db column instead of an str one
        'template_id': fields.selection(_get_templates, 'Template', size=-1),
    }

    def onchange_template_id(self, cr, uid, ids, use_template, template_id, composition_mode, res_id, context=None):
        """ onchange_template_id: read or render the template if set, get back
            to default values if not. """
        fields = ['body', 'body_html', 'subject', 'partner_ids', 'email_to', 'email_cc']
        if use_template and template_id:
            # use the original template values, to be rendered when actually sent
            if composition_mode == 'mass_mail':
                values = self.pool.get('email.template').read(cr, uid, template_id, fields, context)
            # render the mail as one-shot
            else:
                values = self.pool.get('email.template').generate_email(cr, uid, template_id, res_id, context=context)
                # retrofit generated attachments in the expected field format
                if values['attachments']:
                    attachment = values.pop('attachments')
                    attachment_obj = self.pool.get('ir.attachment')
                    att_ids = []
                    for fname, fcontent in attachment.iteritems():
                        data_attach = {
                            'name': fname,
                            'datas': fcontent,
                            'datas_fname': fname,
                            'description': fname,
                            'res_model' : self._name,
                            'res_id' : ids[0] if ids else False
                        }
                        att_ids.append(attachment_obj.create(cr, uid, data_attach))
                    values['attachment_ids'] = att_ids
        else: # restore defaults
            values = self.default_get(cr, uid, fields, context=context)

        if values.get('body_html') is not None:
            values['body'] = values.get('body_html')
        values.update(use_template=use_template, template_id=template_id)

        return {'value': values}

    def toggle_template(self, cr, uid, ids, context=None):
        """ hit toggle template mode button: calls onchange_use_template to 
            emulate an on_change, then writes the value to update the form. """
        for record in self.browse(cr, uid, ids, context=context):
            onchange_res = self.onchange_use_template(cr, uid, ids, not record.use_template, context=context)['value']
            record.write(onchange_res)
        return True

    def onchange_use_template(self, cr, uid, ids, use_template, template_id, composition_mode, res_id, context=None):
        """ onchange_use_template (values: True or False).  If use_template is
            False, we do like an onchange with template_id False for values """
        onchange_template_values = self.onchange_template_id(cr, uid, ids, use_template,
            template_id, composition_mode, res_id, context=context)
        return onchange_template_values

    def save_as_template(self, cr, uid, ids, context=None):
        """ hit save as template button: current form value will be a new
            template attached to the current document. """
        email_template = self.pool.get('email.template')
        ir_model_pool = self.pool.get('ir.model')
        for record in self.browse(cr, uid, ids, context=context):
            model = record.model
            model_ids = ir_model_pool.search(cr, uid, [('model', '=', model)])
            model_id = model_ids and model_ids[0] or False
            model_name = ''
            if model_id:
                model_name = ir_model_pool.browse(cr, uid, model_id, context=context).name
            template_name = "%s: %s" % (model_name, tools.ustr(record.subject))
            values = {
                'name': template_name,
                'subject': record.subject or False,
                'body': record.body or False,
                'model_id': model_id or False,
                'attachment_ids': [(6, 0, [att.id for att in record.attachment_ids])]
            }
            template_id = email_template.create(cr, uid, values, context=context)
            record.write({'template_id': template_id, 'use_template': True})
        return True

    def render_template(self, cr, uid, template, model, res_id, context=None):
        """ Override of mail.compose.message behavior: use the power of
            templates ! """
        return self.pool.get('email.template').render_template(cr, uid, template, model, res_id, context=context)

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
