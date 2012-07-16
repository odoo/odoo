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

from osv import osv
from osv import fields
from tools.translate import _
import tools


def _reopen(self, id, res_id, model):
    return {'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'view_type': 'form',
            'res_id': res_id,
            'res_model': self._name,
            'target': 'new',

            # save original model in context, otherwise
            # it will be lost on the action's context switch
            'context': {'mail.compose.target.model': model,
                        'active_id': res_id,
                        'active_ids': [res_id],
                        'active_model': model,
                        }
    }

class mail_compose_message(osv.osv_memory):
    _inherit = 'mail.compose.message'

    def _get_templates(self, cr, uid, context=None):
        """
        Return Email Template of particular  Model.
        """
        if context is None:
            context = {}
        record_ids = []
        email_template= self.pool.get('email.template')
        model = False
        if context.get('message_id'):
            mail_message = self.pool.get('mail.message')
            message_data = mail_message.browse(cr, uid, int(context.get('message_id')), context)
            model = message_data.model
        elif context.get('mail.compose.target.model') or context.get('active_model'):
            model = context.get('mail.compose.target.model', context.get('active_model'))
        if model:
            record_ids = email_template.search(cr, uid, [('model', '=', model)])
            return email_template.name_get(cr, uid, record_ids, context) + [(False,'')]
        return []

    _columns = {
        'use_template': fields.boolean('Use Template'),
        'template_id': fields.selection(_get_templates, 'Template',
                                        size=-1 # means we want an int db column
                                        ),
    }
    
    _defaults = {
        'template_id' : lambda self, cr, uid, context={} : context.get('mail.compose.template_id', False)          
    }

    def on_change_template(self, cr, uid, ids, use_template, template_id, email_from=None, email_to=None, context=None):
        if context is None:
            context = {}
        values = {}
        if template_id:
            res_id = context.get('active_id', False)
            if context.get('mail.compose.message.mode') == 'mass_mail':
                # use the original template values - to be rendered when actually sent
                # by super.send_mail()
                values = self.pool.get('email.template').read(cr, uid, template_id, self.fields_get_keys(cr, uid), context)
            else:
                # render the mail as one-shot
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
        else:
            # restore defaults
            values = self.default_get(cr, uid, self.fields_get_keys(cr, uid), context)
            values.update(use_template=use_template, template_id=template_id)

        return {'value': values}


    def template_toggle(self, cr, uid, ids, context=None):
        for record in self.browse(cr, uid, ids, context=context):
            had_template = record.use_template
            print had_template
            record.write({'use_template': not(had_template)})
            if had_template:
                # equivalent to choosing an empty template
                onchange_defaults = self.on_change_template(cr, uid, record.id, not(had_template),
                                                            False, email_from=record.email_from,
                                                            email_to=record.email_to, context=context)
                print onchange_defaults
                record.write(onchange_defaults['value'])
            return _reopen(self, record.id, record.res_id, record.model)

    def save_as_template(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        email_template = self.pool.get('email.template')
        model_pool = self.pool.get('ir.model')
        for record in self.browse(cr, uid, ids, context=context):
            model = record.model or context.get('active_model')
            model_ids = model_pool.search(cr, uid, [('model', '=', model)])
            model_id = model_ids and model_ids[0] or False
            model_name = ''
            if model_id:
                model_name = model_pool.browse(cr, uid, model_id, context=context).name
            template_name = "%s: %s" % (model_name, tools.ustr(record.subject))
            values = {
                'name': template_name,
                'email_from': record.email_from or False,
                'subject': record.subject or False,
                'body_text': record.body_text or False,
                'email_to': record.email_to or False,
                'email_cc': record.email_cc or False,
                'email_bcc': record.email_bcc or False,
                'reply_to': record.reply_to or False,
                'model_id': model_id or False,
                'attachment_ids': [(6, 0, [att.id for att in record.attachment_ids])]
            }
            template_id = email_template.create(cr, uid, values, context=context)
            record.write({'template_id': template_id,
                          'use_template': True})

        # _reopen same wizard screen with new template preselected
        return _reopen(self, record.id, record.res_id, record.model)

    # override the basic implementation 
    def render_template(self, cr, uid, template, model, res_id, context=None):
        return self.pool.get('email.template').render_template(cr, uid, template, model, res_id, context=context)

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
