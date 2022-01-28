# -*- coding: utf-8 -*-
from __future__ import print_function
from textwrap import dedent
import copy
import io
import logging
import re
import markupsafe
import tokenize
from lxml import html, etree

from odoo import api, models, tools
from odoo.tools.safe_eval import check_values, assert_valid_codeobj, _BUILTINS, to_opcodes, _EXPR_OPCODES, _BLACKLIST
from odoo.tools.misc import get_lang
from odoo.http import request
from odoo.modules.module import get_resource_path
from odoo.tools.profiler import QwebTracker

from odoo.addons.base.models.qweb import QWeb
from odoo.addons.base.models.assetsbundle import AssetsBundle
from odoo.addons.base.models.ir_asset import can_aggregate, STYLE_EXTENSIONS, SCRIPT_EXTENSIONS

_logger = logging.getLogger(__name__)


_SAFE_QWEB_OPCODES = _EXPR_OPCODES.union(to_opcodes([
    'MAKE_FUNCTION', 'CALL_FUNCTION', 'CALL_FUNCTION_KW', 'CALL_FUNCTION_EX',
    'CALL_METHOD', 'LOAD_METHOD',

    'GET_ITER', 'FOR_ITER', 'YIELD_VALUE',
    'JUMP_FORWARD', 'JUMP_ABSOLUTE',
    'JUMP_IF_FALSE_OR_POP', 'JUMP_IF_TRUE_OR_POP', 'POP_JUMP_IF_FALSE', 'POP_JUMP_IF_TRUE',

    'LOAD_NAME', 'LOAD_ATTR',
    'LOAD_FAST', 'STORE_FAST', 'UNPACK_SEQUENCE',
    'STORE_SUBSCR',
    'LOAD_GLOBAL',
])) - _BLACKLIST


