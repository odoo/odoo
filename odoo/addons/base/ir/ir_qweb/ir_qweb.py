# -*- coding: utf-8 -*-
from __future__ import print_function
import ast
import json
import logging
from collections import OrderedDict
from time import time

from lxml import html
from lxml import etree
from werkzeug import urls

from odoo.tools import pycompat

from odoo import api, models, tools
from odoo.tools.safe_eval import assert_valid_codeobj, _BUILTINS, _SAFE_OPCODES
from odoo.http import request
from odoo.modules.module import get_resource_path

from .qweb import QWeb, Contextifier
from .assetsbundle import AssetsBundle

_logger = logging.getLogger(__name__)


class IrQWeb(models.AbstractModel, QWeb):
    """ Base QWeb rendering engine
    * to customize ``t-field`` rendering, subclass ``ir.qweb.field`` and
      create new models called :samp:`ir.qweb.field.{widget}`
    Beware that if you need extensions or alterations which could be
    incompatible with other subsystems, you should create a local object
    inheriting from ``ir.qweb`` and customize that.
    """

    _name = 'ir.qweb'

    @api.model
    def render(self, id_or_xml_id, values=None, **options):
        """ render(id_or_xml_id, values, **options)

        Render the template specified by the given name.

        :param id_or_xml_id: name or etree (see get_template)
        :param dict values: template values to be used for rendering
        :param options: used to compile the template (the dict available for the rendering is frozen)
            * ``load`` (function) overrides the load method
            * ``profile`` (float) profile the rendering (use astor lib) (filter
              profile line with time ms >= profile)
        """
        for method in dir(self):
            if method.startswith('render_'):
                _logger.warning("Unused method '%s' is found in ir.qweb." % method)

        context = dict(self.env.context, dev_mode='qweb' in tools.config['dev_mode'])
        context.update(options)

        return super(IrQWeb, self).render(id_or_xml_id, values=values, **context)

    def default_values(self):
        """ attributes add to the values for each computed template
        """
        default = super(IrQWeb, self).default_values()
        default.update(request=request, cache_assets=round(time()/180), true=True, false=False) # true and false added for backward compatibility to remove after v10
        return default

    # assume cache will be invalidated by third party on write to ir.ui.view
    def _get_template_cache_keys(self):
        """ Return the list of context keys to use for caching ``_get_template``. """
        return ['lang', 'inherit_branding', 'editable', 'translatable', 'edit_translations', 'website_id']

    # apply ormcache_context decorator unless in dev mode...
    @tools.conditional(
        'xml' not in tools.config['dev_mode'],
        tools.ormcache('id_or_xml_id', 'tuple(options.get(k) for k in self._get_template_cache_keys())'),
    )
    def compile(self, id_or_xml_id, options):
        return super(IrQWeb, self).compile(id_or_xml_id, options=options)

    def load(self, name, options):
        lang = options.get('lang', 'en_US')
        env = self.env
        if lang != env.context.get('lang'):
            env = env(context=dict(env.context, lang=lang))

        template = env['ir.ui.view'].read_template(name)

        # QWeb's `read_template` will check if one of the first children of
        # what we send to it has a "t-name" attribute having `name` as value
        # to consider it has found it. As it'll never be the case when working
        # with view ids or children view or children primary views, force it here.
        def is_child_view(view_name):
            view_id = self.env['ir.ui.view'].get_view_id(view_name)
            view = self.env['ir.ui.view'].browse(view_id)
            return view.inherit_id is not None

        if isinstance(name, pycompat.integer_types) or is_child_view(name):
            for node in etree.fromstring(template):
                if node.get('t-name'):
                    node.set('t-name', str(name))
                    return node.getparent()
            return None  # trigger "template not found" in QWeb
        else:
            return template

    # order

    def _directives_eval_order(self):
        directives = super(IrQWeb, self)._directives_eval_order()
        directives.insert(directives.index('call'), 'lang')
        directives.insert(directives.index('field'), 'call-assets')
        return directives

    # compile directives

    def _compile_directive_lang(self, el, options):
        lang = el.attrib.pop('t-lang', 'en_US')
        if el.get('t-call-options'):
            el.set('t-call-options', el.get('t-call-options')[0:-1] + u', "lang": %s}' % lang)
        else:
            el.set('t-call-options', u'{"lang": %s}' % lang)
        return self._compile_node(el, options)

    def _compile_directive_call_assets(self, el, options):
        """ This special 't-call' tag can be used in order to aggregate/minify javascript and css assets"""
        if len(el):
            raise SyntaxError("t-call-assets cannot contain children nodes")

        # nodes = self._get_asset(xmlid, options, css=css, js=js, debug=values.get('debug'), async=async, values=values)
        #
        # for index, (tagName, t_attrs, content) in enumerate(nodes):
        #     if index:
        #         append('\n        ')
        #     append('<')
        #     append(tagName)
        #
        #     self._post_processing_att(tagName, t_attrs, options)
        #     for name, value in t_attrs.items():
        #         if value or isinstance(value, string_types)):
        #             append(u' ')
        #             append(name)
        #             append(u'="')
        #             append(escape(pycompat.to_text((value)))
        #             append(u'"')
        #
        #     if not content and tagName in self._void_elements:
        #         append('/>')
        #     else:
        #         append('>')
        #         if content:
        #           append(content)
        #         append('</')
        #         append(tagName)
        #         append('>')
        #
        space = el.getprevious() is not None and el.getprevious().tail or el.getparent().text
        sep = u'\n' + space.rsplit('\n').pop()
        return [
            ast.Assign(
                targets=[ast.Name(id='nodes', ctx=ast.Store())],
                value=ast.Call(
                    func=ast.Attribute(
                        value=ast.Name(id='self', ctx=ast.Load()),
                        attr='_get_asset_nodes',
                        ctx=ast.Load()
                    ),
                    args=[
                        ast.Str(el.get('t-call-assets')),
                        ast.Name(id='options', ctx=ast.Load()),
                    ],
                    keywords=[
                        ast.keyword('css', self._get_attr_bool(el.get('t-css', True))),
                        ast.keyword('js', self._get_attr_bool(el.get('t-js', True))),
                        ast.keyword('debug', ast.Call(
                            func=ast.Attribute(
                                value=ast.Name(id='values', ctx=ast.Load()),
                                attr='get',
                                ctx=ast.Load()
                            ),
                            args=[ast.Str('debug')],
                            keywords=[], starargs=None, kwargs=None
                        )),
                        ast.keyword('async', self._get_attr_bool(el.get('async', False))),
                        ast.keyword('values', ast.Name(id='values', ctx=ast.Load())),
                    ],
                    starargs=None, kwargs=None
                )
            ),
            ast.For(
                target=ast.Tuple(elts=[
                    ast.Name(id='index', ctx=ast.Store()),
                    ast.Tuple(elts=[
                        ast.Name(id='tagName', ctx=ast.Store()),
                        ast.Name(id='t_attrs', ctx=ast.Store()),
                        ast.Name(id='content', ctx=ast.Store())
                    ], ctx=ast.Store())
                ], ctx=ast.Store()),
                iter=ast.Call(
                    func=ast.Name(id='enumerate', ctx=ast.Load()),
                    args=[ast.Name(id='nodes', ctx=ast.Load())],
                    keywords=[],
                    starargs=None, kwargs=None
                ),
                body=[
                    ast.If(
                        test=ast.Name(id='index', ctx=ast.Load()),
                        body=[self._append(ast.Str(sep))],
                        orelse=[]
                    ),
                    self._append(ast.Str(u'<')),
                    self._append(ast.Name(id='tagName', ctx=ast.Load())),
                ] + self._append_attributes() + [
                    ast.If(
                        test=ast.BoolOp(
                            op=ast.And(),
                            values=[
                                ast.UnaryOp(ast.Not(), ast.Name(id='content', ctx=ast.Load()), lineno=0, col_offset=0),
                                ast.Compare(
                                    left=ast.Name(id='tagName', ctx=ast.Load()),
                                    ops=[ast.In()],
                                    comparators=[ast.Attribute(
                                        value=ast.Name(id='self', ctx=ast.Load()),
                                        attr='_void_elements',
                                        ctx=ast.Load()
                                    )]
                                ),
                            ]
                        ),
                        body=[self._append(ast.Str(u'/>'))],
                        orelse=[
                            self._append(ast.Str(u'>')),
                            ast.If(
                                test=ast.Name(id='content', ctx=ast.Load()),
                                body=[self._append(ast.Name(id='content', ctx=ast.Load()))],
                                orelse=[]
                            ),
                            self._append(ast.Str(u'</')),
                            self._append(ast.Name(id='tagName', ctx=ast.Load())),
                            self._append(ast.Str(u'>')),
                        ]
                    )
                ],
                orelse=[]
            )
        ]

    # for backward compatibility to remove after v10
    def _compile_widget_options(self, el, directive_type):
        field_options = super(IrQWeb, self)._compile_widget_options(el, directive_type)

        if ('t-%s-options' % directive_type) in el.attrib:
            if tools.config['dev_mode']:
                _logger.warning("Use new syntax t-options instead of t-%s-options" % directive_type)
            if not field_options:
                field_options = el.attrib.pop('t-%s-options' % directive_type)

        if field_options and 'monetary' in field_options:
            try:
                options = "{'widget': 'monetary'"
                for k, v in json.loads(field_options).items():
                    if k in ('display_currency', 'from_currency'):
                        options = "%s, '%s': %s" % (options, k, v)
                    else:
                        options = "%s, '%s': '%s'" % (options, k, v)
                options = "%s}" % options
                field_options = options
                _logger.warning("Use new syntax for '%s' monetary widget t-options (python dict instead of deprecated JSON syntax)." % etree.tostring(el))
            except ValueError:
                pass

        return field_options
    # end backward

    # method called by computing code

    def get_asset_bundle(self, xmlid, files, remains=None, env=None):
        return AssetsBundle(xmlid, files, remains=remains, env=env)

    # compatibility to remove after v11 - DEPRECATED
    @tools.conditional(
        'xml' not in tools.config['dev_mode'],
        tools.ormcache_context('xmlid', 'options.get("lang", "en_US")', 'css', 'js', 'debug', 'kw.get("async")', 'async_load', keys=("website_id",)),
    )
    def _get_asset(self, xmlid, options, css=True, js=True, debug=False, async_load=False, values=None, **kw):
        if 'async' in kw:
            async_load = kw['async']
        files, remains = self._get_asset_content(xmlid, options)
        asset = self.get_asset_bundle(xmlid, files, remains, env=self.env)
        return asset.to_html(css=css, js=js, debug=debug, async_load=async_load, url_for=(values or {}).get('url_for', lambda url: url))

    @tools.conditional(
        # in non-xml-debug mode we want assets to be cached forever, and the admin can force a cache clear
        # by restarting the server after updating the source code (or using the "Clear server cache" in debug tools)
        'xml' not in tools.config['dev_mode'],
        tools.ormcache_context('xmlid', 'options.get("lang", "en_US")', 'css', 'js', 'debug', 'kw.get("async")', 'async_load', keys=("website_id",)),
    )
    def _get_asset_nodes(self, xmlid, options, css=True, js=True, debug=False, async_load=False, values=None, **kw):
        if 'async' in kw:
            async_load = kw['async']
        files, remains = self._get_asset_content(xmlid, options)
        asset = self.get_asset_bundle(xmlid, files, env=self.env)
        remains = [node for node in remains if (css and node[0] == 'link') or (js and node[0] != 'link')]
        return remains + asset.to_node(css=css, js=js, debug=debug, async_load=async_load)

    @tools.ormcache_context('xmlid', 'options.get("lang", "en_US")', keys=("website_id",))
    def _get_asset_content(self, xmlid, options):
        options = dict(options,
            inherit_branding=False, inherit_branding_auto=False,
            edit_translations=False, translatable=False,
            rendering_bundle=True)

        env = self.env(context=options)

        def can_aggregate(url):
            return not urls.url_parse(url).scheme and not urls.url_parse(url).netloc and not url.startswith('/web/content')

        # TODO: This helper can be used by any template that wants to embedd the backend.
        #       It is currently necessary because the ir.ui.view bundle inheritance does not
        #       match the module dependency graph.
        def get_modules_order():
            if request:
                from odoo.addons.web.controllers.main import module_boot
                return json.dumps(module_boot())
            return '[]'
        template = env['ir.qweb'].render(xmlid, {"get_modules_order": get_modules_order})

        files = []
        remains = []
        for el in html.fragments_fromstring(template):
            if isinstance(el, html.HtmlElement):
                href = el.get('href', '')
                src = el.get('src', '')
                atype = el.get('type')
                media = el.get('media')

                if can_aggregate(href) and (el.tag == 'style' or (el.tag == 'link' and el.get('rel') == 'stylesheet')):
                    if href.endswith('.sass'):
                        atype = 'text/sass'
                    elif href.endswith('.less'):
                        atype = 'text/less'
                    if atype not in ('text/less', 'text/sass'):
                        atype = 'text/css'
                    path = [segment for segment in href.split('/') if segment]
                    filename = get_resource_path(*path) if path else None
                    files.append({'atype': atype, 'url': href, 'filename': filename, 'content': el.text, 'media': media})
                elif can_aggregate(src) and el.tag == 'script':
                    atype = 'text/javascript'
                    path = [segment for segment in href.split('/') if segment]
                    filename = get_resource_path(*path) if path else None
                    files.append({'atype': atype, 'url': src, 'filename': filename, 'content': el.text, 'media': media})
                else:
                    remains.append((el.tag, OrderedDict(el.attrib), el.text))
            else:
                # the other cases are ignored
                pass

        return (files, remains)

    def _get_field(self, record, field_name, expression, tagName, field_options, options, values):
        field = record._fields[field_name]

        # adds template compile options for rendering fields
        field_options['template_options'] = options

        # adds generic field options
        field_options['tagName'] = tagName
        field_options['expression'] = expression
        field_options['type'] = field_options.get('widget', field.type)
        inherit_branding = options.get('inherit_branding', options.get('inherit_branding_auto') and record.check_access_rights('write', False))
        field_options['inherit_branding'] = inherit_branding
        translate = options.get('edit_translations') and options.get('translatable') and field.translate
        field_options['translate'] = translate

        # field converter
        model = 'ir.qweb.field.' + field_options['type']
        converter = self.env[model] if model in self.env else self.env['ir.qweb.field']

        # get content
        content = converter.record_to_html(record, field_name, field_options)
        attributes = converter.attributes(record, field_name, field_options, values)

        return (attributes, content, inherit_branding or translate)

    def _get_widget(self, value, expression, tagName, field_options, options, values):
        # adds template compile options for rendering fields
        field_options['template_options'] = options

        field_options['type'] = field_options['widget']
        field_options['tagName'] = tagName
        field_options['expression'] = expression

        # field converter
        model = 'ir.qweb.field.' + field_options['type']
        converter = self.env[model] if model in self.env else self.env['ir.qweb.field']

        # get content
        content = converter.value_to_html(value, field_options)
        attributes = OrderedDict()
        attributes['data-oe-type'] = field_options['type']
        attributes['data-oe-expression'] = field_options['expression']

        return (attributes, content, None)

    # compile expression add safe_eval

    def _compile_expr(self, expr):
        """ Compiles a purported Python expression to ast, verifies that it's safe
        (according to safe_eval's semantics) and alter its variable references to
        access values data instead
        """
        # string must be stripped otherwise whitespace before the start for
        # formatting purpose are going to break parse/compile
        st = ast.parse(expr.strip(), mode='eval')
        assert_valid_codeobj(
            _SAFE_OPCODES,
            compile(st, '<>', 'eval'), # could be expr, but eval *should* be fine
            expr
        )

        # ast.Expression().body -> expr
        return Contextifier(_BUILTINS).visit(st).body

    def _get_attr_bool(self, attr, default=False):
        if attr:
            if attr is True:
                return ast.Name(id='True', ctx=ast.Load())
            attr = attr.lower()
            if attr in ('false', '0'):
                return ast.Name(id='False', ctx=ast.Load())
            elif attr in ('true', '1'):
                return ast.Name(id='True', ctx=ast.Load())
        return ast.Name(id=str(attr if attr is False else default), ctx=ast.Load())
