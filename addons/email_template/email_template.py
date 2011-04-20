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
    _inherit = 'email.message.common'
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

    def _lang_get(self, cr, uid, context={}):
        obj = self.pool.get('res.lang')
        ids = obj.search(cr, uid, [], context=context)
        res = obj.read(cr, uid, ids, ['code', 'name'], context)
        return [(r['code'], r['name']) for r in res] + [('','')]

    _columns = {
        'name': fields.char('Name', size=250),
        'model_id':fields.many2one('ir.model', 'Resource'),
        'model': fields.related('model_id', 'model', string='Model', type="char", size=128, store=True, readonly=True),
        'lang': fields.selection(_lang_get, 'Language', size=5, help="The default language for the email."
                   " Placeholders can be used here. "
                   "eg. ${object.partner_id.lang}"),
        'subject':fields.char(
                  'Subject',
                  size=200,
                  help="The subject of email."
                  " Placeholders can be used here.",
                  translate=True),
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
        'model_object_field':fields.many2one(
                 'ir.model.fields',
                 string="Field",
                 help="Select the field from the model you want to use."
                 "\nIf it is a relationship field you will be able to "
                 "choose the nested values in the box below\n(Note:If "
                 "there are no values make sure you have selected the"
                 " correct model)"),
        'sub_object':fields.many2one(
                 'ir.model',
                 'Sub-model',
                 help='When a relation field is used this field'
                 ' will show you the type of field you have selected'),
        'sub_model_object_field':fields.many2one(
                 'ir.model.fields',
                 'Sub Field',
                 help="When you choose relationship fields "
                 "this field will specify the sub value you can use."),
        'null_value':fields.char(
                 'Null Value',
                 help="This Value is used if the field is empty",
                 size=50),
        'copyvalue':fields.char(
                'Expression',
                size=100,
                help="Copy and paste the value in the "
                "location you want to use a system value."),
        'auto_delete': fields.boolean('Auto Delete', help="Permanently delete emails after sending"),
        'model': fields.related('model_id','model', type='char', size=128, string='Object', help="Placeholders can be used here."),
        'email_from': fields.char('From', size=128, help="Email From. Placeholders can be used here."),
        'email_to': fields.char('To', size=256, help="Email Recipients. Placeholders can be used here."),
        'email_cc': fields.char('Cc', size=256, help="Carbon Copy Email Recipients. Placeholders can be used here."),
        'email_bcc': fields.char('Bcc', size=256, help="Blind Carbon Copy Email Recipients. Placeholders can be used here."),
        'reply_to':fields.char('Reply-To', size=250, help="Placeholders can be used here."),
        'body': fields.text('Description', translate=True, help="Placeholders can be used here."),
        'body_html': fields.text('HTML', help="Contains HTML version of email. Placeholders can be used here."),
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
            model_data_id = data_obj._get_id(cr, uid, 'mail', 'email_compose_message_wizard_form')
            res_id = data_obj.browse(cr, uid, model_data_id, context=context).res_id
            vals['ref_ir_act_window'] = action_obj.create(cr, uid, {
                 'name': template.name,
                 'type': 'ir.actions.act_window',
                 'res_model': 'email.compose.message',
                 'src_model': src_obj,
                 'view_type': 'form',
                 'context': "{'template_id':'%d','src_rec_id':active_id,'src_rec_ids':active_ids}" % (template.id),
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


    def generate_email(self, cr, uid, template_id, record_id, context=None):
        """
        Generates an email from the template for
        record record_id of target object
        """
        if context is None:
            context = {}
        values = {
                  'subject': False,
                  'body': False,
                  'email_to': False,
                  'email_cc': False,
                  'email_bcc': False,
                  'reply_to': False,
                  'auto_delete': False,
                  'model': False,
                  'res_id': False,
                  'smtp_server_id': False,
                  'attachment': False,
                  'attachment_ids': False,
        }
        if not template_id:
            return values
        report_xml_pool = self.pool.get('ir.actions.report.xml')
        template = self.get_email_template(cr, uid, template_id, record_id, context)
        def _get_template_value(field):
            if context.get('mass_mail',False): # Mass Mail: Gets original template values for multiple email change
                return getattr(template, field)
            else:
                return self.get_template_value(cr, uid, getattr(template, field), template.model, record_id, context=context)

        #Use signatures if allowed
        body = _get_template_value('body')
        if template.user_signature:
            signature = self.pool.get('res.users').browse(cr, uid, uid, context).signature
            body += '\n' + signature
        values = {
            'smtp_server_id' : template.smtp_server_id.id,
            'body' : body,
            'email_to' : _get_template_value('email_to') or False,
            'email_cc' : _get_template_value('email_cc') or False,
            'email_bcc' : _get_template_value('email_bcc') or False,
            'reply_to' : _get_template_value('reply_to') or False,
            'subject' : _get_template_value('subject') or False,
            'auto_delete': template.auto_delete,
            'model' : template.model or False,
            'res_id' : record_id or False,
            #'body_html': self.get_template_value(cr, uid, template.body_html, model, record_id, context),
        }

        attachment = {}
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
        attachment[report_name] = result

        # Add document attachments
        for attach in template.attachment_ids:
            #attach = attahcment_obj.browse(cr, uid, attachment_id, context)
            attachment[attach.datas_fname] = attach.datas
        values['attachment'] = attachment
        return values

email_template()


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
