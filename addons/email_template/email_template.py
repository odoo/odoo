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

import base64
import random
import netsvc
import logging
import re

TEMPLATE_ENGINES = []

from osv import osv, fields
from tools.translate import _

try:
    from mako.template import Template as MakoTemplate
    TEMPLATE_ENGINES.append(('mako', 'Mako Templates'))
except ImportError:
    logging.getLogger('init').warning("module email_template: Mako templates not installed")

try:
    from django.template import Context, Template as DjangoTemplate
    #Workaround for bug:
    #http://code.google.com/p/django-tagging/issues/detail?id=110
    from django.conf import settings
    settings.configure()
    #Workaround ends
    TEMPLATE_ENGINES.append(('django', 'Django Template'))
except ImportError:
    logging.getLogger('init').warning("module email_template: Django templates not installed")

import tools
import pooler
import logging

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
            if template.template_language == 'mako':
                templ = MakoTemplate(message, input_encoding='utf-8')
                reply = MakoTemplate(message).render_unicode(object=object,
                                                             peobject=object,
                                                             env=env,
                                                             format_exceptions=True)
            elif template.template_language == 'django':
                templ = DjangoTemplate(message)
                env['object'] = object
                env['peobject'] = object
                reply = templ.render(Context(env))
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
        if object_name:
            mod_name = self.pool.get('ir.model').read(
                                              cursor,
                                              user,
                                              object_name,
                                              ['model'], context)['model']
        else:
            mod_name = False
        return {
                'value':{'model_int_name':mod_name}
                }

    _columns = {
        'name' : fields.char('Name', size=100, required=True),
        'object_name':fields.many2one('ir.model', 'Resource'),
        'model_int_name':fields.char('Model Internal Name', size=200,),
        'from_account':fields.many2one(
                   'email_template.account',
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
        #Template language(engine eg.Mako) specifics
        'template_language':fields.selection(
                TEMPLATE_ENGINES,
                'Templating Language',
                required=True
                )
    }

    _defaults = {
        'template_language' : lambda *a:'mako',

    }

    _sql_constraints = [
        ('name', 'unique (name)','The template name must be unique !')
    ]

    def create_action(self, cr, uid, ids, context=None):
        vals = {}
        if context is None:
            context = {}
        template_obj = self.browse(cr, uid, ids, context=context)[0]
        src_obj = template_obj.object_name.model
        vals['ref_ir_act_window'] = self.pool.get('ir.actions.act_window').create(cr, uid, {
             'name': template_obj.name,
             'type': 'ir.actions.act_window',
             'res_model': 'email_template.send.wizard',
             'src_model': src_obj,
             'view_type': 'form',
             'context': "{'src_model':'%s','template_id':'%d','src_rec_id':active_id,'src_rec_ids':active_ids}" % (src_obj, template_obj.id),
             'view_mode':'form,tree',
             'view_id': self.pool.get('ir.ui.view').search(cr, uid, [('name', '=', 'email_template.send.wizard.form')], context=context)[0],
             'target': 'new',
             'auto_refresh':1
        }, context)
        ir_values_obj = self.pool.get('ir.values')
        vals['ref_ir_value'] = ir_values_obj.create(cr, uid, {
             'name': _('Send Mail (%s)') % template_obj.name,
             'model': src_obj,
             'key2': 'client_action_multi',
             'value': "ir.actions.act_window," + str(vals['ref_ir_act_window']),
             'object': True,
         }, context)
        self.write(cr, uid, ids, {
            'ref_ir_act_window': vals['ref_ir_act_window'],
            'ref_ir_value': vals['ref_ir_value'],
        }, context)
        return True

    def unlink_action(self, cr, uid, ids, context=None):
        for template in self.browse(cr, uid, ids, context=context):
            try:
                if template.ref_ir_act_window:
                    self.pool.get('ir.actions.act_window').unlink(cr, uid, template.ref_ir_act_window.id, context)
                if template.ref_ir_value:
                    ir_values_obj = self.pool.get('ir.values')
                    ir_values_obj.unlink(cr, uid, template.ref_ir_value.id, context)
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
        new_name = _("Copy of template %s") % old.get('name', 'No Name')
        check = self.search(cr, uid, [('name', '=', new_name)], context=context)
        if check:
            new_name = new_name + '_' + random.choice('abcdefghij') + random.choice('lmnopqrs') + random.choice('tuvwzyz')
        default.update({'name':new_name})
        return super(email_template, self).copy(cr, uid, id, default, context)

    def build_expression(self, field_name, sub_field_name, null_value, template_language='mako'):
        """
        Returns a template expression based on data provided
        @param field_name: field name
        @param sub_field_name: sub field name (M2O)
        @param null_value: default value if the target value is empty
        @param template_language: name of template engine
        @return: computed expression
        """

        expression = ''
        if template_language == 'mako':
            if field_name:
                expression = "${object." + field_name
                if sub_field_name:
                    expression += "." + sub_field_name
                if null_value:
                    expression += " or '''%s'''" % null_value
                expression += "}"
        elif template_language == 'django':
            if field_name:
                expression = "{{object." + field_name
                if sub_field_name:
                    expression += "." + sub_field_name
                if null_value:
                    expression += "|default: '''%s'''" % null_value
                expression += "}}"
        return expression

    def onchange_model_object_field(self, cr, uid, ids, model_object_field, template_language, context=None):
        if not model_object_field:
            return {}
        result = {}
        field_obj = self.pool.get('ir.model.fields').browse(cr, uid, model_object_field, context)
        #Check if field is relational
        if field_obj.ttype in ['many2one', 'one2many', 'many2many']:
            res_ids = self.pool.get('ir.model').search(cr, uid, [('model', '=', field_obj.relation)], context=context)
            if res_ids:
                result['sub_object'] = res_ids[0]
                result['copyvalue'] = self.build_expression(False,
                                                      False,
                                                      False,
                                                      template_language)
                result['sub_model_object_field'] = False
                result['null_value'] = False
        else:
            #Its a simple field... just compute placeholder
            result['sub_object'] = False
            result['copyvalue'] = self.build_expression(field_obj.name,
                                                  False,
                                                  False,
                                                  template_language
                                                  )
            result['sub_model_object_field'] = False
            result['null_value'] = False
        return {'value':result}

    def onchange_sub_model_object_field(self, cr, uid, ids, model_object_field, sub_model_object_field, template_language, context=None):
        if not model_object_field or not sub_model_object_field:
            return {}
        result = {}
        field_obj = self.pool.get('ir.model.fields').browse(cr, uid, model_object_field, context)
        if field_obj.ttype in ['many2one', 'one2many', 'many2many']:
            res_ids = self.pool.get('ir.model').search(cr, uid, [('model', '=', field_obj.relation)], context=context)
            sub_field_obj = self.pool.get('ir.model.fields').browse(cr, uid, sub_model_object_field, context)
            if res_ids:
                result['sub_object'] = res_ids[0]
                result['copyvalue'] = self.build_expression(field_obj.name,
                                                      sub_field_obj.name,
                                                      False,
                                                      template_language
                                                      )
                result['sub_model_object_field'] = sub_model_object_field
                result['null_value'] = False
        else:
            #Its a simple field... just compute placeholder
            result['sub_object'] = False
            result['copyvalue'] = self.build_expression(field_obj.name,
                                                  False,
                                                  False,
                                                  template_language
                                                  )
            result['sub_model_object_field'] = False
            result['null_value'] = False
        return {'value':result}

    def onchange_null_value(self, cr, uid, ids, model_object_field, sub_model_object_field, null_value, template_language, context=None):
        if not model_object_field and not null_value:
            return {}
        result = {}
        field_obj = self.pool.get('ir.model.fields').browse(cr, uid, model_object_field, context)
        if field_obj.ttype in ['many2one', 'one2many', 'many2many']:
            res_ids = self.pool.get('ir.model').search(cr, uid, [('model', '=', field_obj.relation)], context=context)
            sub_field_obj = self.pool.get('ir.model.fields').browse(cr, uid, sub_model_object_field, context)
            if res_ids:
                result['sub_object'] = res_ids[0]
                result['copyvalue'] = self.build_expression(field_obj.name,
                                                      sub_field_obj.name,
                                                      null_value,
                                                      template_language
                                                      )
                result['sub_model_object_field'] = sub_model_object_field
                result['null_value'] = null_value
        else:
            #Its a simple field... just compute placeholder
            result['sub_object'] = False
            result['copyvalue'] = self.build_expression(field_obj.name,
                                                  False,
                                                  null_value,
                                                  template_language
                                                  )
            result['sub_model_object_field'] = False
            result['null_value'] = null_value
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
            'res_model':'email_template.mailbox',
            'res_id': mailbox_id,
        }
        attachment_id = attachment_obj.create(cursor,
                                              user,
                                              attachment_data,
                                              context)
        if attachment_id:
            self.pool.get('email_template.mailbox').write(
                              cursor,
                              user,
                              mailbox_id,
                              {
                               'attachments_ids':[(4, attachment_id)],
                               'mail_type':'multipart/mixed'
                              },
                              context)

    def generate_attach_reports(self,
                                 cursor,
                                 user,
                                 template,
                                 record_id,
                                 mail,
                                 context=None):
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
            reportname = 'report.' + \
                self.pool.get('ir.actions.report.xml').read(
                                             cursor,
                                             user,
                                             template.report_template.id,
                                             ['report_name'],
                                             context)['report_name']
            service = netsvc.LocalService(reportname)
            data = {}
            data['model'] = template.model_int_name
            (result, format) = service.create(cursor,
                                              user,
                                              [record_id],
                                              data,
                                              context)
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

    def _generate_mailbox_item_from_template(self,
                                      cursor,
                                      user,
                                      template,
                                      record_id,
                                      context=None):
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
            from_account = self.pool.get('email_template.account').read(
                                                    cursor,
                                                    user,
                                                    context.get('account_id'),
                                                    ['name', 'email_id'],
                                                    context
                                                    )
        else:
            from_account = {
                            'id':template.from_account.id,
                            'name':template.from_account.name,
                            'email_id':template.from_account.email_id
                            }
        lang = get_value(cursor,
                         user,
                         record_id,
                         template.lang,
                         template,
                         context)
        if lang:
            ctx = context.copy()
            ctx.update({'lang':lang})
            template = self.browse(cursor, user, template.id, context=ctx)

        # determine name of sender, either it is specified in email_id or we
        # use the account name
        print "////////////////////////",from_account
        email_id = from_account['email_id']
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
            'account_id' :from_account['id'],
            #This is a mandatory field when automatic emails are sent
            'state':'na',
            'folder':'drafts',
            'mail_type':'multipart/alternative',
        }

        if template['message_id']:
            # use provided message_id with placeholders
            mailbox_values.update({'message_id': get_value(cursor, user, record_id, template['message_id'], template, context)})

        elif template['track_campaign_item']:
            # get appropriate message-id
            mailbox_values.update({'message_id': tools.misc.generate_tracking_message_id(record_id)})

        if not mailbox_values['account_id']:
            raise Exception("Unable to send the mail. No account linked to the template.")
        #Use signatures if allowed
        if template.use_sign:
            sign = self.pool.get('res.users').read(cursor,
                                                   user,
                                                   user,
                                                   ['signature'],
                                                   context)['signature']
            if mailbox_values['body_text']:
                mailbox_values['body_text'] += sign
            if mailbox_values['body_html']:
                mailbox_values['body_html'] += sign
        mailbox_id = self.pool.get('email_template.mailbox').create(
                                                             cursor,
                                                             user,
                                                             mailbox_values,
                                                             context)

        return mailbox_id


    def generate_mail(self,
                      cursor,
                      user,
                      template_id,
                      record_ids,
                      context=None):
        if context is None:
            context = {}
        template = self.browse(cursor, user, template_id, context=context)
        print ">>>>>>>>>>>><<<<<<<<<<<<<<<<",template
        if not template:
            raise Exception("The requested template could not be loaded")
        result = True
        mailbox_obj = self.pool.get('email_template.mailbox')
        for record_id in record_ids:
            mailbox_id = self._generate_mailbox_item_from_template(
                                                                cursor,
                                                                user,
                                                                template,
                                                                record_id,
                                                                context)
            mail = mailbox_obj.browse(
                                        cursor,
                                        user,
                                        mailbox_id,
                                        context=context
                                              )
            if template.report_template or template.attachment_ids:
                self.generate_attach_reports(
                                              cursor,
                                              user,
                                              template,
                                              record_id,
                                              mail,
                                              context
                                              )

            self.pool.get('email_template.mailbox').write(
                                                cursor,
                                                user,
                                                mailbox_id,
                                                {'folder':'outbox'},
                                                context=context
            )
            # TODO : manage return value of all the records
            result = self.pool.get('email_template.mailbox').send_this_mail(cursor, user, [mailbox_id], context)
        return result

