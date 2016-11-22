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
import datetime
import dateutil.relativedelta as relativedelta
import logging
import lxml
import urlparse

import openerp
from openerp import SUPERUSER_ID
from openerp.osv import osv, fields
from openerp import tools, api
from openerp.tools.translate import _
from urllib import urlencode, quote as quote

_logger = logging.getLogger(__name__)


def format_tz(pool, cr, uid, dt, tz=False, format=False, context=None):
    context = dict(context or {})
    if tz:
        context['tz'] = tz or pool.get('res.users').read(cr, SUPERUSER_ID, uid, ['tz'])['tz'] or "UTC"
    timestamp = datetime.datetime.strptime(dt, tools.DEFAULT_SERVER_DATETIME_FORMAT)
    ts = fields.datetime.context_timestamp(cr, uid, timestamp, context)

    # Babel allows to format datetime in a specific language without change locale
    # So month 1 = January in English, and janvier in French
    # Be aware that the default value for format is 'medium', instead of 'short'
    #     medium:  Jan 5, 2016, 10:20:31 PM |   5 janv. 2016 22:20:31
    #     short:   1/5/16, 10:20 PM         |   5/01/16 22:20
    if context.get('use_babel'):
        # Formatting available here : http://babel.pocoo.org/en/latest/dates.html#date-fields
        from babel.dates import format_datetime
        return format_datetime(ts, format or 'medium', locale=context.get("lang") or 'en_US')

    if format:
        return ts.strftime(format)
    else:
        lang = context.get("lang")
        lang_params = {}
        if lang:
            res_lang = pool.get('res.lang')
            ids = res_lang.search(cr, uid, [("code", "=", lang)])
            if ids:
                lang_params = res_lang.read(cr, uid, ids[0], ["date_format", "time_format"])
        format_date = lang_params.get("date_format", '%B-%d-%Y')
        format_time = lang_params.get("time_format", '%I-%M %p')

        fdate = ts.strftime(format_date).decode('utf-8')
        ftime = ts.strftime(format_time).decode('utf-8')
        return "%s %s%s" % (fdate, ftime, (' (%s)' % tz) if tz else '')

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
        'datetime': datetime,
        'len': len,
        'abs': abs,
        'min': min,
        'max': max,
        'sum': sum,
        'filter': filter,
        'reduce': reduce,
        'map': map,
        'round': round,

        # dateutil.relativedelta is an old-style class and cannot be directly
        # instanciated wihtin a jinja2 expression, so a lambda "proxy" is
        # is needed, apparently.
        'relativedelta': lambda *a, **kw : relativedelta.relativedelta(*a, **kw),
    })
except ImportError:
    _logger.warning("jinja2 not available, templating features will not work!")


