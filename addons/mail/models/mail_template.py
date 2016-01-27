# -*- coding: utf-8 -*-

import base64
import copy
import datetime
import dateutil.relativedelta as relativedelta
import logging
import lxml
import urlparse
import openerp
from urllib import urlencode, quote as quote

from openerp import _, api, fields, models, SUPERUSER_ID
from openerp import tools
from openerp import report as odoo_report
from openerp.exceptions import UserError

_logger = logging.getLogger(__name__)


def format_tz(pool, cr, uid, dt, tz=False, format=False, context=None):
    context = dict(context or {})
    if tz:
        context['tz'] = tz or pool.get('res.users').read(cr, SUPERUSER_ID, uid, ['tz'])['tz'] or "UTC"
    timestamp = datetime.datetime.strptime(dt, tools.DEFAULT_SERVER_DATETIME_FORMAT)

    ts = openerp.osv.fields.datetime.context_timestamp(cr, uid, timestamp, context)

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
        ftime = ts.strftime(format_time)
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
        'cmp': cmp,

        # dateutil.relativedelta is an old-style class and cannot be directly
        # instanciated wihtin a jinja2 expression, so a lambda "proxy" is
        # is needed, apparently.
        'relativedelta': lambda *a, **kw : relativedelta.relativedelta(*a, **kw),
    })
    mako_safe_template_env = copy.copy(mako_template_env)
    mako_safe_template_env.autoescape = False
except ImportError:
    _logger.warning("jinja2 not available, templating features will not work!")