email_template()


## FIXME: this class duplicates a lot of features of the email template send wizard,
##        one of the 2 should inherit from the other!

class email_template_preview(osv.osv_memory):
    _name = "email_template.preview"
    _description = "Email Template Preview"

    def _get_model_recs(self, cr, uid, context=None):
        if context is None:
            context = {}
            #Fills up the selection box which allows records from the selected object to be displayed
        self.context = context
        if 'template_id' in context:
            ref_obj_id = self.pool.get('email.template').read(cr, uid, context['template_id'], ['object_name'], context)
            ref_obj_name = self.pool.get('ir.model').read(cr, uid, ref_obj_id['object_name'][0], ['model'], context)['model']
            model_obj = self.pool.get(ref_obj_name)
            ref_obj_ids = model_obj.search(cr, uid, [], 0, 20, 'id', context=context)
            if not ref_obj_ids:
                ref_obj_ids = []

            # also add the default one if requested, otherwise it won't be available for selection:
            default_id = context.get('default_rel_model_ref')
            if default_id and default_id not in ref_obj_ids:
                ref_obj_ids.insert(0, default_id)
            return model_obj.name_get(cr, uid, ref_obj_ids, context)
        return []

    def default_get(self, cr, uid, fields, context=None):
        if context is None:
            context = {}
        result = super(email_template_preview, self).default_get(cr, uid, fields, context=context)
        if (not fields or 'rel_model_ref' in fields) and 'template_id' in context \
           and not result.get('rel_model_ref'):
            selectables = self._get_model_recs(cr, uid, context=context)
            result['rel_model_ref'] = selectables and selectables[0][0] or False
        return result

    def _default_model(self, cursor, user, context=None):
        """
        Returns the default value for model field
        @param cursor: Database Cursor
        @param user: ID of current user
        @param context: OpenERP Context
        """
        return self.pool.get('email.template').read(
                                                   cursor,
                                                   user,
                                                   context['template_id'],
                                                   ['object_name'],
                                                   context).get('object_name', False)

    _columns = {
        'ref_template':fields.many2one(
                                       'email.template',
                                       'Template', readonly=True),
        'rel_model':fields.many2one('ir.model', 'Model', readonly=True),
        'rel_model_ref':fields.selection(_get_model_recs, 'Referred Document'),
        'to':fields.char('To', size=250, readonly=True),
        'cc':fields.char('CC', size=250, readonly=True),
        'bcc':fields.char('BCC', size=250, readonly=True),
        'reply_to':fields.char('Reply-To',
                    size=250,
                    help="The address recipients should reply to,"
                         " if different from the From address."
                         " Placeholders can be used here."),
        'message_id':fields.char('Message-ID',
                    size=250,
                    help="The Message-ID header value, if you need to"
                         "specify it, for example to automatically recognize the replies later."
                        " Placeholders can be used here."),
        'subject':fields.char('Subject', size=200, readonly=True),
        'body_text':fields.text('Body', readonly=True),
        'body_html':fields.text('Body', readonly=True),
        'report':fields.char('Report Name', size=100, readonly=True),
    }
    _defaults = {
        'ref_template': lambda self, cr, uid, ctx:ctx['template_id'] or False,
        'rel_model': _default_model,
    }
    def on_change_ref(self, cr, uid, ids, rel_model_ref, context=None):
        if context is None:
            context = {}
        if not rel_model_ref:
            return {}
        vals = {}
        if context == {}:
            context = self.context
        template = self.pool.get('email.template').browse(cr, uid, context['template_id'], context)
        #Search translated template
        lang = get_value(cr, uid, rel_model_ref, template.lang, template, context)
        if lang:
            ctx = context.copy()
            ctx.update({'lang':lang})
            template = self.pool.get('email.template').browse(cr, uid, context['template_id'], ctx)
        vals['to'] = get_value(cr, uid, rel_model_ref, template.def_to, template, context)
        vals['cc'] = get_value(cr, uid, rel_model_ref, template.def_cc, template, context)
        vals['bcc'] = get_value(cr, uid, rel_model_ref, template.def_bcc, template, context)
        vals['reply_to'] = get_value(cr, uid, rel_model_ref, template.reply_to, template, context)
        if template.message_id:
            vals['message_id'] = get_value(cr, uid, rel_model_ref, template.message_id, template, context)
        elif template.track_campaign_item:
            vals['message_id'] = tools.misc.generate_tracking_message_id(rel_model_ref)
        vals['subject'] = get_value(cr, uid, rel_model_ref, template.def_subject, template, context)
        vals['body_text'] = get_value(cr, uid, rel_model_ref, template.def_body_text, template, context)
        vals['body_html'] = get_value(cr, uid, rel_model_ref, template.def_body_html, template, context)
        vals['report'] = get_value(cr, uid, rel_model_ref, template.file_name, template, context)
        return {'value':vals}

email_template_preview()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