class email_template(osv.osv):
    "Templates for sending email"
    _name = "email.template"
    _description = 'Email Templates'
    _order = 'name'

    def default_get(self, cr, uid, fields, context=None):
        res = super(email_template, self).default_get(cr, uid, fields, context)
        if res.get('model'):
            res['model_id'] = self.pool['ir.model'].search(cr, uid, [('model', '=', res.pop('model'))], context=context)[0]
        return res

    def _replace_local_links(self, cr, uid, html, context=None):
        """ Post-processing of html content to replace local links to absolute
        links, using web.base.url as base url. """
        if not html:
            return html

        # form a tree
        root = lxml.html.fromstring(html)
        if not len(root) and root.text is None and root.tail is None:
            html = '<div>%s</div>' % html
            root = lxml.html.fromstring(html)

        base_url = self.pool['ir.config_parameter'].get_param(cr, uid, 'web.base.url')
        (base_scheme, base_netloc, bpath, bparams, bquery, bfragment) = urlparse.urlparse(base_url)

        def _process_link(url):
            new_url = url
            (scheme, netloc, path, params, query, fragment) = urlparse.urlparse(url)
            if not scheme and not netloc:
                new_url = urlparse.urlunparse((base_scheme, base_netloc, path, params, query, fragment))
            return new_url

        # check all nodes, replace :
        # - img src -> check URL
        # - a href -> check URL
        for node in root.iter():
            if node.tag == 'a' and node.get('href'):
                node.set('href', _process_link(node.get('href')))
            elif node.tag == 'img' and not node.get('src', 'data').startswith('data'):
                node.set('src', _process_link(node.get('src')))

        html = lxml.html.tostring(root, pretty_print=False, method='html')
        # this is ugly, but lxml/etree tostring want to put everything in a 'div' that breaks the editor -> remove that
        if html.startswith('<div>') and html.endswith('</div>'):
            html = html[5:-6]
        return html

    def render_post_process(self, cr, uid, html, context=None):
        html = self._replace_local_links(cr, uid, html, context=context)
        return html

    def render_template_batch(self, cr, uid, template, model, res_ids, context=None, post_process=False):
        """Render the given template text, replace mako expressions ``${expr}``
           with the result of evaluating these expressions with
           an evaluation context containing:

                * ``user``: browse_record of the current user
                * ``object``: browse_record of the document record this mail is
                              related to
                * ``context``: the context passed to the mail composition wizard

           :param str template: the template text to render
           :param str model: model name of the document record this mail is related to.
           :param int res_ids: list of ids of document records those mails are related to.
        """
        if context is None:
            context = {}
        res_ids = filter(None, res_ids)         # to avoid browsing [None] below
        results = dict.fromkeys(res_ids, u"")

        # try to load the template
        try:
            template = mako_template_env.from_string(tools.ustr(template))
        except Exception:
            _logger.exception("Failed to load template %r", template)
            return results

        # prepare template variables
        user = self.pool.get('res.users').browse(cr, uid, uid, context=context)
        records = self.pool[model].browse(cr, uid, res_ids, context=context) or [None]
        variables = {
            'format_tz': lambda dt, tz=False, format=False, context=context: format_tz(self.pool, cr, uid, dt, tz, format, context),
            'user': user,
            'ctx': context,  # context kw would clash with mako internals
        }
        for record in records:
            res_id = record.id if record else None
            variables['object'] = record
            try:
                render_result = template.render(variables)
            except Exception:
                _logger.exception("Failed to render template %r using values %r" % (template, variables))
                render_result = u""
            if render_result == u"False":
                render_result = u""
            results[res_id] = render_result

        if post_process:
            for res_id, result in results.iteritems():
                results[res_id] = self.render_post_process(cr, uid, result, context=context)
        return results

    def get_email_template_batch(self, cr, uid, template_id=False, res_ids=None, context=None):
        if context is None:
            context = {}
        if res_ids is None:
            res_ids = [None]
        results = dict.fromkeys(res_ids, False)

        if not template_id:
            return results
        template = self.browse(cr, uid, template_id, context)
        langs = self.render_template_batch(cr, uid, template.lang, template.model, res_ids, context)
        for res_id, lang in langs.iteritems():
            if lang:
                # Use translated template if necessary
                ctx = context.copy()
                ctx['lang'] = lang
                template = self.browse(cr, uid, template.id, ctx)
            else:
                template = self.browse(cr, uid, int(template_id), context)
            results[res_id] = template
        return results

    def onchange_model_id(self, cr, uid, ids, model_id, context=None):
        mod_name = False
        if model_id:
            mod_name = self.pool.get('ir.model').browse(cr, uid, model_id, context).model
        return {'value': {'model': mod_name}}

    _columns = {
        'name': fields.char('Name'),
        'model_id': fields.many2one('ir.model', 'Applies to', help="The kind of document with with this template can be used"),
        'model': fields.related('model_id', 'model', type='char', string='Related Document Model',
                                 select=True, store=True, readonly=True),
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
        'use_default_to': fields.boolean(
            'Default recipients',
            help="Default recipients of the record:\n"
                 "- partner (using id on a partner or the partner_id field) OR\n"
                 "- email (using email_from or email field)"),
        'email_to': fields.char('To (Emails)', help="Comma-separated recipient addresses (placeholders may be used here)"),
        'partner_to': fields.char('To (Partners)',
            help="Comma-separated ids of recipient partners (placeholders may be used here)",
            oldname='email_recipients'),
        'email_cc': fields.char('Cc', help="Carbon copy recipients (placeholders may be used here)"),
        'reply_to': fields.char('Reply-To', help="Preferred response address (placeholders may be used here)"),
        'mail_server_id': fields.many2one('ir.mail_server', 'Outgoing Mail Server', readonly=False,
                                          help="Optional preferred server for outgoing mails. If not set, the highest "
                                               "priority one will be used."),
        'body_html': fields.html('Body', translate=True, sanitize=False, help="Rich-text/HTML version of the message (placeholders may be used here)"),
        'report_name': fields.char('Report Filename', translate=True,
                                   help="Name to use for the generated report file (may contain placeholders)\n"
                                        "The extension can be omitted and will then come from the report type."),
        'report_template': fields.many2one('ir.actions.report.xml', 'Optional report to print and attach'),
        'ref_ir_act_window': fields.many2one('ir.actions.act_window', 'Sidebar action', readonly=True, copy=False,
                                            help="Sidebar action to make this template available on records "
                                                 "of the related document model"),
        'ref_ir_value': fields.many2one('ir.values', 'Sidebar Button', readonly=True, copy=False,
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
        action_obj = self.pool.get('ir.actions.act_window')
        data_obj = self.pool.get('ir.model.data')
        for template in self.browse(cr, uid, ids, context=context):
            src_obj = template.model_id.model
            model_data_id = data_obj._get_id(cr, uid, 'mail', 'email_compose_message_wizard_form')
            res_id = data_obj.browse(cr, uid, model_data_id, context=context).res_id
            button_name = _('Send Mail (%s)') % template.name
            act_id = action_obj.create(cr, SUPERUSER_ID, {
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
            ir_values_id = self.pool.get('ir.values').create(cr, SUPERUSER_ID, {
                 'name': button_name,
                 'model': src_obj,
                 'key2': 'client_action_multi',
                 'value': "ir.actions.act_window,%s" % act_id,
                 'object': True,
             }, context)

            template.write({
                'ref_ir_act_window': act_id,
                'ref_ir_value': ir_values_id,
            })

        return True

    def unlink_action(self, cr, uid, ids, context=None):
        for template in self.browse(cr, uid, ids, context=context):
            try:
                if template.ref_ir_act_window:
                    self.pool.get('ir.actions.act_window').unlink(cr, SUPERUSER_ID, template.ref_ir_act_window.id, context)
                if template.ref_ir_value:
                    ir_values_obj = self.pool.get('ir.values')
                    ir_values_obj.unlink(cr, SUPERUSER_ID, template.ref_ir_value.id, context)
            except Exception:
                raise osv.except_osv(_("Warning"), _("Deletion of the action record failed."))
        return True

    def unlink(self, cr, uid, ids, context=None):
        self.unlink_action(cr, uid, ids, context=context)
        return super(email_template, self).unlink(cr, uid, ids, context=context)

    def copy(self, cr, uid, id, default=None, context=None):
        template = self.browse(cr, uid, id, context=context)
        default = dict(default or {},
                       name=_("%s (copy)") % template.name)
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

    def generate_recipients_batch(self, cr, uid, results, template_id, res_ids, context=None):
        """Generates the recipients of the template. Default values can ben generated
        instead of the template values if requested by template or context.
        Emails (email_to, email_cc) can be transformed into partners if requested
        in the context. """
        if context is None:
            context = {}
        template = self.browse(cr, uid, template_id, context=context)

        if template.use_default_to or context.get('tpl_force_default_to'):
            ctx = dict(context, thread_model=template.model)
            default_recipients = self.pool['mail.thread'].message_get_default_recipients(cr, uid, res_ids, context=ctx)
            for res_id, recipients in default_recipients.iteritems():
                results[res_id].pop('partner_to', None)
                results[res_id].update(recipients)

        for res_id, values in results.iteritems():
            partner_ids = values.get('partner_ids', list())
            if context and context.get('tpl_partners_only'):
                mails = tools.email_split(values.pop('email_to', '')) + tools.email_split(values.pop('email_cc', ''))
                for mail in mails:
                    partner_id = self.pool.get('res.partner').find_or_create(cr, uid, mail, context=context)
                    partner_ids.append(partner_id)
            partner_to = values.pop('partner_to', '')
            if partner_to:
                # placeholders could generate '', 3, 2 due to some empty field values
                tpl_partner_ids = [int(pid) for pid in partner_to.split(',') if pid]
                partner_ids += self.pool['res.partner'].exists(cr, SUPERUSER_ID, tpl_partner_ids, context=context)
            results[res_id]['partner_ids'] = partner_ids
        return results

    def generate_email_batch(self, cr, uid, template_id, res_ids, context=None, fields=None):
        """Generates an email from the template for given the given model based on
        records given by res_ids.

        :param template_id: id of the template to render.
        :param res_id: id of the record to use for rendering the template (model
                       is taken from template definition)
        :returns: a dict containing all relevant fields for creating a new
                  mail.mail entry, with one extra key ``attachments``, in the
                  format [(report_name, data)] where data is base64 encoded.
        """
        if context is None:
            context = {}
        if fields is None:
            fields = ['subject', 'body_html', 'email_from', 'email_to', 'partner_to', 'email_cc', 'reply_to']

        report_xml_pool = self.pool.get('ir.actions.report.xml')
        res_ids_to_templates = self.get_email_template_batch(cr, uid, template_id, res_ids, context)

        # templates: res_id -> template; template -> res_ids
        templates_to_res_ids = {}
        for res_id, template in res_ids_to_templates.iteritems():
            templates_to_res_ids.setdefault(template, []).append(res_id)

        results = dict()
        for template, template_res_ids in templates_to_res_ids.iteritems():
            # generate fields value for all res_ids linked to the current template
            ctx = context.copy()
            if template.lang:
                ctx['lang'] = template._context.get('lang')
            for field in fields:
                generated_field_values = self.render_template_batch(
                    cr, uid, getattr(template, field), template.model, template_res_ids,
                    post_process=(field == 'body_html'),
                    context=ctx)
                for res_id, field_value in generated_field_values.iteritems():
                    results.setdefault(res_id, dict())[field] = field_value
            # compute recipients
            results = self.generate_recipients_batch(cr, uid, results, template.id, template_res_ids, context=context)
            # update values for all res_ids
            for res_id in template_res_ids:
                values = results[res_id]
                # body: add user signature, sanitize
                if 'body_html' in fields and template.user_signature:
                    signature = self.pool.get('res.users').browse(cr, uid, uid, context).signature
                    if signature:
                        values['body_html'] = tools.append_content_to_html(values['body_html'], signature, plaintext=False)
                if values.get('body_html'):
                    values['body'] = tools.html_sanitize(values['body_html'])
                # technical settings
                values.update(
                    mail_server_id=template.mail_server_id.id or False,
                    auto_delete=template.auto_delete,
                    model=template.model,
                    res_id=res_id or False,
                    attachment_ids=[attach.id for attach in template.attachment_ids],
                )

            # Add report in attachments: generate once for all template_res_ids
            if template.report_template:
                for res_id in template_res_ids:
                    attachments = []
                    report_name = self.render_template(cr, uid, template.report_name, template.model, res_id, context=ctx)
                    report = report_xml_pool.browse(cr, uid, template.report_template.id, context)
                    report_service = report.report_name

                    if report.report_type in ['qweb-html', 'qweb-pdf']:
                        result, format = self.pool['report'].get_pdf(cr, uid, [res_id], report_service, context=ctx), 'pdf'
                    else:
                        result, format = openerp.report.render_report(cr, uid, [res_id], report_service, {'model': template.model}, ctx)
            
            	    # TODO in trunk, change return format to binary to match message_post expected format
                    result = base64.b64encode(result)
                    if not report_name:
                        report_name = 'report.' + report_service
                    ext = "." + format
                    if not report_name.endswith(ext):
                        report_name += ext
                    attachments.append((report_name, result))
                    results[res_id]['attachments'] = attachments

        return results

    @api.cr_uid_id_context
    def send_mail(self, cr, uid, template_id, res_id, force_send=False, raise_exception=False, context=None):
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
            raise osv.except_osv(_('Warning!'), _("Sender email is missing or empty after template rendering. Specify one to deliver your message"))
        values['recipient_ids'] = [(4, pid) for pid in values.get('partner_ids', list())]
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
            context = dict(context)
            context.pop('default_type', None)
            attachment_ids.append(ir_attachment.create(cr, uid, attachment_data, context=context))
        if attachment_ids:
            values['attachment_ids'] = [(6, 0, attachment_ids)]
            mail_mail.write(cr, uid, msg_id, {'attachment_ids': [(6, 0, attachment_ids)]}, context=context)

        if force_send:
            mail_mail.send(cr, uid, [msg_id], raise_exception=raise_exception, context=context)
        return msg_id

    # Compatibility method
    def render_template(self, cr, uid, template, model, res_id, context=None):
        return self.render_template_batch(cr, uid, template, model, [res_id], context)[res_id]

    def get_email_template(self, cr, uid, template_id=False, record_id=None, context=None):
        return self.get_email_template_batch(cr, uid, template_id, [record_id], context)[record_id]

    def generate_email(self, cr, uid, template_id, res_id, context=None):
        return self.generate_email_batch(cr, uid, template_id, [res_id], context=context)[res_id]

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
