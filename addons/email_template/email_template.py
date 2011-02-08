# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2009 Sharoon Thomas
#    Copyright (C) 2010-2010 OpenERP SA (<http://www.openerp.com>)
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

def get_value(cursor, user, recid, message=None, template=None, context=None):
    """
    Evaluates an expression and returns its value
    @param cursor: Database Cursor
    @param user: ID of current user
    @param recid: ID of the target record under evaluation
    @param message: The expression to be evaluated
    @param template: BrowseRecord object of the current template
    @param context: OpenERP Context
    @return: Computed message (unicode) or u""
    """
    pool = pooler.get_pool(cursor.dbname)
    if message is None:
        message = {}
    #Returns the computed expression
    if message:
        try:
            message = tools.ustr(message)
            object = pool.get(template.model_int_name).browse(cursor, user, recid, context=context)
            env = {
                'user':pool.get('res.users').browse(cursor, user, user, context=context),
                'db':cursor.dbname
               }
            templ = MakoTemplate(message, input_encoding='utf-8')
            reply = MakoTemplate(message).render_unicode(object=object, peobject=object, env=env, format_exceptions=True)
            return reply or False
        except Exception:
            logging.exception("can't render %r", message)
            return u""
    else:
        return message

class email_template(osv.osv):
    "Templates for sending Email"

    _name = "email.template"
    _description = 'Email Templates for Models'

    def change_model(self, cursor, user, ids, object_name, context=None):
        mod_name = False
        if object_name:
            mod_name = self.pool.get('ir.model').browse(cursor, user, object_name, context).model
        return {'value':{'model_int_name':mod_name}}

    _columns = {
        'name' : fields.char('Name', size=100, required=True),
        'object_name':fields.many2one('ir.model', 'Resource'),
        'model_int_name':fields.char('Model Internal Name', size=200,),
        'from_account':fields.many2one(
                   'email.smtp_server',
                   string="Email Account",
                   help="Emails will be sent from this approved account."),
        'def_to':fields.char(
                 'Recipient (To)',
                 size=250,
                 help="The Recipient of email. "
                 "Placeholders can be used here. "
                 "e.g. ${object.email_to}"),
        'def_cc':fields.char(
                 'CC',
                 size=250,
                 help="Carbon Copy address(es), comma-separated."
                    " Placeholders can be used here. "
                    "e.g. ${object.email_cc}"),
        'def_bcc':fields.char(
                  'BCC',
                  size=250,
                  help="Blind Carbon Copy address(es), comma-separated."
                    " Placeholders can be used here. "
                    "e.g. ${object.email_bcc}"),
        'reply_to':fields.char('Reply-To',
                    size=250,
                    help="The address recipients should reply to,"
                    " if different from the From address."
                    " Placeholders can be used here. "
                    "e.g. ${object.email_reply_to}"),
        'message_id':fields.char('Message-ID',
                    size=250,
                    help="Specify the Message-ID SMTP header to use in outgoing emails. Please note that this overrides the Resource tracking option! Placeholders can be used here."),
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
        'def_subject':fields.char(
                  'Subject',
                  size=200,
                  help="The subject of email."
                  " Placeholders can be used here.",
                  translate=True),
        'def_body_text':fields.text(
                    'Standard Body (Text)',
                    help="The text version of the mail",
                    translate=True),
        'def_body_html':fields.text(
                    'Body (Text-Web Client Only)',
                    help="The text version of the mail",
                    translate=True),
        'use_sign':fields.boolean(
                  'Signature',
                  help="the signature from the User details"
                  " will be appended to the mail"),
        'file_name':fields.char(
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
    }

    _sql_constraints = [
        ('name', 'unique (name)','The template name must be unique !')
    ]

    def create_action(self, cr, uid, ids, context=None):
        vals = {}
        if context is None:
            context = {}
        action_obj = self.pool.get('ir.actions.act_window')
        for template in self.browse(cr, uid, ids, context=context):
            src_obj = template.object_name.model
            vals['ref_ir_act_window'] = action_obj.create(cr, uid, {
                 'name': template.name,
                 'type': 'ir.actions.act_window',
                 'res_model': 'email_template.send.wizard',
                 'src_model': src_obj,
                 'view_type': 'form',
                 'context': "{'src_model':'%s','template_id':'%d','src_rec_id':active_id,'src_rec_ids':active_ids}" % (src_obj, template.id),
                 'view_mode':'form,tree',
                 'view_id': self.pool.get('ir.ui.view').search(cr, uid, [('name', '=', 'email_template.send.wizard.form')], context=context)[0],
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

    def _add_attachment(self, cursor, user, mailbox_id, name, data, filename, context=None):
        """
        Add an attachment to a given mailbox entry.
        :param data: base64 encoded attachment data to store
        """
        attachment_obj = self.pool.get('ir.attachment')
        attachment_data = {
            'name':  (name or '') + _(' (Email Attachment)'),
            'datas': data,
            'datas_fname': filename,
            'description': name or _('No Description'),
            'res_model':'email.message',
            'res_id': mailbox_id,
        }
        attachment_id = attachment_obj.create(cursor, user, attachment_data, context)
        if attachment_id:
            self.pool.get('email.message').write(cursor, user, mailbox_id,
                              {
                               'attachments_ids':[(4, attachment_id)],
                               'mail_type':'multipart/mixed'
                              },
                              context)

    def generate_attach_reports(self, cursor, user, template, record_id, mail, context=None):
        """
        Generate report to be attached and attach it
        to the email, and add any directly attached files as well.

        @param cursor: Database Cursor
        @param user: ID of User
        @param template: Browse record of
                         template
        @param record_id: ID of the target model
                          for which this mail has
                          to be generated
        @param mail: Browse record of email object
        @return: True
        """
        if template.report_template:
            reportname = 'report.' + self.pool.get('ir.actions.report.xml').browse(cursor,
                                user, template.report_template.id, context).report_name
            service = netsvc.LocalService(reportname)
            data = {}
            data['model'] = template.model_int_name
            (result, format) = service.create(cursor, user, [record_id], data, context)
            fname = tools.ustr(get_value(cursor, user, record_id,
                                         template.file_name, template, context)
                               or 'Report')
            ext = '.' + format
            if not fname.endswith(ext):
                fname += ext
            self._add_attachment(cursor, user, mail.id, mail.subject, base64.b64encode(result), fname, context)

        if template.attachment_ids:
            for attachment in template.attachment_ids:
                self._add_attachment(cursor, user, mail.id, attachment.name, attachment.datas, attachment.datas_fname, context)

        return True

    def _generate_mailbox_item_from_template(self, cursor, user, template, record_id, context=None):
        """
        Generates an email from the template for
        record record_id of target object

        @param cursor: Database Cursor
        @param user: ID of User
        @param template: Browse record of
                         template
        @param record_id: ID of the target model
                          for which this mail has
                          to be generated
        @return: ID of created object
        """
        if context is None:
            context = {}
        #If account to send from is in context select it, else use enforced account
        if 'account_id' in context.keys():
            from_account = self.pool.get('email.smtp_server').read(cursor, user, context.get('account_id'), ['name', 'email_id'], context)
        else:
            from_account = {
                            'id':template.from_account.id,
                            'name':template.from_account.name,
                            'email_id':template.from_account.email_id
                            }
        lang = get_value(cursor, user, record_id, template.lang, template, context)
        if lang:
            ctx = context.copy()
            ctx.update({'lang':lang})
            template = self.browse(cursor, user, template.id, context=ctx)

        # determine name of sender, either it is specified in email_id or we
        # use the account name
        email_id = from_account['email_id'].strip()
        email_from = re.findall(r'([^ ,<@]+@[^> ,]+)', email_id)[0]
        if email_from != email_id:
            # we should keep it all, name is probably specified in the address
            email_from = from_account['email_id']
        else:
            email_from = tools.ustr(from_account['name']) + "<" + tools.ustr(email_id) + ">"

        # FIXME: should do this in a loop and rename template fields to the corresponding
        # mailbox fields. (makes no sense to have different names I think.
        mailbox_values = {
            'email_from': email_from,
            'email_to':get_value(cursor,
                               user,
                               record_id,
                               template.def_to,
                               template,
                               context),
            'email_cc':get_value(cursor,
                               user,
                               record_id,
                               template.def_cc,
                               template,
                               context),
            'email_bcc':get_value(cursor,
                                user,
                                record_id,
                                template.def_bcc,
                                template,
                                context),
            'reply_to':get_value(cursor,
                                user,
                                record_id,
                                template.reply_to,
                                template,
                                context),
            'subject':get_value(cursor,
                                    user,
                                    record_id,
                                    template.def_subject,
                                    template,
                                    context),
            'body_text':get_value(cursor,
                                      user,
                                      record_id,
                                      template.def_body_text,
                                      template,
                                      context),
            'body_html':get_value(cursor,
                                      user,
                                      record_id,
                                      template.def_body_html,
                                      template,
                                      context),
            #This is a mandatory field when automatic emails are sent
            'state':'na',
            'folder':'drafts',
            'mail_type':'multipart/alternative',
            'template_id': template.id
        }

        if template['message_id']:
            # use provided message_id with placeholders
            mailbox_values.update({'message_id': get_value(cursor, user, record_id, template['message_id'], template, context)})

        elif template['track_campaign_item']:
            # get appropriate message-id
            mailbox_values.update({'message_id': tools.misc.generate_tracking_message_id(record_id)})
#
#        if not mailbox_values['account_id']:
#            raise Exception("Unable to send the mail. No account linked to the template.")
        #Use signatures if allowed
        if template.use_sign:
            sign = self.pool.get('res.users').read(cursor, user, user, ['signature'], context)['signature']
            if mailbox_values['body_text']:
                mailbox_values['body_text'] += sign
            if mailbox_values['body_html']:
                mailbox_values['body_html'] += sign
        mailbox_id = self.pool.get('email.message').create(cursor, user, mailbox_values, context)

        return mailbox_id


    def generate_mail(self, cursor, user, template_id, record_ids,  context=None):
        if context is None:
            context = {}
        template = self.browse(cursor, user, template_id, context=context)
        if not template:
            raise Exception("The requested template could not be loaded")
        result = True
        mailbox_obj = self.pool.get('email.message')
        for record_id in record_ids:
            mailbox_id = self._generate_mailbox_item_from_template(cursor, user, template, record_id, context)
            mail = mailbox_obj.browse(cursor, user, mailbox_id, context=context)
            if template.report_template or template.attachment_ids:
                self.generate_attach_reports(cursor, user, template, record_id, mail, context )
            mailbox_obj.write(cursor, user, mailbox_id, {'folder':'outbox', 'state': 'waiting'}, context=context)
        return result

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

email_message()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
