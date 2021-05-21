# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import babel
import copy
import functools
import logging
import re

import dateutil.relativedelta as relativedelta
from lxml import html
from markupsafe import Markup
from werkzeug import urls

from odoo import _, api, fields, models, tools
from odoo.exceptions import UserError
from odoo.tools import is_html_empty, safe_eval

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

def relativedelta_proxy(*args, **kwargs):
    # dateutil.relativedelta is an old-style class and cannot be directly
    # instanciated wihtin a jinja2 expression, so a lambda "proxy" is
    # is needed, apparently
    return relativedelta.relativedelta(*args, **kwargs)

template_env_globals = {
    'str': str,
    'quote': urls.url_quote,
    'urlencode': urls.url_encode,
    'datetime': safe_eval.datetime,
    'len': len,
    'abs': abs,
    'min': min,
    'max': max,
    'sum': sum,
    'filter': filter,
    'reduce': functools.reduce,
    'map': map,
    'relativedelta': relativedelta_proxy,
    'round': round,
}

try:
    # We use a jinja2 sandboxed environment to render mako templates.
    # Note that the rendering does not cover all the mako syntax, in particular
    # arbitrary Python statements are not accepted, and not all expressions are
    # allowed: only "public" attributes (not starting with '_') of objects may
    # be accessed.
    # This is done on purpose: it prevents incidental or malicious execution of
    # Python code that may break the security of the server.
    from jinja2.sandbox import SandboxedEnvironment
    jinja_template_env = SandboxedEnvironment(
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
    jinja_template_env.globals.update(template_env_globals)
    jinja_safe_template_env = copy.copy(jinja_template_env)
    jinja_safe_template_env.autoescape = False
except ImportError:
    _logger.warning("jinja2 not available, templating features will not work!")


class MailRenderMixin(models.AbstractModel):
    _name = 'mail.render.mixin'
    _description = 'Mail Render Mixin'

    # language for rendering
    lang = fields.Char(
        'Language',
        help="Optional translation language (ISO code) to select when sending out an email. "
             "If not set, the english version will be used. This should usually be a placeholder expression "
             "that provides the appropriate language, e.g. ${object.partner_id.lang}.")
    # rendering context
    render_model = fields.Char("Rendering Model", compute='_compute_render_model', store=False)
    # expression builder
    model_object_field = fields.Many2one(
        'ir.model.fields', string="Field", store=False,
        help="Select target field from the related document model.\n"
             "If it is a relationship field you will be able to select "
             "a target field at the destination of the relationship.")
    sub_object = fields.Many2one(
        'ir.model', 'Sub-model', readonly=True, store=False,
        help="When a relationship field is selected as first field, "
             "this field shows the document model the relationship goes to.")
    sub_model_object_field = fields.Many2one(
        'ir.model.fields', 'Sub-field', store=False,
        help="When a relationship field is selected as first field, "
             "this field lets you select the target field within the "
             "destination document model (sub-model).")
    null_value = fields.Char('Default Value', store=False, help="Optional value to use if the target field is empty")
    copyvalue = fields.Char(
        'Placeholder Expression', store=False,
        help="Final placeholder expression, to be copy-pasted in the desired template field.")

    def _compute_render_model(self):
        """ Give the target model for rendering. Void by default as models
        inheriting from ``mail.render.mixin`` should define how to find this
        model. """
        self.render_model = False

    @api.onchange('model_object_field', 'sub_model_object_field', 'null_value')
    def _onchange_dynamic_placeholder(self):
        """ Generate the dynamic placeholder """
        if self.model_object_field:
            if self.model_object_field.ttype in ['many2one', 'one2many', 'many2many']:
                model = self.env['ir.model']._get(self.model_object_field.relation)
                if model:
                    self.sub_object = model.id
                    sub_field_name = self.sub_model_object_field.name
                    self.copyvalue = self._build_expression(self.model_object_field.name,
                                                            sub_field_name, self.null_value or False)
            else:
                self.sub_object = False
                self.sub_model_object_field = False
                self.copyvalue = self._build_expression(self.model_object_field.name, False, self.null_value or False)
        else:
            self.sub_object = False
            self.copyvalue = False
            self.sub_model_object_field = False
            self.null_value = False

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
            expression = "${object." + field_name
            if sub_field_name:
                expression += "." + sub_field_name
            if null_value:
                expression += " or '''%s'''" % null_value
            expression += "}"
        return expression

    # ------------------------------------------------------------
    # ORM
    # ------------------------------------------------------------

    def _valid_field_parameter(self, field, name):
        # allow specifying rendering options directly from field when using the render mixin
        return name in ['render_engine', 'render_options'] or super()._valid_field_parameter(field, name)

    # ------------------------------------------------------------
    # TOOLS
    # ------------------------------------------------------------

    def _replace_local_links(self, html, base_url=None):
        """ Replace local links by absolute links. It is required in various
        cases, for example when sending emails on chatter or sending mass
        mailings. It replaces

         * href of links (mailto will not match the regex)
         * src of images (base64 hardcoded data will not match the regex)
         * styling using url like background-image: url

        It is done using regex because it is shorten than using an html parser
        to create a potentially complex soupe and hope to have a result that
        has not been harmed.
        """
        if not html:
            return html

        wrapper = Markup if isinstance(html, Markup) else str
        html = tools.ustr(html)
        if isinstance(html, Markup):
            wrapper = Markup

        def _sub_relative2absolute(match):
            # compute here to do it only if really necessary + cache will ensure it is done only once
            # if not base_url
            if not _sub_relative2absolute.base_url:
                _sub_relative2absolute.base_url = self.env["ir.config_parameter"].sudo().get_param("web.base.url")
            return match.group(1) + urls.url_join(_sub_relative2absolute.base_url, match.group(2))

        _sub_relative2absolute.base_url = base_url
        html = re.sub(r"""(<img(?=\s)[^>]*\ssrc=")(/[^/][^"]+)""", _sub_relative2absolute, html)
        html = re.sub(r"""(<a(?=\s)[^>]*\shref=")(/[^/][^"]+)""", _sub_relative2absolute, html)
        html = re.sub(r"""(<[^>]+\bstyle="[^"]+\burl\('?)(/[^/'][^'")]+)""", _sub_relative2absolute, html)

        return wrapper(html)

    @api.model
    def _render_encapsulate(self, layout_xmlid, html, add_context=None, context_record=None):
        try:
            template = self.env.ref(layout_xmlid, raise_if_not_found=True)
        except ValueError:
            _logger.warning('QWeb template %s not found when rendering encapsulation template.' % (layout_xmlid))
        else:
            record_name = context_record.display_name if context_record else ''
            model_description = self.env['ir.model']._get(context_record._name).display_name if context_record else False
            template_ctx = {
                'body': html,
                'record_name': record_name,
                'model_description': model_description,
                'company': context_record['company_id'] if (context_record and 'company_id' in context_record) else self.env.company,
                'record': context_record,
            }
            if add_context:
                template_ctx.update(**add_context)

            html = template._render(template_ctx, engine='ir.qweb', minimal_qcontext=True)
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

        if preview:
            html_preview = Markup("""
                <div style="display:none;font-size:1px;height:0px;width:0px;opacity:0;">
                   {}
                </div>
            """).format(preview)
            return tools.prepend_html_content(html, html_preview)
        return html

    # ------------------------------------------------------------
    # RENDERING
    # ------------------------------------------------------------

    @api.model
    def _get_common_eval_context(self):
        """ Evaluation context used in all rendering engines. Contains

          * ``user``: current user browse record;
          * ``ctx```: current context;
          * various formatting tools;
        """
        return {
            'format_date': lambda date, date_format=False, lang_code=False: format_date(self.env, date, date_format, lang_code),
            'format_datetime': lambda dt, tz=False, dt_format=False, lang_code=False: format_datetime(self.env, dt, tz, dt_format, lang_code),
            'format_time': lambda time, tz=False, time_format=False, lang_code=False: format_time(self.env, time, tz, time_format, lang_code),
            'format_amount': lambda amount, currency, lang_code=False: tools.format_amount(self.env, amount, currency, lang_code),
            'format_duration': lambda value: tools.format_duration(value),
            'user': self.env.user,
            'ctx': self._context,
            'is_html_empty': is_html_empty,
        }

    @api.model
    def _render_qweb_eval_context(self):
        """ Prepare qweb evaluation context, containing common context with
        some specific values for Qweb. """
        render_context = self._get_common_eval_context()
        render_context.update(copy.copy(template_env_globals))
        return render_context

    @api.model
    def _render_template_qweb(self, template_src, model, res_ids,
                              add_context=None, options=None):
        """ Render a raw QWeb template.

        :param str template_src: raw QWeb template to render;
        :param str model: see ``MailRenderMixin._render_template()``;
        :param list res_ids: see ``MailRenderMixin._render_template()``;

        :param dict add_context: additional context to give to renderer. It
          allows to add or update values to base rendering context generated
          by ``MailRenderMixin._render_qweb_eval_context()``;
        :param dict options: options for rendering (not used currently);

        :return dict: {res_id: string of rendered template based on record}

        :notice: Experimental. Use at your own risks only.
        """
        results = dict.fromkeys(res_ids, u"")

        # prepare template variables
        variables = self._render_qweb_eval_context()
        if add_context:
            variables.update(**add_context)

        for record in self.env[model].browse(res_ids):
            variables['object'] = record
            try:
                render_result = self.env['ir.qweb']._render(html.fragment_fromstring(template_src), variables)
            except Exception as e:
                _logger.info("Failed to render template : %s", template_src, exc_info=True)
                raise UserError(_("Failed to render QWeb template : %s)", e))
            results[record.id] = render_result

        return results

    @api.model
    def _render_template_qweb_view(self, template_src, model, res_ids,
                                   add_context=None, options=None):
        """ Render a QWeb template based on an ir.ui.view content.

        In addition to the generic evaluation context available, some other
        variables are added:
          * ``object``: record based on which the template is rendered;

        :param str template_src: source QWeb template. It should be a string
          XmlID allowing to fetch an ``ir.ui.view``;
        :param str model: see ``MailRenderMixin._render_template()``;
        :param list res_ids: see ``MailRenderMixin._render_template()``;

        :param dict add_context: additional context to give to renderer. It
          allows to add or update values to base rendering context generated
          by ``MailRenderMixin._render_qweb_eval_context()``;
        :param dict options: options for rendering (not used currently);

        :return dict: {res_id: string of rendered template based on record}
        """
        # prevent wrong values (rendering on a void record set, ...)
        if any(r is None for r in res_ids):
            raise ValueError(_('Template rendering should be called on a valid record IDs.'))

        view = self.env.ref(template_src, raise_if_not_found=False) or self.env['ir.ui.view']
        results = dict.fromkeys(res_ids, u"")
        if not view:
            return results

        # prepare template variables
        variables = self._render_qweb_eval_context()
        if add_context:
            variables.update(**add_context)
        safe_eval.check_values(variables)

        for record in self.env[model].browse(res_ids):
            variables['object'] = record
            try:
                render_result = view._render(variables, engine='ir.qweb', minimal_qcontext=True)
            except Exception as e:
                _logger.info("Failed to render template : %s (%d)", template_src, view.id, exc_info=True)
                raise UserError(_("Failed to render template : %(xml_id)s (%(view_id)d)",
                                  xml_id=template_src,
                                  view_id=view.id))
            results[record.id] = render_result

        return results

    @api.model
    def _render_jinja_eval_context(self):
        return self._get_common_eval_context()

    @api.model
    def _render_template_jinja(self, template_txt, model, res_ids,
                               add_context=None, options=None):
        """ Render a string-based template on records given by a model and a list
        of IDs, using jinja.

        In addition to the generic evaluation context available, some other
        variables are added:
          * ``object``: record based on which the template is rendered;

        :param str template_txt: template text to render
        :param str model: see ``MailRenderMixin._render_template()``;
        :param list res_ids: see ``MailRenderMixin._render_template()``;

        :param dict add_context: additional context to give to renderer. It
          allows to add or update values to base rendering context generated
          by ``MailRenderMixin._render_jinja_eval_context()``;
        :param dict options: options for rendering;

        :return dict: {res_id: string of rendered template based on record}
        """
        # prevent wrong values (rendering on a void record set, ...)
        if any(r is None for r in res_ids):
            raise ValueError(_('Template rendering should be called on a valid record IDs.'))

        # TDE note: support 'safe' context key as backward compatibility for 6dde919bb9850912f618b561cd2141bffe41340c
        if options is None:
            options = {}
        no_autoescape = options.get('render_safe') or self._context.get('safe')

        results = dict.fromkeys(res_ids, u"")
        if not template_txt:
            return results

        # try to load the template
        try:
            jinja_env = jinja_safe_template_env if no_autoescape else jinja_template_env
            template = jinja_env.from_string(tools.ustr(template_txt))
        except Exception:
            _logger.info("Failed to load template %r", template_txt, exc_info=True)
            return results

        # prepare template variables
        variables = self._render_jinja_eval_context()
        if add_context:
            variables.update(**add_context)
        safe_eval.check_values(variables)


        for record in self.env[model].browse(res_ids):
            variables['object'] = record
            try:
                render_result = template.render(variables)
            except Exception as e:
                _logger.info("Failed to render template : %s", e, exc_info=True)
                raise UserError(_("Failed to render template : %s", e))
            if render_result == u"False":
                render_result = u""
            results[record.id] = Markup(render_result)

        return results

    @api.model
    def _render_template_postprocess(self, rendered):
        """ Tool method for post processing. In this method we ensure local
        links ('/shop/Basil-1') are replaced by global links ('https://www.
        mygarden.com/shop/Basil-1').

        :param rendered: result of ``_render_template``;

        :return dict: updated version of rendered per record ID;
        """
        for res_id, rendered_html in rendered.items():
            rendered[res_id] = self._replace_local_links(rendered_html)
        return rendered

    @api.model
    def _render_template(self, template_src, model, res_ids, engine='jinja',
                         add_context=None, options=None, post_process=False):
        """ Render the given string on records designed by model / res_ids using
        the given rendering engine. Currently only jinja or qweb are supported.

        :param str template_src: template text to render (jinja) or xml id of
          view (qweb);
        :param str model: model name of records on which we want to perform
          rendering (aka 'crm.lead');
        :param list res_ids: list of ids of records. All should belong to the
          Odoo model given by model;
        :param string engine: jinja or qweb_view;

        :param dict add_context: additional context to give to renderer. It
          allows to add or update values to base rendering context generated
          by ``MailRenderMixin._render_<engine>_eval_context()``;
        :param dict options: options for rendering;
        :param boolean post_process: perform a post processing on rendered result
          (notably html links management). See``_render_template_postprocess``;

        :return dict: {res_id: string of rendered template based on record}
        """
        if not isinstance(res_ids, (list, tuple)):
            raise ValueError(_('Template rendering should be called only using on a list of IDs.'))
        if engine not in ('jinja', 'qweb', 'qweb_view'):
            raise ValueError(_('Template rendering supports only raw jinja or qweb (view or raw).'))

        if engine == 'qweb_view':
            rendered = self._render_template_qweb_view(template_src, model, res_ids,
                                                       add_context=add_context, options=options)
        elif engine == 'qweb':
            rendered = self._render_template_qweb(template_src, model, res_ids,
                                                  add_context=add_context, options=options)
        else:
            rendered = self._render_template_jinja(template_src, model, res_ids,
                                                   add_context=add_context, options=options)
        if post_process:
            rendered = self._render_template_postprocess(rendered)

        return rendered

    def _render_lang(self, res_ids, engine='jinja'):
        """ Given some record ids, return the lang for each record based on
        lang field of template or through specific context-based key. Lang is
        computed by performing a rendering on res_ids, based on self.render_model.

        :param list res_ids: list of ids of records. All should belong to the
          Odoo model given by model;
        :param string engine: jinja or qweb_view;

        :return dict: {res_id: lang code (i.e. en_US)}
        """
        self.ensure_one()
        if not isinstance(res_ids, (list, tuple)):
            raise ValueError(_('Template rendering for language should be called with a list of IDs.'))

        rendered_langs = self._render_template(self.lang, self.render_model, res_ids, engine=engine)
        return dict(
            (res_id, lang)
            for res_id, lang in rendered_langs.items()
        )

    def _classify_per_lang(self, res_ids, engine='jinja'):
        """ Given some record ids, return for computed each lang a contextualized
        template and its subset of res_ids.

        :param list res_ids: list of ids of records (all belonging to same model
          defined by self.render_model)
        :param string engine: jinja or qweb_view;

        :return dict: {lang: (template with lang=lang_code if specific lang computed
          or template, res_ids targeted by that language}
        """
        self.ensure_one()

        if self.env.context.get('template_preview_lang'):
            return dict((res_id, self.env.context['template_preview_lang']) for res_id in res_ids)

        lang_to_res_ids = {}
        for res_id, lang in self._render_lang(res_ids, engine=engine).items():
            lang_to_res_ids.setdefault(lang, []).append(res_id)

        return dict(
            (lang, (self.with_context(lang=lang) if lang else self, lang_res_ids))
            for lang, lang_res_ids in lang_to_res_ids.items()
        )

    def _render_field(self, field, res_ids, engine='jinja',
                      compute_lang=False, set_lang=False,
                      add_context=None, options=None, post_process=False):
        """ Given some record ids, render a template located on field on all
        records. ``field`` should be a field of self (i.e. ``body_html`` on
        ``mail.template``). res_ids are record IDs linked to ``model`` field
        on self.

        :param field: a field name existing on self;
        :param list res_ids: list of ids of records (all belonging to same model
          defined by ``self.render_model``)
        :param string engine: jinja or qweb_view;

        :param boolean compute_lang: compute language to render on translated
          version of the template instead of default (probably english) one.
          Language will be computed based on ``self.lang``;
        :param string set_lang: force language for rendering. It should be a
          valid lang code matching an activate res.lang. Checked only if
          ``compute_lang`` is False;
        :param dict add_context: additional context to give to renderer;
        :param dict options: options for rendering;
        :param boolean post_process: perform a post processing on rendered result
          (notably html links management). See``_render_template_postprocess``);

        :return dict: {res_id: string of rendered template based on record}
        """
        if options is None:
            options = {}

        self.ensure_one()
        if compute_lang:
            templates_res_ids = self._classify_per_lang(res_ids)
        elif set_lang:
            templates_res_ids = {set_lang: (self.with_context(lang=set_lang), res_ids)}
        else:
            templates_res_ids = {self._context.get('lang'): (self, res_ids)}

        # rendering options
        engine = getattr(self._fields[field], 'render_engine', engine)
        options.update(**getattr(self._fields[field], 'render_options', {}))
        post_process = options.get('post_process') or post_process

        return dict(
            (res_id, rendered)
            for lang, (template, tpl_res_ids) in templates_res_ids.items()
            for res_id, rendered in template._render_template(
                template[field], template.render_model, tpl_res_ids, engine=engine,
                add_context=add_context, options=options, post_process=post_process
            ).items()
        )
