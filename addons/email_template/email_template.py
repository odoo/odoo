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

from osv import osv
from osv import fields
import base64
import random
import netsvc
import logging
import re
from tools.translate import _
import tools
import pooler

class email_template(osv.osv):
    "Templates for sending Email"
    _inherit = 'email.message.template'
    _name = "email.template"
    _description = 'Email Templates for Models'

    def get_template_value(self, cr, uid, message=None, model=None, record_id=None, context=None):
        import mako_template
        return mako_template.get_value(cr, uid, message=message, model=model, record_id=record_id, context=context)

    def get_email_template(self, cr, uid, template_id=False, record_id=None, context=None):
        "Return Template Object"
        if context is None:
            context = {}
        if not template_id:
            template_id = context.get('template_id', False)
        if not template_id:
            return False

        template = self.browse(cr, uid, int(template_id), context)
        lang = self.get_template_value(cr, uid, template.lang, template.model, record_id, context)
        if lang:
            # Use translated template if necessary
            ctx = context.copy()
            ctx['lang'] = lang
            template = self.browse(cr, uid, template.id, ctx)
        return template

    def onchange_model_id(self, cr, uid, ids, model_id, context=None):
        mod_name = False
        if model_id:
            mod_name = self.pool.get('ir.model').browse(cr, uid, model_id, context).model
        return {'value':{'model':mod_name}}

    _columns = {
        'name': fields.char('Name', size=250),
        'model_id':fields.many2one('ir.model', 'Resource'),
        'model': fields.related('model_id', 'model', string='Model', type="char", size=128, store=True, readonly=True),
        'track_campaign_item':fields.boolean('Resource Tracking',
                                help="Enable this is you wish to include a special \
tracking marker in outgoing emails so you can identify replies and link \
them back to the corresponding resource record. \
This is useful for CRM leads for example"),
        'lang':fields.char(
                   'Language',
                   size=250,
                   help="The default language for the email."
                   " Placeholders can be used here. "
                   "eg. ${object.partner_id.lang}"),
        'subject':fields.char(
                  'Subject',
                  size=200,
                  help="The subject of email."
                  " Placeholders can be used here.",
                  translate=True),
#        'description':fields.text(
#                    'Standard Body (Text)',
#                    help="The text version of the mail",
#                    translate=True),
#        'body_html':fields.text(
#                    'Body (Text-Web Client Only)',
#                    help="The text version of the mail",
#                    translate=True),
        'user_signature':fields.boolean(
                  'Signature',
                  help="the signature from the User details"
                  " will be appended to the mail"),
        'report_name':fields.char(
                'Report Filename',
                size=200,
                help="Name of the generated report file. Placeholders can be used in the filename. eg: 2009_SO003.pdf",
                translate=True),
        'report_template':fields.many2one(
                  'ir.actions.report.xml',
                  'Report to send'),
        'attachment_ids': fields.many2many(
                    'ir.attachment',
                    'email_template_attachment_rel',
                    'email_template_id',
                    'attachment_id',
                    'Attached Files',
                    help="You may attach existing files to this template, "
                         "so they will be added in all emails created from this template"),
        'ref_ir_act_window':fields.many2one(
                    'ir.actions.act_window',
                    'Window Action',
                    help="Action that will open this email template on Resource records",
                    readonly=True),
        'ref_ir_value':fields.many2one(
                   'ir.values',
                   'Wizard Button',
                   help="Button in the side bar of the form view of this Resource that will invoke the Window Action",
                   readonly=True),
        'allowed_groups':fields.many2many(
                  'res.groups',
                  'template_group_rel',
                  'templ_id', 'group_id',
                  string="Allowed User Groups",
                  help="Only users from these groups will be"
                  " allowed to send mails from this Template"),
        'model_object_field':fields.many2one(
                 'ir.model.fields',
                 string="Field",
                 help="Select the field from the model you want to use."
                 "\nIf it is a relationship field you will be able to "
                 "choose the nested values in the box below\n(Note:If "
                 "there are no values make sure you have selected the"
                 " correct model)",
                 store=False),
        'sub_object':fields.many2one(
                 'ir.model',
                 'Sub-model',
                 help='When a relation field is used this field'
                 ' will show you the type of field you have selected',
                 store=False),
        'sub_model_object_field':fields.many2one(
                 'ir.model.fields',
                 'Sub Field',
                 help="When you choose relationship fields "
                 "this field will specify the sub value you can use.",
                 store=False),
        'null_value':fields.char(
                 'Null Value',
                 help="This Value is used if the field is empty",
                 size=50, store=False),
        'copyvalue':fields.char(
                'Expression',
                size=100,
                help="Copy and paste the value in the "
                "location you want to use a system value.",
                store=False),
        'table_html':fields.text(
             'HTML code',
             help="Copy this html code to your HTML message"
             " body for displaying the info in your mail.",
             store=False),
        'auto_delete': fields.boolean('Auto Delete', help="Permanently delete emails after sending"),
        'model': fields.related('model_id','model', type='char', size=128, string='Object'),
    }

    _sql_constraints = [
        ('name', 'unique (name)','The template name must be unique !')
    ]

    def create_action(self, cr, uid, ids, context=None):
        vals = {}
        if context is None:
            context = {}
        action_obj = self.pool.get('ir.actions.act_window')
        data_obj = self.pool.get('ir.model.data')
        for template in self.browse(cr, uid, ids, context=context):
            src_obj = template.model_id.model
            model_data_id = data_obj._get_id(cr, uid, 'emails', 'email_compose_message_wizard_form')
            res_id = data_obj.browse(cr, uid, model_data_id, context=context).res_id
            vals['ref_ir_act_window'] = action_obj.create(cr, uid, {
                 'name': template.name,
                 'type': 'ir.actions.act_window',
                 'res_model': 'email.compose.message',
                 'src_model': src_obj,
                 'view_type': 'form',
                 'context': "{'email_model':'%s', 'email_res_id': active_id,'template_id':'%d','src_rec_id':active_id,'src_rec_ids':active_ids}" % (src_obj, template.id),
                 'view_mode':'form,tree',
                 'view_id': res_id,
                 'target': 'new',
                 'auto_refresh':1
            }, context)
            vals['ref_ir_value'] = self.pool.get('ir.values').create(cr, uid, {
                 'name': _('Send Mail (%s)') % template.name,
                 'model': src_obj,
                 'key2': 'client_action_multi',
                 'value': "ir.actions.act_window," + str(vals['ref_ir_act_window']),
                 'object': True,
             }, context)
        self.write(cr, uid, ids, {
                    'ref_ir_act_window': vals.get('ref_ir_act_window',False),
                    'ref_ir_value': vals.get('ref_ir_value',False),
                }, context)
        return True

    def unlink_action(self, cr, uid, ids, context=None):
        for template in self.browse(cr, uid, ids, context=context):
            try:
                if template.ref_ir_act_window:
                    self.pool.get('ir.actions.act_window').unlink(cr, uid, template.ref_ir_act_window.id, context)
                if template.ref_ir_value:
                    self.pool.get('ir.values').unlink(cr, uid, template.ref_ir_value.id, context)
            except:
                raise osv.except_osv(_("Warning"), _("Deletion of Record failed"))

    def delete_action(self, cr, uid, ids, context=None):
        self.unlink_action(cr, uid, ids, context=context)
        return True

    def unlink(self, cr, uid, ids, context=None):
        self.unlink_action(cr, uid, ids, context=context)
        return super(email_template, self).unlink(cr, uid, ids, context=context)

    def copy(self, cr, uid, id, default=None, context=None):
        if default is None:
            default = {}
        default = default.copy()
        old = self.read(cr, uid, id, ['name'], context=context)
        new_name = _("Copy of template ") + old.get('name', 'No Name')
        check = self.search(cr, uid, [('name', '=', new_name)], context=context)
        if check:
            new_name = new_name + '_' + random.choice('abcdefghij') + random.choice('lmnopqrs') + random.choice('tuvwzyz')
        default.update({'name':new_name})
        return super(email_template, self).copy(cr, uid, id, default, context)

    def build_expression(self, field_name, sub_field_name, null_value):
        """
        Returns a template expression based on data provided
        @param field_name: field name
        @param sub_field_name: sub field name (M2O)
        @param null_value: default value if the target value is empty
        @return: computed expression
        """
        expression = ''
        if field_name:
            expression = "${object." + field_name
            if sub_field_name:
                expression += "." + sub_field_name
            if null_value:
                expression += " or '''%s'''" % null_value
            expression += "}"
        return expression