class IrQWeb(models.AbstractModel, QWeb):
    """ Base QWeb rendering engine
    * to customize ``t-field`` rendering, subclass ``ir.qweb.field`` and
      create new models called :samp:`ir.qweb.field.{widget}`
    Beware that if you need extensions or alterations which could be
    incompatible with other subsystems, you should create a local object
    inheriting from ``ir.qweb`` and customize that.
    """

    _name = 'ir.qweb'
    _description = 'Qweb'

    _available_objects = dict(_BUILTINS)
    _empty_lines = re.compile(r'\n\s*\n')

    @QwebTracker.wrap_render
    @api.model
    def _render(self, template, values=None, **options):
        """ render(template, values, **options)

        Render the template specified by the given name.

        :param template: etree, xml_id, template name (see _get_template)
            * Call the method ``load`` is not an etree.
        :param dict values: template values to be used for rendering
        :param options: used to compile the template (the dict available for the rendering is frozen)
            * ``load`` (function) overrides the load method

        :returns: bytes marked as markup-safe (decode to :class:`markupsafe.Markup`
                  instead of `str`)
        :rtype: MarkupSafe
        """
        compile_options = dict(self.env.context, dev_mode='qweb' in tools.config['dev_mode'])
        compile_options.update(options)

        result = super()._render(template, values=values, **compile_options)

        if not values or not values.get('__keep_empty_lines'):
            result = markupsafe.Markup(IrQWeb._empty_lines.sub('\n', result.strip()))

        if 'data-pagebreak=' not in result:
            return result

        fragments = html.fragments_fromstring(result)

        for fragment in fragments:
            for row in fragment.iterfind('.//tr[@data-pagebreak]'):
                table = next(row.iterancestors('table'))
                newtable = html.Element('table', attrib=dict(table.attrib))
                thead = table.find('thead')
                if thead:
                    newtable.append(copy.deepcopy(thead))
                # TODO: copy caption & tfoot as well?
                # TODO: move rows in a tbody if row.getparent() is one?

                pos = row.get('data-pagebreak')
                assert pos in ('before', 'after')
                for sibling in row.getparent().iterchildren('tr'):
                    if sibling is row:
                        if pos == 'after':
                            newtable.append(sibling)
                        break
                    newtable.append(sibling)

                table.addprevious(newtable)
                table.addprevious(html.Element('div', attrib={
                    'style': 'page-break-after: always'
                }))

        return markupsafe.Markup(''.join(html.tostring(f).decode() for f in fragments))

    # assume cache will be invalidated by third party on write to ir.ui.view
    def _get_template_cache_keys(self):
        """ Return the list of context keys to use for caching ``_get_template``. """
        return ['lang', 'inherit_branding', 'editable', 'translatable', 'edit_translations', 'website_id', 'profile', 'raise_on_code']

    # apply ormcache_context decorator unless in dev mode...
    @tools.conditional(
        'xml' not in tools.config['dev_mode'],
        tools.ormcache('id_or_xml_id', 'tuple(options.get(k) for k in self._get_template_cache_keys())'),
    )
    @QwebTracker.wrap_compile
    def _compile(self, id_or_xml_id, options):
        try:
            id_or_xml_id = int(id_or_xml_id)
        except:
            pass
        return super()._compile(id_or_xml_id, options=options)

    def _load(self, name, options):
        lang = options.get('lang', get_lang(self.env).code)
        env = self.env
        if lang != env.context.get('lang'):
            env = env(context=dict(env.context, lang=lang))

        view_id = self.env['ir.ui.view'].get_view_id(name)
        template = env['ir.ui.view'].sudo()._read_template(view_id)

        # QWeb's `_read_template` will check if one of the first children of
        # what we send to it has a "t-name" attribute having `name` as value
        # to consider it has found it. As it'll never be the case when working
        # with view ids or children view or children primary views, force it here.
        def is_child_view(view_name):
            view_id = self.env['ir.ui.view'].get_view_id(view_name)
            view = self.env['ir.ui.view'].sudo().browse(view_id)
            return view.inherit_id is not None

        if isinstance(name, int) or is_child_view(name):
            view = etree.fromstring(template)
            for node in view:
                if node.get('t-name'):
                    node.set('t-name', str(name))
            return (view, view_id)
        else:
            return (template, view_id)

    # order

    def _directives_eval_order(self):
        directives = super()._directives_eval_order()
        directives.insert(directives.index('foreach'), 'groups')
        directives.insert(directives.index('call'), 'lang')
        directives.insert(directives.index('field'), 'call-assets')
        return directives

    # compile

    def _compile_node(self, el, options, indent):
        if el.get("groups"):
            el.set("t-groups", el.attrib.pop("groups"))
        return super()._compile_node(el, options, indent)

    # compile directives

    @QwebTracker.wrap_compile_directive
    def _compile_directive(self, el, options, directive, indent):
        return super()._compile_directive(el, options, directive, indent)

    def _compile_directive_groups(self, el, options, indent):
        """Compile `t-groups` expressions into a python code as a list of
        strings.

        The code will contain the condition `if self.user_has_groups(groups)`
        part that wrap the rest of the compiled code of this element.
        """
        groups = el.attrib.pop('t-groups')
        code = self._flushText(options, indent)
        code.append(self._indent(f"if self.user_has_groups({repr(groups)}):", indent))
        code.extend(self._compile_directives(el, options, indent + 1) + self._flushText(options, indent + 1) or [self._indent('pass', indent + 1)])
        return code

    def _compile_directive_lang(self, el, options, indent):
        el.attrib['t-options-lang'] = el.attrib.pop('t-lang')
        return self._compile_node(el, options, indent)

    def _compile_directive_call_assets(self, el, options, indent):
        """ This special 't-call' tag can be used in order to aggregate/minify javascript and css assets"""
        if len(el):
            raise SyntaxError("t-call-assets cannot contain children nodes")

        code = self._flushText(options, indent)
        code.append(self._indent(dedent("""
            t_call_assets_nodes = self._get_asset_nodes(%(xmlid)s, css=%(css)s, js=%(js)s, debug=values.get("debug"), async_load=%(async_load)s, defer_load=%(defer_load)s, lazy_load=%(lazy_load)s, media=%(media)s)
            for index, (tagName, attrs, content) in enumerate(t_call_assets_nodes):
                if index:
                    yield '\\n        '
                yield '<'
                yield tagName
            """).strip() % {
                'xmlid': repr(el.get('t-call-assets')),
                'css': self._compile_bool(el.get('t-css', True)),
                'js': self._compile_bool(el.get('t-js', True)),
                'async_load': self._compile_bool(el.get('async_load', False)),
                'defer_load': self._compile_bool(el.get('defer_load', False)),
                'lazy_load': self._compile_bool(el.get('lazy_load', False)),
                'media': repr(el.get('media')) if el.get('media') else False,
            }, indent))
        code.extend(self._compile_attributes(options, indent + 1))
        code.append(self._indent(dedent("""
                if not content and tagName in self._void_elements:
                    yield '/>'
                else:
                    yield '>'
                    if content:
                      yield content
                    yield '</'
                    yield tagName
                    yield '>'
                """).strip(), indent + 1))

        return code

    # method called by computing code

    def get_asset_bundle(self, bundle_name, files, env=None, css=True, js=True):
        return AssetsBundle(bundle_name, files, env=env, css=css, js=js)

    def _get_asset_nodes(self, bundle, css=True, js=True, debug=False, async_load=False, defer_load=False, lazy_load=False, media=None):
        """Generates asset nodes.
        If debug=assets, the assets will be regenerated when a file which composes them has been modified.
        Else, the assets will be generated only once and then stored in cache.
        """
        if debug and 'assets' in debug:
            return self._generate_asset_nodes(bundle, css, js, debug, async_load, defer_load, lazy_load, media)
        else:
            return self._generate_asset_nodes_cache(bundle, css, js, debug, async_load, defer_load, lazy_load, media)

    @tools.conditional(
        # in non-xml-debug mode we want assets to be cached forever, and the admin can force a cache clear
        # by restarting the server after updating the source code (or using the "Clear server cache" in debug tools)
        'xml' not in tools.config['dev_mode'],
        tools.ormcache_context('bundle', 'css', 'js', 'debug', 'async_load', 'defer_load', 'lazy_load', keys=("website_id", "lang")),
    )
    def _generate_asset_nodes_cache(self, bundle, css=True, js=True, debug=False, async_load=False, defer_load=False, lazy_load=False, media=None):
        return self._generate_asset_nodes(bundle, css, js, debug, async_load, defer_load, lazy_load, media)

    def _generate_asset_nodes(self, bundle, css=True, js=True, debug=False, async_load=False, defer_load=False, lazy_load=False, media=None):
        nodeAttrs = None
        if css and media:
            nodeAttrs = {
                'media': media,
            }
        files, remains = self._get_asset_content(bundle, nodeAttrs, defer_load=defer_load, lazy_load=lazy_load)
        asset = self.get_asset_bundle(bundle, files, env=self.env, css=css, js=js)
        remains = [node for node in remains if (css and node[0] == 'link') or (js and node[0] == 'script')]
        return remains + asset.to_node(css=css, js=js, debug=debug, async_load=async_load, defer_load=defer_load, lazy_load=lazy_load)

    def _get_asset_link_urls(self, bundle):
        asset_nodes = self._get_asset_nodes(bundle, js=False)
        return [node[1]['href'] for node in asset_nodes if node[0] == 'link']

    @tools.ormcache_context('bundle', 'nodeAttrs and nodeAttrs.get("media")', 'defer_load', 'lazy_load', keys=("website_id", "lang"))
    def _get_asset_content(self, bundle, nodeAttrs=None, defer_load=False, lazy_load=False):
        asset_paths = self.env['ir.asset']._get_asset_paths(bundle=bundle, css=True, js=True)

        files = []
        remains = []
        for path, *_ in asset_paths:
            ext = path.split('.')[-1]
            is_js = ext in SCRIPT_EXTENSIONS
            is_css = ext in STYLE_EXTENSIONS
            if not is_js and not is_css:
                continue

            mimetype = 'text/javascript' if is_js else 'text/%s' % ext
            if can_aggregate(path):
                segments = [segment for segment in path.split('/') if segment]
                files.append({
                    'atype': mimetype,
                    'url': path,
                    'filename': get_resource_path(*segments) if segments else None,
                    'content': '',
                    'media': nodeAttrs and nodeAttrs.get('media'),
                })
            else:
                if is_js:
                    tag = 'script'
                    attributes = {
                        "type": mimetype,
                    }
                    attributes["data-src" if lazy_load else "src"] = path
                    if defer_load or lazy_load:
                        attributes["defer"] = "defer"
                else:
                    tag = 'link'
                    attributes = {
                        "type": mimetype,
                        "rel": "stylesheet",
                        "href": path,
                        'media': nodeAttrs and nodeAttrs.get('media'),
                    }
                remains.append((tag, attributes, ''))

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

        # get content (the return values from fields are considered to be markup safe)
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

        # get content (the return values from widget are considered to be markup safe)
        content = converter.value_to_html(value, field_options)
        attributes = {}
        attributes['data-oe-type'] = field_options['type']
        attributes['data-oe-expression'] = field_options['expression']

        return (attributes, content, None)

    def _prepare_values(self, values, options):
        """ Prepare the context that will be sent to the evaluated function.

        :param values: template values to be used for rendering
        :param options: frozen dict of compilation parameters.
        """
        check_values(values)
        values['true'] = True
        values['false'] = False
        if 'request' not in values:
            values['request'] = request
        return super()._prepare_values(values, options)

    def _compile_expr(self, expr, raise_on_missing=False):
        """ Compiles a purported Python expression to compiled code, verifies
        that it's safe (according to safe_eval's semantics) and alter its
        variable references to access values data instead

        :param expr: string
        """
        readable = io.BytesIO(expr.strip().encode('utf-8'))
        try:
            tokens = list(tokenize.tokenize(readable.readline))
        except tokenize.TokenError:
            raise ValueError(f"Cannot compile expression: {expr}")

        namespace_expr = self._compile_expr_tokens(tokens, self._allowed_keyword + list(self._available_objects.keys()), raise_on_missing=raise_on_missing)

        assert_valid_codeobj(_SAFE_QWEB_OPCODES, compile(namespace_expr, '<>', 'eval'), expr)
        return namespace_expr