class MailTemplate(models.Model):
    "Templates for sending email"
    _name = "mail.template"
    _description = 'Email Templates'
    _order = 'name'

    @api.model
    def default_get(self, fields):
        res = super(MailTemplate, self).default_get(fields)
        if res.get('model'):
            res['model_id'] = self.env['ir.model'].search([('model', '=', res.pop('model'))]).id
        return res

    name = fields.Char('Name')
    model_id = fields.Many2one('ir.model', 'Applies to', help="The kind of document with with this template can be used")
    model = fields.Char('Related Document Model', related='model_id.model', select=True, store=True, readonly=True)
    lang = fields.Char('Language',
                       help="Optional translation language (ISO code) to select when sending out an email. "
                            "If not set, the english version will be used. "
                            "This should usually be a placeholder expression "
                            "that provides the appropriate language, e.g. "
                            "${object.partner_id.lang}.",
                       placeholder="${object.partner_id.lang}")
    user_signature = fields.Boolean('Add Signature',
                                    help="If checked, the user's signature will be appended to the text version "
                                         "of the message")
    subject = fields.Char('Subject', translate=True, help="Subject (placeholders may be used here)")
    email_from = fields.Char('From',
                             help="Sender address (placeholders may be used here). If not set, the default "
                                  "value will be the author's email alias if configured, or email address.")
    use_default_to = fields.Boolean(
        'Default recipients',
        help="Default recipients of the record:\n"
             "- partner (using id on a partner or the partner_id field) OR\n"
             "- email (using email_from or email field)")
    email_to = fields.Char('To (Emails)', help="Comma-separated recipient addresses (placeholders may be used here)")
    partner_to = fields.Char('To (Partners)', oldname='email_recipients',
                             help="Comma-separated ids of recipient partners (placeholders may be used here)")
    email_cc = fields.Char('Cc', help="Carbon copy recipients (placeholders may be used here)")
    reply_to = fields.Char('Reply-To', help="Preferred response address (placeholders may be used here)")
    mail_server_id = fields.Many2one('ir.mail_server', 'Outgoing Mail Server', readonly=False,
                                     help="Optional preferred server for outgoing mails. If not set, the highest "
                                          "priority one will be used.")
    body_html = fields.Html('Body', translate=True, sanitize=False, help="Rich-text/HTML version of the message (placeholders may be used here)")
    report_name = fields.Char('Report Filename', translate=True,
                              help="Name to use for the generated report file (may contain placeholders)\n"
                                   "The extension can be omitted and will then come from the report type.")
    report_template = fields.Many2one('ir.actions.report.xml', 'Optional report to print and attach')
    ref_ir_act_window = fields.Many2one('ir.actions.act_window', 'Sidebar action', readonly=True, copy=False,
                                        help="Sidebar action to make this template available on records "
                                             "of the related document model")
    ref_ir_value = fields.Many2one('ir.values', 'Sidebar Button', readonly=True, copy=False,
                                   help="Sidebar button to open the sidebar action")
    attachment_ids = fields.Many2many('ir.attachment', 'email_template_attachment_rel', 'email_template_id',
                                      'attachment_id', 'Attachments',
                                      help="You may attach files to this template, to be added to all "
                                           "emails created from this template")
    auto_delete = fields.Boolean('Auto Delete', default=True, help="Permanently delete this email after sending it, to save space")

    # Fake fields used to implement the placeholder assistant
    model_object_field = fields.Many2one('ir.model.fields', string="Field",
                                         help="Select target field from the related document model.\n"
                                              "If it is a relationship field you will be able to select "
                                              "a target field at the destination of the relationship.")
    sub_object = fields.Many2one('ir.model', 'Sub-model', readonly=True,
                                 help="When a relationship field is selected as first field, "
                                      "this field shows the document model the relationship goes to.")
    sub_model_object_field = fields.Many2one('ir.model.fields', 'Sub-field',
                                             help="When a relationship field is selected as first field, "
                                                  "this field lets you select the target field within the "
                                                  "destination document model (sub-model).")
    null_value = fields.Char('Default Value', help="Optional value to use if the target field is empty")
    copyvalue = fields.Char('Placeholder Expression', help="Final placeholder expression, to be copy-pasted in the desired template field.")

    @api.onchange('model_id')
    def onchange_model_id(self):
        # TDE CLEANME: should'nt it be a stored related ?
        if self.model_id:
            self.model = self.model_id.model
        else:
            self.model = False

    def build_expression(self, field_name, sub_field_name, null_value):
        """Returns a placeholder expression for use in a template field,
        based on the values provided in the placeholder assistant.

        :param field_name: main field name
        :param sub_field_name: sub field name (M2O)
        :param null_value: default value if the target value is empty
        :return: final placeholder expression """
        expression = ''
        if field_name:
            expression = "${object." + field_name
            if sub_field_name:
                expression += "." + sub_field_name
            if null_value:
                expression += " or '''%s'''" % null_value
            expression += "}"
        return expression

    @api.onchange('model_object_field', 'sub_model_object_field', 'null_value')
    def onchange_sub_model_object_value_field(self):
        if self.model_object_field:
            if self.model_object_field.ttype in ['many2one', 'one2many', 'many2many']:
                models = self.env['ir.model'].search([('model', '=', self.model_object_field.relation)])
                if models:
                    self.sub_object = models.id
                    self.copyvalue = self.build_expression(self.model_object_field.name, self.sub_model_object_field and self.sub_model_object_field.name or False, self.null_value or False)
            else:
                self.sub_object = False
                self.sub_model_object_field = False
                self.copyvalue = self.build_expression(self.model_object_field.name, False, self.null_value or False)
        else:
            self.sub_object = False
            self.copyvalue = False
            self.sub_model_object_field = False
            self.null_value = False

    @api.multi
    def unlink(self):
        self.unlink_action()
        return super(MailTemplate, self).unlink()

    @api.multi
    def copy(self, default=None):
        default = dict(default or {},
                       name=_("%s (copy)") % self.name)
        return super(MailTemplate, self).copy(default=default)

    @api.multi
    def unlink_action(self):
        for template in self:
            if template.ref_ir_act_window:
                template.ref_ir_act_window.sudo().unlink()
            if template.ref_ir_value:
                template.ref_ir_value.sudo().unlink()
        return True

    @api.multi
    def create_action(self):
        ActWindowSudo = self.env['ir.actions.act_window'].sudo()
        IrValuesSudo = self.env['ir.values'].sudo()
        view = self.env.ref('mail.email_compose_message_wizard_form')

        for template in self:
            src_obj = template.model_id.model

            button_name = _('Send Mail (%s)') % template.name
            action = ActWindowSudo.create({
                'name': button_name,
                'type': 'ir.actions.act_window',
                'res_model': 'mail.compose.message',
                'src_model': src_obj,
                'view_type': 'form',
                'context': "{'default_composition_mode': 'mass_mail', 'default_template_id' : %d, 'default_use_template': True}" % (template.id),
                'view_mode': 'form,tree',
                'view_id': view.id,
                'target': 'new',
                'auto_refresh': 1})
            ir_value = IrValuesSudo.create({
                'name': button_name,
                'model': src_obj,
                'key2': 'client_action_multi',
                'value': "ir.actions.act_window,%s" % action.id})
            template.write({
                'ref_ir_act_window': action.id,
                'ref_ir_value': ir_value.id,
            })

        return True

    # ----------------------------------------
    # RENDERING
    # ----------------------------------------

    @api.model
    def _replace_local_links(self, html):
        """ Post-processing of html content to replace local links to absolute
        links, using web.base.url as base url. """
        if not html:
            return html

        # form a tree
        root = lxml.html.fromstring(html)
        if not len(root) and root.text is None and root.tail is None:
            html = '<div>%s</div>' % html
            root = lxml.html.fromstring(html)

        base_url = self.env['ir.config_parameter'].get_param('web.base.url')
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

    @api.model
    def render_post_process(self, html):
        html = self._replace_local_links(html)
        return html

    @api.model
    def render_template(self, template_txt, model, res_ids, post_process=False):
        """ Render the given template text, replace mako expressions ``${expr}``
        with the result of evaluating these expressions with an evaluation
        context containing:

         - ``user``: browse_record of the current user
         - ``object``: record of the document record this mail is related to
         - ``context``: the context passed to the mail composition wizard

        :param str template_txt: the template text to render
        :param str model: model name of the document record this mail is related to.
        :param int res_ids: list of ids of document records those mails are related to.
        """
        multi_mode = True
        if isinstance(res_ids, (int, long)):
            multi_mode = False
            res_ids = [res_ids]

        results = dict.fromkeys(res_ids, u"")

        # try to load the template
        try:
            mako_env = mako_safe_template_env if self.env.context.get('safe') else mako_template_env
            template = mako_env.from_string(tools.ustr(template_txt))
        except Exception:
            _logger.info("Failed to load template %r", template_txt, exc_info=True)
            return multi_mode and results or results[res_ids[0]]

        # prepare template variables
        records = self.env[model].browse(filter(None, res_ids))  # filter to avoid browsing [None]
        res_to_rec = dict.fromkeys(res_ids, None)
        for record in records:
            res_to_rec[record.id] = record
        variables = {
            'format_tz': lambda dt, tz=False, format=False, context=self._context: format_tz(self.pool, self._cr, self._uid, dt, tz, format, context),
            'user': self.env.user,
            'ctx': self._context,  # context kw would clash with mako internals
        }
        for res_id, record in res_to_rec.iteritems():
            variables['object'] = record
            try:
                render_result = template.render(variables)
            except Exception:
                _logger.info("Failed to render template %r using values %r" % (template, variables), exc_info=True)
                raise UserError(_("Failed to render template %r using values %r")% (template, variables))
                render_result = u""
            if render_result == u"False":
                render_result = u""
            results[res_id] = render_result

        if post_process:
            for res_id, result in results.iteritems():
                results[res_id] = self.render_post_process(result)

        return multi_mode and results or results[res_ids[0]]

    @api.multi
    def get_email_template(self, res_ids):
        multi_mode = True
        if isinstance(res_ids, (int, long)):
            res_ids = [res_ids]
            multi_mode = False

        if res_ids is None:
            res_ids = [None]
        results = dict.fromkeys(res_ids, False)

        if not self.ids:
            return results
        self.ensure_one()

        langs = self.render_template(self.lang, self.model, res_ids)
        for res_id, lang in langs.iteritems():
            if lang:
                template = self.with_context(lang=lang)
            else:
                template = self
            results[res_id] = template

        return multi_mode and results or results[res_ids[0]]

    @api.multi
    def generate_recipients(self, results, res_ids):
        """Generates the recipients of the template. Default values can ben generated
        instead of the template values if requested by template or context.
        Emails (email_to, email_cc) can be transformed into partners if requested
        in the context. """
        self.ensure_one()

        if self.use_default_to or self._context.get('tpl_force_default_to'):
            default_recipients = self.env['mail.thread'].message_get_default_recipients(res_model=self.model, res_ids=res_ids)
            for res_id, recipients in default_recipients.iteritems():
                results[res_id].pop('partner_to', None)
                results[res_id].update(recipients)

        for res_id, values in results.iteritems():
            partner_ids = values.get('partner_ids', list())
            if self._context.get('tpl_partners_only'):
                mails = tools.email_split(values.pop('email_to', '')) + tools.email_split(values.pop('email_cc', ''))
                for mail in mails:
                    partner_id = self.env['res.partner'].find_or_create(mail)
                    partner_ids.append(partner_id)
            partner_to = values.pop('partner_to', '')
            if partner_to:
                # placeholders could generate '', 3, 2 due to some empty field values
                tpl_partner_ids = [int(pid) for pid in partner_to.split(',') if pid]
                partner_ids += self.env['res.partner'].sudo().browse(tpl_partner_ids).exists().ids
            results[res_id]['partner_ids'] = partner_ids
        return results

    @api.multi
    def generate_email(self, res_ids, fields=None):
        """Generates an email from the template for given the given model based on
        records given by res_ids.

        :param template_id: id of the template to render.
        :param res_id: id of the record to use for rendering the template (model
                       is taken from template definition)
        :returns: a dict containing all relevant fields for creating a new
                  mail.mail entry, with one extra key ``attachments``, in the
                  format [(report_name, data)] where data is base64 encoded.
        """
        self.ensure_one()
        multi_mode = True
        if isinstance(res_ids, (int, long)):
            res_ids = [res_ids]
            multi_mode = False
        if fields is None:
            fields = ['subject', 'body_html', 'email_from', 'email_to', 'partner_to', 'email_cc', 'reply_to']

        res_ids_to_templates = self.get_email_template_batch(res_ids)

        # templates: res_id -> template; template -> res_ids
        templates_to_res_ids = {}
        for res_id, template in res_ids_to_templates.iteritems():
            templates_to_res_ids.setdefault(template, []).append(res_id)

        results = dict()
        for template, template_res_ids in templates_to_res_ids.iteritems():
            Template = self.env['mail.template']
            # generate fields value for all res_ids linked to the current template
            if template.lang:
                Template = Template.with_context(lang=template._context.get('lang'))
            for field in fields:
                Template = Template.with_context(safe=field in {'subject'})
                generated_field_values = Template.render_template(
                    getattr(template, field), template.model, template_res_ids,
                    post_process=(field == 'body_html'))
                for res_id, field_value in generated_field_values.iteritems():
                    results.setdefault(res_id, dict())[field] = field_value
            # compute recipients
            if any(field in fields for field in ['email_to', 'partner_to', 'email_cc']):
                results = template.generate_recipients(results, template_res_ids)
            # update values for all res_ids
            for res_id in template_res_ids:
                values = results[res_id]
                # body: add user signature, sanitize
                if 'body_html' in fields and template.user_signature:
                    signature = self.env.user.signature
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
            if template.report_template and not 'report_template_in_attachment' in self.env.context:
                for res_id in template_res_ids:
                    attachments = []
                    report_name = self.render_template(template.report_name, template.model, res_id)
                    report = template.report_template
                    report_service = report.report_name

                    if report.report_type in ['qweb-html', 'qweb-pdf']:
                        result, format = self.pool['report'].get_pdf(self._cr, self._uid, [res_id], report_service, context=Template._context), 'pdf'
                    else:
                        result, format = odoo_report.render_report(self._cr, self._uid, [res_id], report_service, {'model': template.model}, Template._context)

                    # TODO in trunk, change return format to binary to match message_post expected format
                    result = base64.b64encode(result)
                    if not report_name:
                        report_name = 'report.' + report_service
                    ext = "." + format
                    if not report_name.endswith(ext):
                        report_name += ext
                    attachments.append((report_name, result))
                    results[res_id]['attachments'] = attachments

        return multi_mode and results or results[res_ids[0]]

    @api.multi
    def send_mail(self, res_id, force_send=False, raise_exception=False):
        """Generates a new mail message for the given template and record,
           and schedules it for delivery through the ``mail`` module's scheduler.

           :param int res_id: id of the record to render the template with
                              (model is taken from the template)
           :param bool force_send: if True, the generated mail.message is
                immediately sent after being created, as if the scheduler
                was executed for this message only.
           :returns: id of the mail.message that was created
        """
        self.ensure_one()
        Mail = self.env['mail.mail']
        Attachment = self.env['ir.attachment']  # TDE FIXME: should remove dfeault_type from context

        # create a mail_mail based on values, without attachments
        values = self.generate_email(res_id)
        values['recipient_ids'] = [(4, pid) for pid in values.get('partner_ids', list())]
        attachment_ids = values.pop('attachment_ids', [])
        attachments = values.pop('attachments', [])
        # add a protection against void email_from
        if 'email_from' in values and not values.get('email_from'):
            values.pop('email_from')
        mail = Mail.create(values)

        # manage attachments
        for attachment in attachments:
            attachment_data = {
                'name': attachment[0],
                'datas_fname': attachment[0],
                'datas': attachment[1],
                'res_model': 'mail.message',
                'res_id': mail.mail_message_id.id,
            }
            attachment_ids.append(Attachment.create(attachment_data).id)
        if attachment_ids:
            values['attachment_ids'] = [(6, 0, attachment_ids)]
            mail.write({'attachment_ids': [(6, 0, attachment_ids)]})

        if force_send:
            mail.send(raise_exception=raise_exception)
        return mail.id  # TDE CLEANME: return mail + api.returns ?

    # compatibility
    render_template_batch = render_template
    get_email_template_batch = get_email_template
    generate_email_batch = generate_email

    # Compatibility method
    # def render_template(self, cr, uid, template, model, res_id, context=None):
    #     return self.render_template_batch(cr, uid, template, model, [res_id], context)[res_id]

    # def get_email_template(self, cr, uid, template_id=False, record_id=None, context=None):
    #     return self.get_email_template_batch(cr, uid, template_id, [record_id], context)[record_id]

    # def generate_email(self, cr, uid, template_id, res_id, context=None):
    #     return self.generate_email_batch(cr, uid, template_id, [res_id], context)[res_id]