#
#    def onchange_model_object_field(self, cr, uid, ids, model_object_field, context=None):
#        if not model_object_field:
#            return {}
#        result = {}
#        field_obj = self.pool.get('ir.model.fields').browse(cr, uid, model_object_field, context)
#        #Check if field is relational
#        if field_obj.ttype in ['many2one', 'one2many', 'many2many']:
#            res_ids = self.pool.get('ir.model').search(cr, uid, [('model', '=', field_obj.relation)], context=context)
#            if res_ids:
#                result['sub_object'] = res_ids[0]
#                result['copyvalue'] = self.build_expression(False, False, False)
#                result['sub_model_object_field'] = False
#                result['null_value'] = False
#        else:
#            #Its a simple field... just compute placeholder
#            result['sub_object'] = False
#            result['copyvalue'] = self.build_expression(field_obj.name, False, False)
#            result['sub_model_object_field'] = False
#            result['null_value'] = False
#        return {'value':result}
#
#    def onchange_sub_model_object_field(self, cr, uid, ids, model_object_field, sub_model_object_field, context=None):
#        if not model_object_field or not sub_model_object_field:
#            return {}
#        result = {}
#        field_obj = self.pool.get('ir.model.fields').browse(cr, uid, model_object_field, context)
#        if field_obj.ttype in ['many2one', 'one2many', 'many2many']:
#            res_ids = self.pool.get('ir.model').search(cr, uid, [('model', '=', field_obj.relation)], context=context)
#            sub_field_obj = self.pool.get('ir.model.fields').browse(cr, uid, sub_model_object_field, context)
#            if res_ids:
#                result['sub_object'] = res_ids[0]
#                result['copyvalue'] = self.build_expression(field_obj.name, sub_field_obj.name, False)
#                result['sub_model_object_field'] = sub_model_object_field
#                result['null_value'] = False
#        else:
#            #Its a simple field... just compute placeholder
#            result['sub_object'] = False
#            result['copyvalue'] = self.build_expression(field_obj.name, False, False)
#            result['sub_model_object_field'] = False
#            result['null_value'] = False
#        return {'value':result}
#
#
#    def onchange_null_value(self, cr, uid, ids, model_object_field, sub_model_object_field, null_value, template_language, context=None):
#        if not model_object_field and not null_value:
#            return {}
#        result = {}
#        field_obj = self.pool.get('ir.model.fields').browse(cr, uid, model_object_field, context)
#        if field_obj.ttype in ['many2one', 'one2many', 'many2many']:
#            res_ids = self.pool.get('ir.model').search(cr, uid, [('model', '=', field_obj.relation)], context=context)
#            sub_field_obj = self.pool.get('ir.model.fields').browse(cr, uid, sub_model_object_field, context)
#            if res_ids:
#                result['sub_object'] = res_ids[0]
#                result['copyvalue'] = self.build_expression(field_obj.name,
#                                                      sub_field_obj.name,
#                                                      null_value,
#                                                      template_language
#                                                      )
#                result['sub_model_object_field'] = sub_model_object_field
#                result['null_value'] = null_value
#        else:
#            #Its a simple field... just compute placeholder
#            result['sub_object'] = False
#            result['copyvalue'] = self.build_expression(field_obj.name,
#                                                  False,
#                                                  null_value,
#                                                  template_language
#                                                  )
#            result['sub_model_object_field'] = False
#            result['null_value'] = null_value
#        return {'value':result}

    def onchange_sub_model_object_value_field(self, cr, uid, ids, model_object_field, sub_model_object_field=False, null_value=None, context=None):
        result = {
            'sub_object': False,
            'copyvalue': False,
            'sub_model_object_field': False,
            'null_value': False
            }
        if model_object_field:
            fields_obj = self.pool.get('ir.model.fields')
            field_value = fields_obj.browse(cr, uid, model_object_field, context)
            if field_value.ttype in ['many2one', 'one2many', 'many2many']:
                res_ids = self.pool.get('ir.model').search(cr, uid, [('model', '=', field_value.relation)], context=context)
                sub_field_value = False
                if sub_model_object_field:
                    sub_field_value = fields_obj.browse(cr, uid, sub_model_object_field, context)
                if res_ids:
                    result.update({
                        'sub_object': res_ids[0],
                        'copyvalue': self.build_expression(field_value.name, sub_field_value and sub_field_value.name or False, null_value or False),
                        'sub_model_object_field': sub_model_object_field or False,
                        'null_value': null_value or False
                        })
            else:
                result.update({
                        'copyvalue': self.build_expression(field_value.name, False, null_value or False),
                        'null_value': null_value or False
                        })
        return {'value':result}


    def _generate_email(self, cr, uid, template_id, record_id, context=None):
        """
        Generates an email from the template for
        record record_id of target object
        """
        if context is None:
            context = {}
        smtp_pool = self.pool.get('email.smtp_server')
        email_message_pool = self.pool.get('email.message')
        report_xml_pool = self.pool.get('ir.actions.report.xml')
        template = self.get_email_template(cr, uid, template_id, record_id, context)
        smtp_server_id = context.get('smtp_server_id', False)
        if not smtp_server_id and template.smtp_server_id:
            smtp_server_id = template.smtp_server_id.id
        else:
            smtp_ids = smtp_pool.search(cr, uid, [('default','=',True)])
            smtp_server_id = smtp_ids and smtp_ids[0]
        smtp_server = smtp_pool.browse(cr, uid, smtp_server_id, context=context)
        # determine name of sender, either it is specified in email_id

        email_id = smtp_server.email_id.strip()
        email_from = re.findall(r'([^ ,<@]+@[^> ,]+)', email_id)[0]
        if email_from != email_id:
            email_from = smtp_server.email_id
        else:
            email_from = tools.ustr(smtp_server.name) + "<" + tools.ustr(email_id) + ">"

        model = template.model_id.model
        values = {
            'email_from': email_from,
            'email_to': self.get_template_value(cr, uid, template.email_to, model, record_id, context),
            'email_cc': self.get_template_value(cr, uid, template.email_cc, model, record_id, context),
            'email_bcc': self.get_template_value(cr, uid, template.email_bcc, model, record_id, context),
            'reply_to': self.get_template_value(cr, uid, template.reply_to, model, record_id, context),
            'name': self.get_template_value(cr, uid, template.subject, model, record_id, context),
            'description': self.get_template_value(cr, uid, template.description, model, record_id, context),
            #'body_html': self.get_template_value(cr, uid, template.body_html, model, record_id, context),
        }

        if template.message_id:
            # use provided message_id with placeholders
            values.update({'message_id': self.get_template_value(cr, uid, template.message_id, model, record_id, context)})

        elif template['track_campaign_item']:
            # get appropriate message-id
            values.update({'message_id': tools.misc.generate_tracking_message_id(record_id)})

        #Use signatures if allowed
        if template.user_signature:
            sign = self.pool.get('res.users').read(cr, uid, uid, ['signature'], context)['signature']
            if values['description']:
                values['description'] += '\n\n' + sign
            #if values['body_html']:
            #    values['body_html'] += sign

        attachment = []

        # Add report as a Document
        if template.report_template:
            report_name = template.report_name
            reportname = 'report.' + report_xml_pool.browse(cr, uid, template.report_template.id, context).report_name
            data = {}
            data['model'] = template.model

            # Ensure report is rendered using template's language
            ctx = context.copy()
            if template.lang:
                ctx['lang'] = self.get_template_value(cr, uid, template.lang, template.model, record_id, context)
            service = netsvc.LocalService(reportname)
            (result, format) = service.create(cr, uid, [record_id], data, ctx)
            result = base64.b64encode(result)
            if not report_name:
                report_name = reportname
            report_name = report_name + "." + format
            attachment.append((report_name, result))


        # Add document attachments
        for attach in template.attachment_ids:
            #attach = attahcment_obj.browse(cr, uid, attachment_id, context)
            attachment.append((attach.datas_fname, attach.datas))

        #Send emails
        context.update({'notemplate':True})
        email_id = email_message_pool.email_send(cr, uid, values.get('email_from'), values.get('email_to'), values.get('name'), values.get('description'),
                    model=model, email_cc=values.get('email_cc'), email_bcc=values.get('email_bcc'), reply_to=values.get('reply_to'),
                    attach=attachment, message_id=values.get('message_id'), openobject_id=record_id, debug=True, subtype='plain', x_headers={}, priority='3', smtp_server_id=smtp_server.id, context=context)
        email_message_pool.write(cr, uid, email_id, {'template_id': context.get('template_id',template.id)})
        return email_id



    def generate_email(self, cr, uid, template_id, record_id,  context=None):
        if context is None:
            context = {}
        email_id = self._generate_email(cr, uid, template_id, record_id, context)
        return email_id

