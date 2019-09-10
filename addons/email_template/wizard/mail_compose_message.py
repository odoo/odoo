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

from openerp import tools
from openerp.osv import osv, fields


def _reopen(self, res_id, model, context=None):
    # save original model in context, because selecting the list of available
    # templates requires a model in context
    context = dict(context or {}, default_model=model)
    return {'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'view_type': 'form',
            'res_id': res_id,
            'res_model': self._name,
            'target': 'new',
            'context': context,
            }


class mail_compose_message(osv.TransientModel):
    _inherit = 'mail.compose.message'

    def default_get(self, cr, uid, fields, context=None):
        """ Override to pre-fill the data when having a template in single-email mode
        and not going through the view: the on_change is not called in that case. """
        if context is None:
            context = {}
        res = super(mail_compose_message, self).default_get(cr, uid, fields, context=context)
        if res.get('composition_mode') != 'mass_mail' and context.get('default_template_id') and res.get('model') and res.get('res_id'):
            res.update(
                self.onchange_template_id(
                    cr, uid, [], context['default_template_id'], res.get('composition_mode'),
                    res.get('model'), res.get('res_id'), context=context
                )['value']
            )
        if fields is not None:
            [res.pop(field, None) for field in res.keys() if field not in fields]
        return res

    _columns = {
        'template_id': fields.many2one('email.template', 'Use template', select=True),
    }

    def send_mail(self, cr, uid, ids, context=None):
        """ Override of send_mail to duplicate attachments linked to the email.template.
            Indeed, basic mail.compose.message wizard duplicates attachments in mass
            mailing mode. But in 'single post' mode, attachments of an email template
            also have to be duplicated to avoid changing their ownership. """
        if context is None:
            context = {}
        wizard_context = dict(context)
        for wizard in self.browse(cr, uid, ids, context=context):
            if wizard.template_id:
                wizard_context['mail_notify_user_signature'] = False  # template user_signature is added when generating body_html
                wizard_context['mail_auto_delete'] = wizard.template_id.auto_delete  # mass mailing: use template auto_delete value -> note, for emails mass mailing only
                wizard_context['mail_server_id'] = wizard.template_id.mail_server_id.id
            if not wizard.attachment_ids or wizard.composition_mode == 'mass_mail' or not wizard.template_id:
                continue
            new_attachment_ids = []
            for attachment in wizard.attachment_ids:
                if attachment in wizard.template_id.attachment_ids:
                    new_attachment_ids.append(self.pool.get('ir.attachment').copy(cr, uid, attachment.id, {'res_model': 'mail.compose.message', 'res_id': wizard.id}, context=context))
                else:
                    new_attachment_ids.append(attachment.id)
                self.write(cr, uid, wizard.id, {'attachment_ids': [(6, 0, new_attachment_ids)]}, context=context)
        return super(mail_compose_message, self).send_mail(cr, uid, ids, context=wizard_context)

    def onchange_template_id(self, cr, uid, ids, template_id, composition_mode, model, res_id, context=None):
        """ - mass_mailing: we cannot render, so return the template values
            - normal mode: return rendered values """
        if template_id and composition_mode == 'mass_mail':
            fields = ['subject', 'body_html', 'email_from', 'reply_to', 'mail_server_id']
            template = self.pool['email.template'].browse(cr, uid, template_id, context=context)
            values = dict((field, getattr(template, field)) for field in fields if getattr(template, field))
            if template.attachment_ids:
                values['attachment_ids'] = [att.id for att in template.attachment_ids]
            if template.mail_server_id:
                values['mail_server_id'] = template.mail_server_id.id
            if template.user_signature and 'body_html' in values:
                signature = self.pool.get('res.users').browse(cr, uid, uid, context).signature
                values['body_html'] = tools.append_content_to_html(values['body_html'], signature, plaintext=False)
        elif template_id:
            values = self.generate_email_for_composer_batch(cr, uid, template_id, [res_id], context=context)[res_id]
            # transform attachments into attachment_ids; not attached to the document because this will
            # be done further in the posting process, allowing to clean database if email not send
            ir_attach_obj = self.pool.get('ir.attachment')
            for attach_fname, attach_datas in values.pop('attachments', []):
                data_attach = {
                    'name': attach_fname,
                    'datas': attach_datas,
                    'datas_fname': attach_fname,
                    'res_model': 'mail.compose.message',
                    'res_id': 0,
                    'type': 'binary',  # override default_type from context, possibly meant for another model!
                }
                values.setdefault('attachment_ids', list()).append(ir_attach_obj.create(cr, uid, data_attach, context=context))
        else:
            default_context = dict(context, default_composition_mode=composition_mode, default_model=model, default_res_id=res_id)
            default_values = self.default_get(cr, uid, ['composition_mode', 'model', 'res_id', 'parent_id', 'partner_ids', 'subject', 'body', 'email_from', 'reply_to', 'attachment_ids', 'mail_server_id'], context=default_context)
            values = dict((key, default_values[key]) for key in ['subject', 'body', 'partner_ids', 'email_from', 'reply_to', 'attachment_ids', 'mail_server_id'] if key in default_values)

        if values.get('body_html'):
            values['body'] = values.pop('body_html')
        return {'value': values}

    def save_as_template(self, cr, uid, ids, context=None):
        """ hit save as template button: current form value will be a new
            template attached to the current document. """
        email_template = self.pool.get('email.template')
        ir_model_pool = self.pool.get('ir.model')
        for record in self.browse(cr, uid, ids, context=context):
            model_ids = ir_model_pool.search(cr, uid, [('model', '=', record.model or 'mail.message')], context=context)
            model_id = model_ids and model_ids[0] or False
            model_name = ''
            if model_id:
                model_name = ir_model_pool.browse(cr, uid, model_id, context=context).name
            template_name = "%s: %s" % (model_name, tools.ustr(record.subject))
            values = {
                'name': template_name,
                'subject': record.subject or False,
                'body_html': record.body or False,
                'model_id': model_id or False,
                'attachment_ids': [(6, 0, [att.id for att in record.attachment_ids])],
            }
            template_id = email_template.create(cr, uid, values, context=context)
            # generate the saved template
            template_values = record.onchange_template_id(template_id, record.composition_mode, record.model, record.res_id)['value']
            template_values['template_id'] = template_id
            record.write(template_values)
            return _reopen(self, record.id, record.model, context=context)

    #------------------------------------------------------
    # Wizard validation and send
    #------------------------------------------------------

    def generate_email_for_composer_batch(self, cr, uid, template_id, res_ids, context=None, fields=None):
        """ Call email_template.generate_email(), get fields relevant for
            mail.compose.message, transform email_cc and email_to into partner_ids """
        if context is None:
            context = {}
        if fields is None:
            fields = ['subject', 'body_html', 'email_from', 'email_to', 'partner_to', 'email_cc',  'reply_to', 'attachment_ids', 'mail_server_id']
        returned_fields = fields + ['partner_ids', 'attachments']
        values = dict.fromkeys(res_ids, False)

        ctx = dict(context, tpl_partners_only=True)
        template_values = self.pool.get('email.template').generate_email_batch(cr, uid, template_id, res_ids, fields=fields, context=ctx)
        for res_id in res_ids:
            res_id_values = dict((field, template_values[res_id][field]) for field in returned_fields if template_values[res_id].get(field))
            res_id_values['body'] = res_id_values.pop('body_html', '')
            values[res_id] = res_id_values
        return values

    def render_message_batch(self, cr, uid, wizard, res_ids, context=None):
        """ Override to handle templates. """
        # generate composer values
        composer_values = super(mail_compose_message, self).render_message_batch(cr, uid, wizard, res_ids, context)

        # generate template-based values
        if wizard.template_id:
            template_values = self.generate_email_for_composer_batch(
                cr, uid, wizard.template_id.id, res_ids,
                fields=['email_to', 'partner_to', 'email_cc', 'attachment_ids', 'mail_server_id'],
                context=context)
        else:
            template_values = {}

        for res_id in res_ids:
            if template_values.get(res_id):
                # recipients are managed by the template
                composer_values[res_id].pop('partner_ids')
                composer_values[res_id].pop('email_to')
                composer_values[res_id].pop('email_cc')
                # remove attachments from template values as they should not be rendered
                template_values[res_id].pop('attachment_ids', None)
            else:
                template_values[res_id] = dict()
            # update template values by composer values
            template_values[res_id].update(composer_values[res_id])
        return template_values

    def render_template_batch(self, cr, uid, template, model, res_ids, context=None, post_process=False):
        return self.pool.get('email.template').render_template_batch(cr, uid, template, model, res_ids, context=context, post_process=post_process)

    # Compatibility methods
    def generate_email_for_composer(self, cr, uid, template_id, res_id, context=None):
        return self.generate_email_for_composer_batch(cr, uid, template_id, [res_id], context)[res_id]

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
