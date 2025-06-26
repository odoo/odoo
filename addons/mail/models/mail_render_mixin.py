# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import babel
import copy
import logging
import re
import traceback

from lxml import html
from functools import reduce
from markupsafe import Markup, escape
from werkzeug import urls

from odoo import _, api, fields, models, tools
from odoo.addons.base.models.ir_qweb import QWebException
from odoo.exceptions import UserError, AccessError
from odoo.tools.mail import is_html_empty, prepend_html_content, html_normalize
from odoo.tools.rendering_tools import convert_inline_template_to_qweb, parse_inline_template, render_inline_template, template_env_globals

_logger = logging.getLogger(__name__)

def format_date(env, date, pattern=False, lang_code=False):
    try:
        return tools.format_date(env, date, date_format=pattern, lang_code=lang_code)
    except babel.core.UnknownLocaleError:
        return date


def format_datetime(env, dt, tz=False, dt_format='medium', lang_code=False):
    try:
        return tools.format_datetime(env, dt, tz=tz, dt_format=dt_format, lang_code=lang_code)
    except babel.core.UnknownLocaleError:
        return dt

def format_time(env, time, tz=False, time_format='medium', lang_code=False):
    try:
        return tools.format_time(env, time, tz=tz, time_format=time_format, lang_code=lang_code)
    except babel.core.UnknownLocaleError:
        return time


