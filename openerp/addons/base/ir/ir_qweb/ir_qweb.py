# -*- coding: utf-8 -*-
import ast
from urlparse import urlparse
from lxml import html
import math

from .qweb import QWeb, Contextifier
from .assetsbundle import AssetsBundle
from lxml import etree

from openerp import api, models, tools
from openerp.tools import safe_eval
from openerp.addons.web.http import request
import json

import logging
_logger = logging.getLogger(__name__)


class ir_QWeb(models.AbstractModel, QWeb):
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
        """ render(id_or_xml_id, values=None, **options)
        Renders the template specified by the provided template name
        :param values: context for rendering the template
        :type values: dict or :class:`values` instance
        """
        for method in dir(self):
            if method.startswith('render_'):
                _logger.warning("Unused method '%s' is found in ir.qweb." % method)

        body = []

        import time
        _ = []
        ap = _.append
        t = time.time()
        def append(data):
            ap([time.time()-t, data])
            body.append(data)

        context = dict(self.env.context, dev_mode='qweb' in tools.config['dev_mode'])
        context.update(options)

        self.compile(id_or_xml_id, context)(self, append, values or {})

        # t = _[0][0]
        # for v in _:
        #     print round((v[0]-t)*1000000)/1000, v[1]

        return u''.join(body)

    # assume cache will be invalidated by third party on write to ir.ui.view
    def _get_template_cache_keys(self):
        """ Return the list of context keys to use for caching ``_get_template``. """
        return ['lang', 'inherit_branding', 'editable', 'translatable', 'edit_translations']

    # apply ormcache_context decorator unless in dev mode...
    @tools.conditional(
        'xml' not in tools.config['dev_mode'],
        tools.ormcache('id_or_xml_id', 'tuple(map(options.get, self._get_template_cache_keys()))'),
    )
    def compile(self, id_or_xml_id, options):
        return super(ir_QWeb, self).compile(id_or_xml_id, options=options)

    def load(self, name, options):
        lang = options.get('lang', 'en_US')
        env = self.env
        if lang != env.context.get('lang'):
            env = env(context=dict(env.context, lang=lang))
        template = env['ir.ui.view'].read_template(name)

        res_id = isinstance(name, (int, long)) and name or None
        if res_id:
            for node in etree.fromstring(template):
                if node.get('t-name'):
                    return node
                elif res_id and node.tag == "t":
                    node.set('t-name', str(res_id))
                    return node

        return template

    # order

    def _directives_eval_order(self):
        directives = super(ir_QWeb, self)._directives_eval_order()
        directives.insert(directives.index('call'), 'lang')
        directives.insert(directives.index('field'), 'call-assets')
        return directives

    # compile directives

    def _compile_directive_lang(self, el, options):
        el.set('t-call-options', '{"lang": %s}' % el.attrib.pop('t-lang', 'en_US'))
        return self._compile_node(el, options)

    def _compile_directive_call_assets(self, el, options):
        """ This special 't-call' tag can be used in order to aggregate/minify javascript and css assets"""
        if len(el):
            raise "t-call-assets cannot contain children nodes"

        # self._get_asset(xmlid, options).to_html(css, js, debug, async, values)
        return [
            self._append(ast.Call(
                func=ast.Attribute(
                    value=ast.Call(
                        func=ast.Attribute(
                            value=ast.Name(id='self', ctx=ast.Load()),
                            attr='_get_asset',
                            ctx=ast.Load()
                        ),
                        args=[
                            ast.Str(el.get('t-call-assets')),
                            ast.Name(id='options', ctx=ast.Load()),
                        ],
                        keywords=[], starargs=None, kwargs=None
                    ),
                    attr='to_html',
                    ctx=ast.Load()
                ),
                args=[],
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
            ))
        ]

    # method called by computing code

    def _get_asset(self, xmlid, options):
        files, remains = self._get_asset_content(xmlid, options)
        return AssetsBundle(xmlid, files, remains, env=self.env)

    @tools.ormcache('xmlid', 'options["lang"]')
    def _get_asset_content(self, xmlid, options):
        options = dict(options,
            inherit_branding=False, inherit_branding_auto=False,
            edit_translations=False, translatable=False,
            rendering_bundle=True)

        env = self.env(context=options)

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
            if isinstance(el, basestring):
                remains.append(el)
            elif isinstance(el, html.HtmlElement):
                href = el.get('href', '')
                atype = el.get('type')
                media = el.get('media')

                can_aggregate = not urlparse(href).netloc and not href.startswith('/web/content')
                if el.tag == 'style' or (el.tag == 'link' and el.get('rel') == 'stylesheet' and can_aggregate):
                    if href.endswith('.sass'):
                        atype = 'text/sass'
                    elif href.endswith('.less'):
                        atype = 'text/less'
                    if atype not in ('text/less', 'text/sass'):
                        atype = 'text/css'
                    files.append({'atype': atype, 'url': href, 'content': el.text, 'media': media})
                elif el.tag == 'script':
                    atype = 'text/javascript'
                    files.append({'atype': atype, 'url': el.get('src', ''), 'content': el.text, 'media': media})
                else:
                    remains.append(html.tostring(el))
            else:
                try:
                    remains.append(html.tostring(el))
                except Exception:
                    # notYETimplementederror
                    raise NotImplementedError

        return (files, remains)

    def _get_field(self, record, field_name, expression, default_content, tagName, field_options, options, values):
        field = record._fields[field_name]

        field_options['tagName'] = tagName
        field_options['expression'] = expression
        field_options['default_content'] = default_content
        field_options['type'] = field_options.get('widget', field.type)
        inherit_branding = options.get('inherit_branding', options.get('inherit_branding_auto') and record.check_access_rights('write', False))
        field_options['inherit_branding'] = inherit_branding
        translate = options.get('edit_translations') and options.get('translatable') and getattr(field, 'translate', False)
        field_options['translate'] = translate

        # field converter
        model = 'ir.qweb.field.' + field_options['type']
        converter = self.env[model] if model in self.env else self.env['ir.qweb.field']

        # get content
        content = converter.record_to_html(record, field_name, field_options, values)
        attributes = converter.attributes(record, field_name, field_options, values)

        return (attributes, content or default_content or (u"" if inherit_branding or translate else None))

    # formating methods

    def _format_func_monetary(self, value, display_currency=None, from_currency=None):
        env = display_currency.env
        precision = int(round(math.log10(display_currency.rounding)))
        fmt = "%.{0}f".format(-precision if precision < 0 else 0)
        lang = env['res.lang']._lang_get(env.context.get('lang', 'en_US'))
        formatted_amount = lang.format(fmt, value, grouping=True, monetary=True).replace(r' ', u'\N{NO-BREAK SPACE}')
        pre = post = u''
        if display_currency.position == 'before':
            pre = u'{symbol}\N{NO-BREAK SPACE}'
        else:
            post = u'\N{NO-BREAK SPACE}{symbol}'
        return u'{pre}{0}{post}'.format(
            formatted_amount, pre=pre, post=post
        ).format(symbol=display_currency.symbol,)

    # compile expression add safe_eval

    def _compile_expr(self, expr):
        """ Compiles a purported Python expression to ast, verifies that it's safe
        (according to safe_eval's semantics) and alter its variable references to
        access values data instead
        """
        # string must be stripped otherwise whitespace before the start for
        # formatting purpose are going to break parse/compile
        st = ast.parse(expr.strip(), mode='eval')
        safe_eval.assert_valid_codeobj(
            safe_eval._SAFE_OPCODES,
            compile(st, '<>', 'eval'), # could be expr, but eval *should* be fine
            expr
        )

        # ast.Expression().body -> expr
        return Contextifier().visit(st).body