email_template()

class email_message(osv.osv):
    _inherit = 'email.message'
    _columns = {
        'template_id': fields.many2one('email.template', 'Email-Template', readonly=True),
        }

    def process_email_queue(self, cr, uid, ids=None, context=None):
        result = super(email_message, self).process_email_queue(cr, uid, ids, context)
        attachment_obj = self.pool.get('ir.attachment')
        for message in self.browse(cr, uid, result, context):
            if message.template_id and message.template_id.auto_delete:
                self.unlink(cr, uid, [id], context=context)
                attachment_ids = [x.id for x in message.attachments_ids]
                attachment_obj.unlink(cr, uid, attachment_ids, context=context)
        return result

    def email_send(self, cr, uid, email_from, email_to, subject, body, model=False, email_cc=None, email_bcc=None, reply_to=False, attach=None,
            message_id=False, references=False, openobject_id=False, debug=False, subtype='plain', x_headers={}, priority='3', smtp_server_id=False, context=None):
        if context is None:
            context = {}
        notemplate = context.get('notemplate', True)
        if (not notemplate) and model and openobject_id:
            template_pool = self.pool.get('email.template')
            template_ids = template_pool.search(cr, uid, [('model','=',model)])
            if template_ids and len(template_ids):
                template_id = template_ids[0]
                return template_pool.generate_email(cr, uid, template_id, openobject_id, context=context)

        return super(email_message, self).email_send(cr, uid, email_from, email_to, subject, body, model=model, email_cc=email_cc, email_bcc=email_bcc, reply_to=reply_to, attach=attach,
                message_id=message_id, references=references, openobject_id=openobject_id, debug=debug, subtype=subtype, x_headers=x_headers, priority=priority, smtp_server_id=smtp_server_id, context=context)

email_message()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
