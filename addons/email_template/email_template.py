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

import base64
import logging

from openerp import netsvc
from openerp.osv import osv, fields
from openerp.osv import fields
from openerp import tools
from openerp.tools.translate import _
from urllib import urlencode, quote as quote

_logger = logging.getLogger(__name__)

try:
    # We use a jinja2 sandboxed environment to render mako templates.
    # Note that the rendering does not cover all the mako syntax, in particular
    # arbitrary Python statements are not accepted, and not all expressions are
    # allowed: only "public" attributes (not starting with '_') of objects may
    # be accessed.
    # This is done on purpose: it prevents incidental or malicious execution of
    # Python code that may break the security of the server.
    from jinja2.sandbox import SandboxedEnvironment
    mako_template_env = SandboxedEnvironment(
        block_start_string="<%",
        block_end_string="%>",
        variable_start_string="${",
        variable_end_string="}",
        comment_start_string="<%doc>",
        comment_end_string="</%doc>",
        line_statement_prefix="%",
        line_comment_prefix="##",
        trim_blocks=True,               # do not output newline after blocks
        autoescape=True,                # XML/HTML automatic escaping
    )
    mako_template_env.globals.update({
        'str': str,
        'quote': quote,
        'urlencode': urlencode,
    })
except ImportError:
    _logger.warning("jinja2 not available, templating features will not work!")