def render(template_name, values, load, **options):
    """ Rendering of a qweb template without database and outside the registry.
    (Widget, field, or asset rendering is not implemented.)
    :param (string|int) template_name: template identifier
    :param dict values: template values to be used for rendering
    :param def load: function like `load(template_name, options)` which
        returns an etree from the given template name (from initial rendering
        or template `t-call`).
    :param options: used to compile the template (the dict available for the
        rendering is frozen)
    :returns: bytes marked as markup-safe (decode to :class:`markupsafe.Markup`
                instead of `str`)
    :rtype: MarkupSafe
    """
    class MockPool:
        db_name = None
        _Registry__cache = {}

    class MockIrQWeb(IrQWeb):
        _register = False               # not visible in real registry

        pool = MockPool()

        def _get_field(self, *args):
            raise NotImplementedError("Fields are not allowed in this rendering mode. Please use \"env['ir.qweb']._render\" method")

        def _get_widget(self, *args):
            raise NotImplementedError("Widgets are not allowed in this rendering mode. Please use \"env['ir.qweb']._render\" method")

        def _get_asset_nodes(self, *args):
            raise NotImplementedError("Assets are not allowed in this rendering mode. Please use \"env['ir.qweb']._render\" method")

    class MockEnv(dict):
        def __init__(self):
            super().__init__()
            self.context = {}

    renderer = object.__new__(MockIrQWeb)
    renderer.env = MockEnv()
    return renderer._render(template_name, values, load=load, **options)