class MailRenderMixin(models.AbstractModel):
    _name = 'mail.render.mixin'
    _description = 'Mail Render Mixin'

    # If True, we trust the value on the model for rendering
    # If False, we need the group "Template Editor" to render the model fields
    _unrestricted_rendering = False

    # language for rendering
    lang = fields.Char(
        'Language',
        help="Optional translation language (ISO code) to select when sending out an email. "
             "If not set, the english version will be used. This should usually be a placeholder expression "
             "that provides the appropriate language, e.g. {{ object.partner_id.lang }}.")
    # rendering context
    render_model = fields.Char("Rendering Model", compute='_compute_render_model', store=False)

    def _compute_render_model(self):
        """ Give the target model for rendering. Void by default as models
        inheriting from ``mail.render.mixin`` should define how to find this
        model. """
        self.render_model = False

    @api.model
    def _build_expression(self, field_name, sub_field_name, null_value):
        """Returns a placeholder expression for use in a template field,
        based on the values provided in the placeholder assistant.

        :param field_name: main field name
        :param sub_field_name: sub field name (M2O)
        :param null_value: default value if the target value is empty
        :return: final placeholder expression """
        expression = ''
        if field_name:
            expression = "{{ object." + field_name
            if sub_field_name:
                expression += "." + sub_field_name
            if null_value:
                expression += f" ||| {null_value}"
            expression += " }}"
        return expression

    # ------------------------------------------------------------
    # ORM
    # ------------------------------------------------------------

    def _valid_field_parameter(self, field, name):
        # allow specifying rendering options directly from field when using the render mixin
        return name in ['render_engine', 'render_options'] or super()._valid_field_parameter(field, name)

    @api.model_create_multi
    def create(self, vals_list):
        record = super().create(vals_list)
        if self._unrestricted_rendering:
            # If the rendering is unrestricted (e.g. mail.template),
            # check the user is part of the mail editor group to create a new template if the template is dynamic
            record._check_access_right_dynamic_template()
        return record

    def write(self, vals):
        super().write(vals)
        if self._unrestricted_rendering:
            # If the rendering is unrestricted (e.g. mail.template),
            # check the user is part of the mail editor group to modify a template if the template is dynamic
            self._check_access_right_dynamic_template()
        return True

    def _update_field_translations(self, field_name, translations, digest=None, source_lang=''):
        res = super()._update_field_translations(field_name, translations, digest=digest, source_lang=source_lang)
        if self._unrestricted_rendering:
            for lang in translations:
                # If the rendering is unrestricted (e.g. mail.template),
                # check the user is part of the mail editor group to modify a template if the template is dynamic
                self.with_context(lang=lang)._check_access_right_dynamic_template()
        return res

    # ------------------------------------------------------------
    # TOOLS
    # ------------------------------------------------------------

    def _replace_local_links(self, html, base_url=None):
        """ Replace local links by absolute links. It is required in various
        cases, for example when sending emails on chatter or sending mass
        mailings. It replaces

         * href of links (mailto will not match the regex)
         * src of images/v:fill/v:image (base64 hardcoded data will not match the regex)
         * styling using url like background-image: url or background="url"

        It is done using regex because it is shorter than using an html parser
        to create a potentially complex soupe and hope to have a result that
        has not been harmed.
        """
        if not html:
            return html

        assert isinstance(html, str)
        Wrapper = html.__class__

        def _sub_relative2absolute(match):
            # compute here to do it only if really necessary + cache will ensure it is done only once
            # if not base_url
            if not _sub_relative2absolute.base_url:
                _sub_relative2absolute.base_url = self.env["ir.config_parameter"].sudo().get_param("web.base.url")
            return match.group(1) + urls.url_join(_sub_relative2absolute.base_url, match.group(2))

        _sub_relative2absolute.base_url = base_url
        html = re.sub(r"""(<(?:img|v:fill|v:image)(?=\s)[^>]*\ssrc=")(/[^/][^"]+)""", _sub_relative2absolute, html)
        html = re.sub(r"""(<a(?=\s)[^>]*\shref=")(/[^/][^"]+)""", _sub_relative2absolute, html)
        html = re.sub(r"""(<[\w-]+(?=\s)[^>]*\sbackground=")(/[^/][^"]+)""", _sub_relative2absolute, html)
        html = re.sub(re.compile(
            r"""( # Group 1: element up to url in style
                <[^>]+\bstyle=" # Element with a style attribute
                [^"]+\burl\( # Style attribute contains "url(" style
                (?:&\#34;|'|&quot;|&\#39;)?) # url style may start with (escaped) quote: capture it
            ( # Group 2: url itself
                /(?:[^'")]|(?!&\#34;)|(?!&\#39;))+ # stop at the first closing quote
        )""", re.VERBOSE), _sub_relative2absolute, html)

        return Wrapper(html)

    @api.model
    def _render_encapsulate(self, layout_xmlid, html, add_context=None, context_record=None):
        template_ctx = {
            'body': html,
            'record_name': context_record.display_name if context_record else '',
            'model_description': self.env['ir.model']._get(context_record._name).display_name if context_record else False,
            'company': context_record['company_id'] if (context_record and 'company_id' in context_record) else self.env.company,
            'record': context_record,
        }
        if add_context:
            template_ctx.update(**add_context)

        html = self.env['ir.qweb']._render(layout_xmlid, template_ctx, minimal_qcontext=True, raise_if_not_found=False)
        if not html:
            _logger.warning('QWeb template %s not found when rendering encapsulation template.' % (layout_xmlid))
        html = self.env['mail.render.mixin']._replace_local_links(html)
        return html

    @api.model
    def _prepend_preview(self, html, preview):
        """ Prepare the email body before sending. Add the text preview at the
        beginning of the mail. The preview text is displayed bellow the mail
        subject of most mail client (gmail, outlook...).

        :param html: html content for which we want to prepend a preview
        :param preview: the preview to add before the html content
        :return: html with preprended preview
        """
        if preview:
            preview = preview.strip()

        preview_markup = convert_inline_template_to_qweb(preview)

        if preview:
            html_preview = Markup("""
                <div style="display:none;font-size:1px;height:0px;width:0px;opacity:0;">
                    {}
                </div>
            """).format(preview_markup)
            return prepend_html_content(html, html_preview)
        return html

    # ------------------------------------------------------------
    # SECURITY
    # ------------------------------------------------------------

    def _has_unsafe_expression(self):
        for template in self.sudo():
            for fname, field in template._fields.items():
                engine = getattr(field, 'render_engine', 'inline_template')
                if engine in ('qweb', 'qweb_view'):
                    if self._has_unsafe_expression_template_qweb(template[fname], template.render_model, fname):
                        return True
                else:
                    if self._has_unsafe_expression_template_inline_template(template[fname], template.render_model, fname):
                        return True
        return False

    @api.model
    def _has_unsafe_expression_template_qweb(self, template_src, model, fname=None):
        if template_src:
            try:
                node = html.fragment_fromstring(template_src, create_parent='div')
                self.env["ir.qweb"].with_context(raise_on_forbidden_code_for_model=model)._generate_code(node)
            except QWebException as e:
                if isinstance(e.__cause__, PermissionError):
                    return True
                raise
        return False

    @api.model
    def _has_unsafe_expression_template_inline_template(self, template_txt, model, fname=None):
        if template_txt:
            template_instructions = parse_inline_template(str(template_txt))
            expressions = [inst[1] for inst in template_instructions]
            if not all(self.env["ir.qweb"]._is_expression_allowed(e, model) for e in expressions if e):
                return True
        return False

    def _check_access_right_dynamic_template(self):
        if not self.env.su and not self.env.user.has_group('mail.group_mail_template_editor') and self._has_unsafe_expression():
            group = self.env.ref('mail.group_mail_template_editor')
            raise AccessError(
                _('Only members of %(group_name)s group are allowed to edit templates containing sensible placeholders',
                  group_name=group.name)
            )

    # ------------------------------------------------------------
    # RENDERING
    # ------------------------------------------------------------

    @api.model
    def _render_eval_context(self):
        """ Evaluation context used in all rendering engines. Contains

          * ``user``: current user browse record;
          * ``ctx```: current context;
          * various formatting tools;
        """
        render_context = {
            'ctx': self._context,
            'format_addr': tools.formataddr,
            'format_date': lambda date, date_format=False, lang_code=False: format_date(self.env, date, date_format, lang_code),
            'format_datetime': lambda dt, tz=False, dt_format=False, lang_code=False: format_datetime(self.env, dt, tz, dt_format, lang_code),
            'format_time': lambda time, tz=False, time_format=False, lang_code=False: format_time(self.env, time, tz, time_format, lang_code),
            'format_amount': lambda amount, currency, lang_code=False: tools.format_amount(self.env, amount, currency, lang_code),
            'format_duration': tools.format_duration,
            'is_html_empty': is_html_empty,
            'slug': self.env['ir.http']._slug,
            'user': self.env.user,
            'env': self.env,
        }
        render_context.update(copy.copy(template_env_globals))
        return render_context

    @api.model
    def _render_template_qweb(self, template_src, model, res_ids,
                              add_context=None, options=None):
        """ Render a raw QWeb template.

        In addition to the generic evaluation context available, some other
        variables are added:
          * ``object``: record based on which the template is rendered;

        :param str template_src: raw QWeb template to render;
        :param str model: see ``MailRenderMixin._render_template()``;
        :param list res_ids: see ``MailRenderMixin._render_template()``;

        :param dict add_context: additional context to give to renderer. It
          allows to add or update values to base rendering context generated
          by ``MailRenderMixin._render_eval_context()``;
        :param dict options: options for rendering propagated to IrQweb render
          (see docstring for available options);

        :returns: {res_id: string of rendered template based on record}
        :rtype: dict
        """
        results = dict.fromkeys(res_ids, u"")
        if not template_src or not res_ids:
            return results

        if not self._has_unsafe_expression_template_qweb(template_src, model):
            # do not call the qweb engine
            return self._render_template_qweb_regex(template_src, model, res_ids)

        # prepare template variables
        variables = self._render_eval_context()
        if add_context:
            variables.update(**add_context)

        is_restricted = not self._unrestricted_rendering and not self.env.is_admin() and not self.env.user.has_group('mail.group_mail_template_editor')

        for record in self.env[model].browse(res_ids):
            variables['object'] = record
            options = options or {}
            if is_restricted:
                options['raise_on_forbidden_code_for_model'] = model
            try:
                render_result = self.env['ir.qweb']._render(
                    html.fragment_fromstring(template_src, create_parent='div'),
                    variables,
                    **options,
                )
                # remove the rendered tag <div> that was added in order to wrap potentially multiples nodes into one.
                render_result = render_result[5:-6]
            except Exception as e:
                if isinstance(e, QWebException) and isinstance(e.__cause__, PermissionError):
                    group = self.env.ref('mail.group_mail_template_editor')
                    raise AccessError(
                        _('Only members of %(group_name)s group are allowed to edit templates containing sensible placeholders',
                           group_name=group.name)
                    ) from e
                _logger.info("Failed to render template: %s", template_src, exc_info=True)
                raise UserError(
                    _("Failed to render QWeb template: %(template_src)s\n\n%(template_traceback)s)",
                      template_src=template_src,
                      template_traceback=traceback.format_exc())
                    ) from e
            results[record.id] = render_result

        return results

    @api.model
    def _render_template_qweb_regex(self, template_src, model, res_ids):
        """Render the template with regex instead of qweb to avoid `eval` call.

        Supporting only QWeb allowed expressions, no custom variable in that mode.
        """
        records = self.env[model].browse(res_ids)
        result = {}
        for record in records:
            def replace(match):
                tag = match.group(1)
                expr = match.group(3)
                default = match.group(9)
                if not self.env['ir.qweb']._is_expression_allowed(expr, model):
                    raise SyntaxError(f"Invalid expression for the regex mode {expr!r}")

                try:
                    value = reduce(lambda rec, field: rec[field], expr.split('.')[1:], record) or default
                except KeyError:
                    value = default

                value = escape(value or '')
                return value if tag.lower() == 't' else f"<{tag}>{value}</{tag}>"

            # normalize the HTML (add a parent div to avoid modification of the template)
            template_src = html_normalize(f'<div>{template_src}</div>')
            if template_src.startswith('<div>') and template_src.endswith('</div>'):
                template_src = template_src[5:-6]

            result[record.id] = Markup(re.sub(
                r'''<(\w+)[\s|\n]+t-out=[\s|\n]*(\'|\")((\w|\.)+)(\2)[\s|\n]*((\/>)|(>[\s|\n]*([^<>]*?))[\s|\n]*<\/\1>)''',
                replace,
                template_src,
                flags=re.DOTALL,
            ))

        return result

    @api.model
    def _render_template_qweb_view(self, view_ref, model, res_ids,
                                   add_context=None, options=None):
        """ Render a QWeb template based on an ir.ui.view content.

        In addition to the generic evaluation context available, some other
        variables are added:
          * ``object``: record based on which the template is rendered;

        :param str/int/record view_ref: source QWeb template. It should be an
          XmlID allowing to fetch an ``ir.ui.view``, or an ID of a view or
          an ``ir.ui.view`` record;
        :param str model: see ``MailRenderMixin._render_template()``;
        :param list res_ids: see ``MailRenderMixin._render_template()``;

        :param dict add_context: additional context to give to renderer. It
          allows to add or update values to base rendering context generated
          by ``MailRenderMixin._render_eval_context()``;
        :param dict options: options for rendering propagated to IrQweb render
          (see docstring for available options);

        :returns: {res_id: string of rendered template based on record}
        :rtype: dict
        """
        results = {}
        if not res_ids:
            return results

        # prepare template variables
        variables = self._render_eval_context()
        if add_context:
            variables.update(**add_context)

        view_ref = view_ref.id if isinstance(view_ref, models.BaseModel) else view_ref
        for record in self.env[model].browse(res_ids):
            variables['object'] = record
            try:
                render_result = self.env['ir.qweb']._render(
                    view_ref,
                    variables,
                    minimal_qcontext=True,
                    raise_if_not_found=False,
                    **(options or {})
                )
                results[record.id] = render_result
            except Exception as e:
                _logger.info("Failed to render template: %s", view_ref, exc_info=True)
                raise UserError(
                    _("Failed to render template: %(view_ref)s", view_ref=view_ref)
                ) from e

        return results

    @api.model
    def _render_template_inline_template(self, template_txt, model, res_ids,
                                         add_context=None, options=None):
        """ Render a string-based template on records given by a model and a list
        of IDs, using inline_template.

        In addition to the generic evaluation context available, some other
        variables are added:
          * ``object``: record based on which the template is rendered;

        :param str template_txt: template text to render
        :param str model: see ``MailRenderMixin._render_template()``;
        :param list res_ids: see ``MailRenderMixin._render_template()``;

        :param dict add_context: additional context to give to renderer. It
          allows to add or update values to base rendering context generated
          by ``MailRenderMixin._render_inline_template_eval_context()``;
        :param dict options: options for rendering (no options available
          currently);

        :returns: {res_id: string of rendered template based on record}
        :rtype: dict
        """
        results = dict.fromkeys(res_ids, "")
        if not template_txt or not res_ids:
            return results

        if not self._has_unsafe_expression_template_inline_template(str(template_txt), model):
            # do not call the qweb engine
            return self._render_template_inline_template_regex(str(template_txt), model, res_ids)

        if (not self._unrestricted_rendering
            and not self.env.is_admin()
            and not self.env.user.has_group('mail.group_mail_template_editor')):
            group = self.env.ref('mail.group_mail_template_editor')
            raise AccessError(
                _('Only members of %(group_name)s group are allowed to edit templates containing sensible placeholders',
                  group_name=group.name)
            )

        # prepare template variables
        variables = self._render_eval_context()
        if add_context:
            variables.update(**add_context)

        for record in self.env[model].browse(res_ids):
            variables['object'] = record

            try:
                results[record.id] = render_inline_template(
                    parse_inline_template(str(template_txt)),
                    variables
                )
            except Exception as e:
                _logger.info("Failed to render inline_template: \n%s", str(template_txt), exc_info=True)
                raise UserError(
                    _("Failed to render inline_template template: %(template_txt)s",
                      template_txt=template_txt)
                ) from e

        return results

    @api.model
    def _render_template_inline_template_regex(self, template_txt, model, res_ids):
        """Render the inline template in static mode, without calling safe eval."""
        template = parse_inline_template(str(template_txt))
        records = self.env[model].browse(res_ids)
        result = {}
        for record in records:
            renderer = []
            for string, expression, default in template:
                renderer.append(string)
                if expression:
                    if not self.env['ir.qweb']._is_expression_allowed(expression, model):
                        raise SyntaxError(f"Invalid expression for the regex mode {expression!r}")
                    try:
                        value = reduce(lambda rec, field: rec[field], expression.split('.')[1:], record) or default
                    except KeyError:
                        value = default
                    renderer.append(str(value))
            result[record.id] = ''.join(renderer)
        return result

    @api.model
    def _render_template_postprocess(self, model, rendered):
        """ Tool method for post processing. In this method we ensure local
        links ('/shop/Basil-1') are replaced by global links ('https://www.
        mygarden.com/shop/Basil-1').

        :param rendered: result of ``_render_template``;

        :returns: updated version of rendered per record ID;
        :rtype: dict
        """
        res_ids = list(rendered.keys())
        for res_id, rendered_html in rendered.items():
            base_url = None
            if model:
                base_url = self.env[model].browse(res_id).with_prefetch(res_ids).get_base_url()
            rendered[res_id] = self._replace_local_links(rendered_html, base_url)
        return rendered

    @api.model
    def _process_scheduled_date(self, scheduled_date):
        if scheduled_date:
            # parse scheduled_date to make it timezone agnostic UTC as expected
            # by the ORM
            parsed_datetime = self.env['mail.mail']._parse_scheduled_datetime(scheduled_date)
            scheduled_date = parsed_datetime.replace(tzinfo=None) if parsed_datetime else False
        return scheduled_date

    @api.model
    def _render_template_get_valid_options(self):
        return {'post_process', 'preserve_comments'}

    @api.model
    def _render_template(self, template_src, model, res_ids, engine='inline_template',
                         add_context=None, options=None):
        """ Render the given string on records designed by model / res_ids using
        the given rendering engine. Possible engine are small_web, qweb, or
        qweb_view.

        :param str template_src: template text to render or xml id of a qweb view;
        :param str model: model name of records on which we want to perform
          rendering (aka 'crm.lead');
        :param list res_ids: list of ids of records. All should belong to the
          Odoo model given by model;
        :param string engine: inline_template, qweb or qweb_view;

        :param dict add_context: additional context to give to renderer. It
          allows to add or update values to base rendering context generated
          by ``MailRenderMixin._render_<engine>_eval_context()``;
        :param dict options: options for rendering. Use in this method and also
          propagated to rendering sub-methods. May contain notably

            boolean post_process: perform a post processing on rendered result
            (notably html links management). See``_render_template_postprocess``;
            boolean preserve_comments: if set, comments are preserved. Default
            behavior is to remove them. It is used notably for browser-specific
            code implemented like comments;

        :returns: ``{res_id: string of rendered template based on record}``
        :rtype: dict
        """
        if options is None:
            options = {}

        if not isinstance(res_ids, (list, tuple)):
            raise ValueError(
                _('Template rendering should only be called with a list of IDs. Received “%(res_ids)s” instead.',
                  res_ids=res_ids)
            )
        if engine not in ('inline_template', 'qweb', 'qweb_view'):
            raise ValueError(
                _('Template rendering supports only inline_template, qweb, or qweb_view (view or raw); received %(engine)s instead.',
                  engine=engine)
            )
        valid_render_options = self._render_template_get_valid_options()
        if not set((options or {}).keys()) <= valid_render_options:
            raise ValueError(
                _('Those values are not supported as options when rendering: %(param_names)s',
                  param_names=', '.join(set(options.keys()) - valid_render_options)
                 )
            )

        if engine == 'qweb_view':
            rendered = self._render_template_qweb_view(template_src, model, res_ids,
                                                       add_context=add_context, options=options)
        elif engine == 'qweb':
            rendered = self._render_template_qweb(template_src, model, res_ids,
                                                  add_context=add_context, options=options)
        else:
            rendered = self._render_template_inline_template(template_src, model, res_ids,
                                                             add_context=add_context, options=options)

        if options.get('post_process'):
            rendered = self._render_template_postprocess(model, rendered)

        return rendered

    def _render_lang(self, res_ids, engine='inline_template'):
        """ Given some record ids, return the lang for each record based on
        lang field of template or through specific context-based key. Lang is
        computed by performing a rendering on res_ids, based on self.render_model.

        :param list res_ids: list of ids of records. All should belong to the
          Odoo model given by model;
        :param string engine: inline_template or qweb_view;

        :return: {res_id: lang code (i.e. en_US)}
        :rtype: dict
        """
        self.ensure_one()

        rendered_langs = self._render_template(self.lang, self.render_model, res_ids, engine=engine)
        return dict(
            (res_id, lang)
            for res_id, lang in rendered_langs.items()
        )

    def _classify_per_lang(self, res_ids, engine='inline_template'):
        """ Given some record ids, return for computed each lang a contextualized
        template and its subset of res_ids.

        :param list res_ids: list of ids of records (all belonging to same model
          defined by self.render_model)
        :param string engine: inline_template, qweb, or qweb_view;

        :return: {lang: (template with lang=lang_code if specific lang computed
          or template, res_ids targeted by that language}
        :rtype: dict
        """
        self.ensure_one()

        if self.env.context.get('template_preview_lang'):
            lang_to_res_ids = {self.env.context['template_preview_lang']: res_ids}
        else:
            lang_to_res_ids = {}
            for res_id, lang in self._render_lang(res_ids, engine=engine).items():
                lang_to_res_ids.setdefault(lang, []).append(res_id)

        return dict(
            (lang, (self.with_context(lang=lang) if lang else self, lang_res_ids))
            for lang, lang_res_ids in lang_to_res_ids.items()
        )

    def _render_field(self, field, res_ids, engine='inline_template',
                      compute_lang=False, set_lang=False,
                      add_context=None, options=None):
        """ Given some record ids, render a template located on field on all
        records. ``field`` should be a field of self (i.e. ``body_html`` on
        ``mail.template``). res_ids are record IDs linked to ``model`` field
        on self.

        :param field: a field name existing on self;
        :param list res_ids: list of ids of records (all belonging to same model
          defined by ``self.render_model``)
        :param string engine: inline_template, qweb, or qweb_view;

        :param boolean compute_lang: compute language to render on translated
          version of the template instead of default (probably english) one.
          Language will be computed based on ``self.lang``;
        :param string set_lang: force language for rendering. It should be a
          valid lang code matching an activate res.lang. Checked only if
          ``compute_lang`` is False;

        :param dict add_context: additional context to give to renderer;
        :param dict options: options for rendering. Use in this method and also
          propagated to rendering sub-methods. Base values come from the field
          (coming from ``render_options`` parameter) and are updated by this
          optional dictionary. May contain notably

            boolean post_process: perform a post processing on rendered result
            (notably html links management). See``_render_template_postprocess``;
            boolean preserve_comments: if set, comments are preserved. Default
            behavior is to remove them. It is used notably for browser-specific
            code implemented like comments;

        :return: {res_id: string of rendered template based on record}
        :rtype: dict
        """
        if field not in self:
            raise ValueError(
                _('Rendering of %(field_name)s is not possible as not defined on template.',
                  field_name=field
                 )
            )
        self.ensure_one()
        if compute_lang:
            templates_res_ids = self._classify_per_lang(res_ids)
        elif set_lang:
            templates_res_ids = {set_lang: (self.with_context(lang=set_lang), res_ids)}
        else:
            templates_res_ids = {self._context.get('lang'): (self, res_ids)}

        # rendering options (update default defined on field by asked options)
        f = self._fields[field]
        if hasattr(f, 'render_engine') and f.render_engine:
            engine = f.render_engine

        render_options = options.copy() if options else {}
        if hasattr(f, 'render_options') and f.render_options:
            render_options = {**f.render_options, **render_options}

        return {
            res_id: rendered
            for (template, tpl_res_ids) in templates_res_ids.values()
            for res_id, rendered in template._render_template(
                template[field],
                template.render_model,
                tpl_res_ids,
                engine=engine,
                add_context=add_context,
                options=render_options,
            ).items()
        }