class email_template(osv.osv):
    "Templates for sending email"
    _name = "email.template"
    _description = 'Email Templates'
    _order = 'name'

    def render_template(self, cr, uid, template, model, res_id, context=None):
        """Render the given template text, replace mako expressions ``${expr}``
           with the result of evaluating these expressions with
           an evaluation context containing:

                * ``user``: browse_record of the current user
                * ``object``: browse_record of the document record this mail is
                              related to
                * ``context``: the context passed to the mail composition wizard

           :param str template: the template text to render
           :param str model: model name of the document record this mail is related to.
           :param int res_id: id of the document record this mail is related to.
        """
        if not template:
            return u""
        if context is None:
            context = {}
        try:
            template = tools.ustr(template)
            record = None
            if res_id:
                record = self.pool.get(model).browse(cr, uid, res_id, context=context)
            user = self.pool.get('res.users').browse(cr, uid, uid, context=context)
            variables = {
                'object': record,
                'user': user,
                'ctx': context,     # context kw would clash with mako internals
            }
            result = mako_template_env.from_string(template).render(variables)
            if result == u"False":
                result = u""
            return result
        except Exception:
            _logger.exception("failed to render mako template value %r", template)
            return u""

    def get_email_template(self, cr, uid, template_id=False, record_id=None, context=None):
        if context is None:
            context = {}
        if not template_id:
            return False
        template = self.browse(cr, uid, template_id, context)
        lang = self.render_template(cr, uid, template.lang, template.model, record_id, context)
        if lang:
            # Use translated template if necessary
            ctx = context.copy()
            ctx['lang'] = lang
            template = self.browse(cr, uid, template.id, ctx)
        else:
            template = self.browse(cr, uid, int(template_id), context)
        return template

    def onchange_model_id(self, cr, uid, ids, model_id, context=None):
        mod_name = False
        if model_id:
            mod_name = self.pool.get('ir.model').browse(cr, uid, model_id, context).model
        return {'value': {'model': mod_name}}

    _columns = {
        'name': fields.char('Name'),
        'model_id': fields.many2one('ir.model', 'Applies to', help="The kind of document with with this template can be used"),
        'model': fields.related('model_id', 'model', type='char', string='Related Document Model',
                                size=128, select=True, store=True, readonly=True),
        'lang': fields.char('Language',
                            help="Optional translation language (ISO code) to select when sending out an email. "
                                 "If not set, the english version will be used. "
                                 "This should usually be a placeholder expression "
                                 "that provides the appropriate language, e.g. "
                                 "${object.partner_id.lang}.",
                            placeholder="${object.partner_id.lang}"),
        'user_signature': fields.boolean('Add Signature',
                                         help="If checked, the user's signature will be appended to the text version "
                                              "of the message"),
        'subject': fields.char('Subject', translate=True, help="Subject (placeholders may be used here)",),
        'email_from': fields.char('From',
            help="Sender address (placeholders may be used here). If not set, the default "
                    "value will be the author's email alias if configured, or email address."),
        'email_to': fields.char('To (Emails)', help="Comma-separated recipient addresses (placeholders may be used here)"),
        'email_recipients': fields.char('To (Partners)', help="Comma-separated ids of recipient partners (placeholders may be used here)"),
        'email_cc': fields.char('Cc', help="Carbon copy recipients (placeholders may be used here)"),
        'reply_to': fields.char('Reply-To', help="Preferred response address (placeholders may be used here)"),
        'mail_server_id': fields.many2one('ir.mail_server', 'Outgoing Mail Server', readonly=False,
                                          help="Optional preferred server for outgoing mails. If not set, the highest "
                                               "priority one will be used."),
        'body_html': fields.text('Body', translate=True, help="Rich-text/HTML version of the message (placeholders may be used here)"),
        'report_name': fields.char('Report Filename', translate=True,
                                   help="Name to use for the generated report file (may contain placeholders)\n"
                                        "The extension can be omitted and will then come from the report type."),
        'report_template': fields.many2one('ir.actions.report.xml', 'Optional report to print and attach'),
        'ref_ir_act_window': fields.many2one('ir.actions.act_window', 'Sidebar action', readonly=True,
                                            help="Sidebar action to make this template available on records "
                                                 "of the related document model"),
        'ref_ir_value': fields.many2one('ir.values', 'Sidebar Button', readonly=True,
                                       help="Sidebar button to open the sidebar action"),
        'attachment_ids': fields.many2many('ir.attachment', 'email_template_attachment_rel', 'email_template_id',
                                           'attachment_id', 'Attachments',
                                           help="You may attach files to this template, to be added to all "
                                                "emails created from this template"),
        'auto_delete': fields.boolean('Auto Delete', help="Permanently delete this email after sending it, to save space"),

        # Fake fields used to implement the placeholder assistant
        'model_object_field': fields.many2one('ir.model.fields', string="Field",
                                              help="Select target field from the related document model.\n"
                                                   "If it is a relationship field you will be able to select "
                                                   "a target field at the destination of the relationship."),
        'sub_object': fields.many2one('ir.model', 'Sub-model', readonly=True,
                                      help="When a relationship field is selected as first field, "
                                           "this field shows the document model the relationship goes to."),
        'sub_model_object_field': fields.many2one('ir.model.fields', 'Sub-field',
                                                  help="When a relationship field is selected as first field, "
                                                       "this field lets you select the target field within the "
                                                       "destination document model (sub-model)."),
        'null_value': fields.char('Default Value', help="Optional value to use if the target field is empty"),
        'copyvalue': fields.char('Placeholder Expression', help="Final placeholder expression, to be copy-pasted in the desired template field."),
    }

    _defaults = {
        'auto_delete': True,
    }

    def create_action(self, cr, uid, ids, context=None):
        vals = {}
        action_obj = self.pool.get('ir.actions.act_window')
        data_obj = self.pool.get('ir.model.data')
        for template in self.browse(cr, uid, ids, context=context):
            src_obj = template.model_id.model
            model_data_id = data_obj._get_id(cr, uid, 'mail', 'email_compose_message_wizard_form')
            res_id = data_obj.browse(cr, uid, model_data_id, context=context).res_id
            button_name = _('Send Mail (%s)') % template.name
            vals['ref_ir_act_window'] = action_obj.create(cr, uid, {
                 'name': button_name,
                 'type': 'ir.actions.act_window',
                 'res_model': 'mail.compose.message',
                 'src_model': src_obj,
                 'view_type': 'form',
                 'context': "{'default_composition_mode': 'mass_mail', 'default_template_id' : %d, 'default_use_template': True}" % (template.id),
                 'view_mode':'form,tree',
                 'view_id': res_id,
                 'target': 'new',
                 'auto_refresh':1
            }, context)
            vals['ref_ir_value'] = self.pool.get('ir.values').create(cr, uid, {
                 'name': button_name,
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
                    ir_values_obj = self.pool.get('ir.values')
                    ir_values_obj.unlink(cr, uid, template.ref_ir_value.id, context)
            except Exception:
                raise osv.except_osv(_("Warning"), _("Deletion of the action record failed."))
        return True

    def unlink(self, cr, uid, ids, context=None):
        self.unlink_action(cr, uid, ids, context=context)
        return super(email_template, self).unlink(cr, uid, ids, context=context)

    def copy(self, cr, uid, id, default=None, context=None):
        template = self.browse(cr, uid, id, context=context)
        if default is None:
            default = {}
        default = default.copy()
        default.update(
            name=_("%s (copy)") % (template.name),
            ref_ir_act_window=False,
            ref_ir_value=False)
        return super(email_template, self).copy(cr, uid, id, default, context)

    def build_expression(self, field_name, sub_field_name, null_value):
        """Returns a placeholder expression for use in a template field,
           based on the values provided in the placeholder assistant.

          :param field_name: main field name
          :param sub_field_name: sub field name (M2O)
          :param null_value: default value if the target value is empty
          :return: final placeholder expression
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
        return {'value': result}

    def generate_email(self, cr, uid, template_id, res_id, context=None):
        """Generates an email from the template for given (model, res_id) pair.

           :param template_id: id of the template to render.
           :param res_id: id of the record to use for rendering the template (model
                          is taken from template definition)
           :returns: a dict containing all relevant fields for creating a new
                     mail.mail entry, with one extra key ``attachments``, in the
                     format [(report_name, data)] where data is base64 encoded.
        """
        if context is None:
            context = {}
        report_xml_pool = self.pool.get('ir.actions.report.xml')
        template = self.get_email_template(cr, uid, template_id, res_id, context)
        values = {}
        for field in ['subject', 'body_html', 'email_from',
                      'email_to', 'email_recipients', 'email_cc', 'reply_to']:
            values[field] = self.render_template(cr, uid, getattr(template, field),
                                                 template.model, res_id, context=context) \
                                                 or False
        if template.user_signature:
            signature = self.pool.get('res.users').browse(cr, uid, uid, context).signature
            if signature:
                values['body_html'] = tools.append_content_to_html(values['body_html'], signature)

        if values['body_html']:
            values['body'] = tools.html_sanitize(values['body_html'])

        values.update(mail_server_id=template.mail_server_id.id or False,
                      auto_delete=template.auto_delete,
                      model=template.model,
                      res_id=res_id or False)

        attachments = []
        # Add report in attachments
        if template.report_template:
            report_name = self.render_template(cr, uid, template.report_name, template.model, res_id, context=context)
            report_service = 'report.' + report_xml_pool.browse(cr, uid, template.report_template.id, context).report_name
            # Ensure report is rendered using template's language
            ctx = context.copy()
            if template.lang:
                ctx['lang'] = self.render_template(cr, uid, template.lang, template.model, res_id, context)
            service = netsvc.LocalService(report_service)
            (result, format) = service.create(cr, uid, [res_id], {'model': template.model}, ctx)
            # TODO in trunk, change return format to binary to match message_post expected format
            result = base64.b64encode(result)
            if not report_name:
                report_name = report_service
            ext = "." + format
            if not report_name.endswith(ext):
                report_name += ext
            attachments.append((report_name, result))

        attachment_ids = []
        # Add template attachments
        for attach in template.attachment_ids:
            attachment_ids.append(attach.id)

        values['attachments'] = attachments
        values['attachment_ids'] = attachment_ids
        return values

    def send_mail(self, cr, uid, template_id, res_id, force_send=False, context=None):
        """Generates a new mail message for the given template and record,
           and schedules it for delivery through the ``mail`` module's scheduler.

           :param int template_id: id of the template to render
           :param int res_id: id of the record to render the template with
                              (model is taken from the template)
           :param bool force_send: if True, the generated mail.message is
                immediately sent after being created, as if the scheduler
                was executed for this message only.
           :returns: id of the mail.message that was created
        """
        if context is None:
            context = {}
        mail_mail = self.pool.get('mail.mail')
        ir_attachment = self.pool.get('ir.attachment')

        # create a mail_mail based on values, without attachments
        values = self.generate_email(cr, uid, template_id, res_id, context=context)
        if not values.get('email_from'):
            raise osv.except_osv(_('Warning!'),_("Sender email is missing or empty after template rendering. Specify one to deliver your message"))
        # process email_recipients field that is a comma separated list of partner_ids -> recipient_ids
        # NOTE: only usable if force_send is True, because otherwise the value is
        # not stored on the mail_mail, and therefore lost -> fixed in v8
        recipient_ids = []
        email_recipients = values.pop('email_recipients', '')
        if email_recipients:
            for partner_id in email_recipients.split(','):
                if partner_id:  # placeholders could generate '', 3, 2 due to some empty field values
                    recipient_ids.append(int(partner_id))

        attachment_ids = values.pop('attachment_ids', [])
        attachments = values.pop('attachments', [])
        msg_id = mail_mail.create(cr, uid, values, context=context)
        mail = mail_mail.browse(cr, uid, msg_id, context=context)

        # manage attachments
        for attachment in attachments:
            attachment_data = {
                'name': attachment[0],
                'datas_fname': attachment[0],
                'datas': attachment[1],
                'res_model': 'mail.message',
                'res_id': mail.mail_message_id.id,
            }
            context.pop('default_type', None)
            attachment_ids.append(ir_attachment.create(cr, uid, attachment_data, context=context))
        if attachment_ids:
            values['attachment_ids'] = [(6, 0, attachment_ids)]
            mail_mail.write(cr, uid, msg_id, {'attachment_ids': [(6, 0, attachment_ids)]}, context=context)

        if force_send:
            mail_mail.send(cr, uid, [msg_id], recipient_ids=recipient_ids, context=context)
        return msg_id

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
