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

def _reopen(self, res_id, model):
    return {'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'view_type': 'form',
            'res_id': res_id,
            'res_model': self._name,
            'target': 'new',
            # save original model in context, because selecting the list of available
            # templates requires a model in context
            'context': {
                'default_model': model,
            },
    }

class mail_compose_message(osv.TransientModel):
    _inherit = 'mail.compose.message'

    _columns = {
        'template_id': fields.many2one('email.template', 'Use template', select=True),
        'partner_to': fields.char('To (Partner IDs)',
            help="Comma-separated list of recipient partners ids (placeholders may be used here)"),
        'email_to': fields.char('To (Emails)',
            help="Comma-separated recipient addresses (placeholders may be used here)",),
        'email_cc': fields.char('Cc (Emails)',
            help="Carbon copy recipients (placeholders may be used here)"),
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
            if wizard.template_id and not wizard.template_id.user_signature:
                wizard_context['mail_notify_user_signature'] = False  # template user_signature is added when generating body_html
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
            fields = ['subject', 'body_html', 'email_from', 'email_to', 'partner_to', 'email_cc', 'reply_to', 'attachment_ids']
            template_values = self.pool.get('email.template').read(cr, uid, template_id, fields, context)
            values = dict((field, template_values[field]) for field in fields if template_values.get(field))
        elif template_id:
            values = self.generate_email_for_composer(cr, uid, template_id, res_id, context=context)
            # transform attachments into attachment_ids; not attached to the document because this will
            # be done further in the posting process, allowing to clean database if email not send
            values['attachment_ids'] = values.pop('attachment_ids', [])
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
                values['attachment_ids'].append(ir_attach_obj.create(cr, uid, data_attach, context=context))
        else:
            values = self.default_get(cr, uid, ['subject', 'body', 'email_from', 'email_to', 'email_cc', 'partner_to', 'reply_to', 'attachment_ids'], context=context)

        if values.get('body_html'):
            values['body'] = values.pop('body_html')
        return {'value': values}

    def save_as_template(self, cr, uid, ids, context=None):
        """ hit save as template button: current form value will be a new
            template attached to the current document. """
        email_template = self.pool.get('email.template')
        ir_model_pool = self.pool.get('ir.model')
        for record in self.browse(cr, uid, ids, context=context):
            model_ids = ir_model_pool.search(cr, uid, [('model', '=', record.model)], context=context)
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
            return _reopen(self, record.id, record.model)

    #------------------------------------------------------
    # Wizard validation and send
    #------------------------------------------------------

    def _get_or_create_partners_from_values(self, cr, uid, rendered_values, context=None):
        """ Check for email_to, email_cc, partner_to """
        partner_ids = []
        mails = tools.email_split(rendered_values.pop('email_to', '') + ' ' + rendered_values.pop('email_cc', ''))
        for mail in mails:
            partner_id = self.pool.get('res.partner').find_or_create(cr, uid, mail, context=context)
            partner_ids.append(partner_id)
        partner_to = rendered_values.pop('partner_to', '')
        if partner_to:
            for partner_id in partner_to.split(','):
                if partner_id:  # placeholders could generate '', 3, 2 due to some empty field values
                    partner_ids.append(int(partner_id))
        return partner_ids

    def generate_email_for_composer(self, cr, uid, template_id, res_id, context=None):
        """ Call email_template.generate_email(), get fields relevant for
            mail.compose.message, transform email_cc and email_to into partner_ids """
        template_values = self.pool.get('email.template').generate_email(cr, uid, template_id, res_id, context=context)
        # filter template values
        fields = ['subject', 'body_html', 'email_from', 'email_to', 'partner_to', 'email_cc',  'reply_to', 'attachment_ids', 'attachments']
        values = dict((field, template_values[field]) for field in fields if template_values.get(field))
        values['body'] = values.pop('body_html', '')

        # transform email_to, email_cc into partner_ids
        partner_ids = self._get_or_create_partners_from_values(cr, uid, values, context=context)
        # legacy template behavior: void values do not erase existing values and the
        # related key is removed from the values dict
        if partner_ids:
            values['partner_ids'] = list(partner_ids)

        return values

    def render_message(self, cr, uid, wizard, res_id, context=None):
        """ Override to handle templates. """
        # generate the composer email
        if wizard.template_id:
            values = self.generate_email_for_composer(cr, uid, wizard.template_id.id, res_id, context=context)
        else:
            values = {}
        # remove attachments as they should not be rendered
        values.pop('attachment_ids', None)
        # get values to return
        email_dict = super(mail_compose_message, self).render_message(cr, uid, wizard, res_id, context)
        # those values are not managed; they are readonly
        email_dict.pop('email_to', None)
        email_dict.pop('email_cc', None)
        email_dict.pop('partner_to', None)
        # update template values by wizard values
        values.update(email_dict)
        return values

    def render_template(self, cr, uid, template, model, res_id, context=None):
        return self.pool.get('email.template').render_template(cr, uid, template, model, res_id, context=context)

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
