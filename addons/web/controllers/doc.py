import contextlib
import inspect
import json
from collections import defaultdict
from http import HTTPStatus

import docutils.core
from werkzeug.exceptions import NotFound
from werkzeug.http import is_resource_modified, parse_cache_control_header

from odoo import http
from odoo.exceptions import AccessError
from odoo.http import request
from odoo.modules.module_graph import get_sorted_installed_modules
from odoo.service.model import get_public_method
from odoo.tools import lazy_classproperty, py_to_js_locale


class DocController(http.Controller):
    """
    A single page application that provides an OpenAPI-like interface
    feeded by a reflection of the registry (fields and methods) in JSON
    documents.
    """

    @http.route(['/doc', '/doc/', '/doc/<model_name>', '/doc/index.html'], type='http', auth='user')
    def doc_client(self, mod=None, **kwargs):
        request.env.user._on_webclient_bootstrap()
        context = request.env['ir.http'].webclient_rendering_context()
        return request.render('web.doc', qcontext=context)

    @http.route('/doc/index.json', type='http', auth='user', readonly=True)
    def doc_index(self):
        """
        Get a listing of all modules, models, methods and fields. But
        only their technical name and translated "human" name.
        """
        db_registry_sequence, _ = self.env.registry.get_sequences(self.env.cr)
        etag = f'"{db_registry_sequence}"'
        use_cache = not parse_cache_control_header(
            request.httprequest.headers.get('Cache-Control')).no_cache
        if use_cache and not is_resource_modified(request.httprequest.environ, etag=etag):
            return request.make_response('', status=HTTPStatus.NOT_MODIFIED)

        modules = get_sorted_installed_modules(self.env)

        result = {
            'modules': modules,
            'models': [
                {
                    'model': ir_model.model,
                    'name': ir_model.name,
                    'fields': {
                        field.name: {'string': field.field_description}
                        for field in ir_model.field_id
                        # sorted(ir_model.field_id, key=partial(sort_key_field, modules, Model))
                        if Model._has_field_access(Model._fields[field.name], 'read')
                    },
                    'methods': [
                        method_name
                        for method_name
                        in dir(Model)
                        if is_public_method(Model, method_name)
                    ],
                    # sorted(..., key=partial(sort_key_method, modules, Model)),
                }
                for ir_model
                in self.env['ir.model'].sudo().search([])
                if (Model := self.env[ir_model.model]).has_access('read')
            ],
        }

        response = request.make_json_response(result)
        response.headers['ETag'] = etag
        response.headers['Cache-Control'] = 'private'
        response.headers['Content-Language'] = py_to_js_locale(self.env.context['lang'])
        return response

    @http.route('/doc/<model_name>.json', type='http', auth='user', readonly=True)
    def doc_model(self, model_name):
        """
        Get a complete listing of all the methods and fields for a
        specific model. The listing includes the htmlified docstring of
        the model, an enriched fields_get(), the methods signature,
        parameters and htmlified docstrings.
        """
        if model_name not in self.env:
            raise NotFound()

        Model = self.env[model_name]
        Model.check_access('read')
        ir_model = self.env['ir.model']._get(model_name)

        db_registry_sequence, _ = self.env.registry.get_sequences(self.env.cr)
        etag = f'"{db_registry_sequence}"'
        use_cache = not parse_cache_control_header(
            request.httprequest.headers.get('Cache-Control')).no_cache
        if use_cache and not is_resource_modified(request.httprequest.environ, etag=etag):
            return request.make_response('', status=HTTPStatus.NOT_MODIFIED)

        result = {
            'model': model_name,
            'name': ir_model.name,
            'doc': None,  # TODO
            'fields': {
                field['name']: dict(
                    field,
                    module=next(iter(Model._fields[field['name']]._modules), None),
                )
                for field
                in Model.fields_get().values()
            },
            'methods': {
                method_name: self._doc_method(Model, model_name, method, method_name)
                for method_name
                in dir(Model)
                if (method := is_public_method(Model, method_name))
            },
        }

        response = request.make_json_response(result)
        response.headers['ETag'] = etag
        response.headers['Cache-Control'] = 'private'
        response.headers['Content-Language'] = py_to_js_locale(self.env.context['lang'])
        return response

    def _doc_method(self, model, model_name, method, method_name):
        """ Get the JSON reflection of a method. """

        # find what module/model introduced the method, for grouping
        introducing_model = next(
            parent_model
            for parent_model in reversed(type(model).mro())
            if hasattr(parent_model, method_name)
        )
        signature, parameters, return_ = self._doc_method_signature(method)

        obj = {
            'model': introducing_model._name or 'core',
            'module': introducing_model._module or 'core',
            'signature': str(signature),
            'parameters': parameters,
            # doc: ''
            # raise: {}
            # return: {}
            # api: []
            # signature: ''
        }

        if method.__doc__:
            rst_fields, html_docstring = self._doc_method_docstring(method)
            if html_docstring:
                obj['doc'] = html_docstring
            if raises := rst_fields.get('raises'):
                obj['raise'] = raises
            for param, doc in rst_fields.get('param', {}).items():
                with contextlib.suppress(KeyError):
                    parameters[param]['doc'] = doc
            for param, type_ in rst_fields.get('type', {}).items():
                with contextlib.suppress(KeyError):
                    parameters[param].setdefault('annotation', type_)
            if rdoc := rst_fields.get('returns'):
                return_['doc'] = rdoc
            if rtype := rst_fields.get('rtype'):
                return_.setdefault('annotation', rtype)

        if return_:
            obj['return'] = return_

        api = []
        if getattr(method, '_api_model', False):
            api.append('model')
        if api:
            obj['api'] = api

        obj['signature'] = str(signature.replace(
            parameters=[
                inspect.Parameter(
                    name=name,
                    kind=inspect._ParameterKind[p.get('kind', 'POSITIONAL_OR_KEYWORD')],
                    default=p.get('default', inspect._empty),
                ) for name, p in parameters.items()],
            return_annotation=return_.get('annotation', inspect._empty),
        )).replace(") -> '", ") -> ").removesuffix("'")

        return obj

    def _doc_method_signature(self, method):
        signature = inspect.signature(method)

        # replace BaseModel and such by list[int], see /json/2
        return_type = str(signature.return_annotation).strip("'\"").rpartition('.')[2]
        if return_type in ('Self', 'BaseModel', 'Model'):
            signature = signature.replace(return_annotation=list[int])

        # strip self and cls from the signature
        iter_params = iter(signature.parameters.items())
        if next(iter_params, (None, None))[0] in ('self', 'cls'):
            signature = signature.replace(parameters=(v for i, v in iter_params))

        parameters = {}
        for param_name, param in signature.parameters.items():
            parameters[param_name] = {}
            if param.kind.name != 'POSITIONAL_OR_KEYWORD':
                parameters[param_name]['kind'] = param.kind.name
            if param.default is not param.empty:
                try:
                    json.dumps(param.default)
                except TypeError:
                    pass
                else:
                    parameters[param_name]['default'] = param.default
            if param.annotation is not param.empty:
                parameters[param_name]['annotation'] = str(param.annotation)

        return_ = {}
        if signature.return_annotation is not signature.empty:
            return_['annotation'] = signature.return_annotation

        return signature, parameters, return_

    def _doc_method_docstring(self, method):
        docstring = inspect.cleandoc(method.__doc__)
        doctree = _DocUtils.tree(docstring)

        field_lists = [node for node in doctree if node.tagname == 'field_list']

        # populate rst_fields using the :param: and like fields
        rst_fields = defaultdict(dict)
        # rst_fields = {
        #     'param': {name: doc},
        #     'type': {name: type},
        #     'returns': ...,
        #     'rtype': ...,
        #     'raise': {exception: doc},
        #     'var': {name: doc},
        #     'vartype': {name: type},
        #     'meta': {},
        # }

        for field_list in field_lists:
            for field in field_list:
                field_name, field_body = field.children
                kind, sp, name = str(field_name[0]).partition(' ')
                if kind not in RST_INFO_FIELDS:
                    continue

                kind = RST_INFO_FIELDS[kind]

                if kind == 'returns':
                    assert not sp, (kind, name)
                    rst_fields[kind] = _DocUtils.html_firstchild(field_body)
                elif kind == 'rtype':
                    assert not sp, (kind, name)
                    rst_fields[kind] = field_body.children[0].astext().strip()
                elif kind in ('param', 'var'):
                    # :param str foo: hello
                    # -> :param foo: hello
                    #    :type foo: str
                    type_, _, name = name.rpartition(' ')
                    if type_:
                        kind_type = 'type' if kind == 'param' else 'vartype'
                        rst_fields[kind_type][name] = type_
                    rst_fields[kind][name] = _DocUtils.html_firstchild(field_body)
                elif kind in ('type', 'vartype'):
                    rst_fields[kind][name] = field_body.children[0].astext().strip()
                else:
                    rst_fields[kind][name] = _DocUtils.html_firstchild(field_body)
            doctree.remove(field_list)

        assert set(rst_fields).issubset(RST_INFO_FIELDS), rst_fields
        return rst_fields, _DocUtils.html(doctree)


# https://www.sphinx-doc.org/en/master/usage/domains/python.html#info-field-lists
RST_INFO_FIELDS = {
    'param': 'param',
    'parameter': 'param',
    'arg': 'param',
    'argument': 'param',
    'key': 'param',
    'keyword': 'param',

    'type': 'type',

    'raises': 'raises',
    'raise': 'raises',
    'except': 'raises',
    'exception': 'raises',

    'var': 'var',
    'ivar': 'var',
    'cvar': 'var',

    'vartype': 'vartype',

    'returns': 'returns',
    'return': 'returns',

    'rtype': 'rtype',

    'meta': 'meta',
}


def is_public_method(model, name):
    try:
        return get_public_method(model, name)
    except (AttributeError, AccessError):
        return None


CORE_FIELDS = ('id', 'display_name', 'create_uid', 'write_uid', 'create_date', 'write_date')
def sort_key_field(sorted_module_list, model, field):  # noqa: E302
    """
    Key function to sort fields with the following order:

    (1) core fields < (2) model fields < (3) custom ``x_`` fields

    1. The core fields have a hardcoded order, like `id` is first.
    2. The model fields are sorted first by *introducing module* (i.e.
       base then web then website then ecommerce), and second by
       alphabetical order.
    3. The custom fields are sorted solely by alphabetical order.
    """
    if introducing_modules := model._fields[field['name']]._modules:
        depth = sorted_module_list.index(introducing_modules[0])
        return 2, depth, field['name']

    if field['name'] in CORE_FIELDS:
        return 1, CORE_FIELDS.index(field['name'])

    assert field['name'].startswith('x_'), field['name']
    return 3, field['name']


def sort_key_method(sorted_module_list, model, method_name):
    """
    Key function to sort fields by the following criteria:

    1) Depth of the module that introduced the method in the dependency grap.
    2) Alphabetical order.
    """
    introducing_model = next(
        parent_model
        for parent_model
        in reversed(type(model).mro())
        if hasattr(parent_model, method_name)
    )
    if introducing_model._module:
        depth = sorted_module_list.index(introducing_model._module)
    else:
        depth = -1
    return depth, method_name


# This class could had been a python module, but lazy_classproperty
# works much better than odoo.tools.lazy.
class _DocUtils:
    """ Helpers for docutils """
    @lazy_classproperty
    def _new_docutils_root(cls):
        # surely there's a better way, but that'll do
        return docutils.core.publish_doctree("").copy

    @classmethod
    def _make_settings(cls, writer_name, settings_overrides):
        pub = docutils.core.Publisher()
        pub.set_components('standalone', 'restructuredtext', writer_name)
        pub.process_programmatic_settings(None, settings_overrides, None)
        return pub.settings

    @lazy_classproperty
    def _settings_pseudoxml(cls):
        return cls._make_settings('pseudoxml', {
            'report_level': 3,
            'halt_level': 5,
        })

    @lazy_classproperty
    def _settings_html(cls):
        return cls._make_settings('html', {
            'report_level': 3,
            'halt_level': 5,
            'embed_stylesheet': False,
        })

    @classmethod
    def tree(cls, docstring):
        return docutils.core.publish_doctree(
            docstring,
            settings=cls._settings_pseudoxml,
        )

    @classmethod
    def html(cls, tree):
        root = cls._new_docutils_root()
        root.append(tree)
        html = docutils.core.publish_from_doctree(
            root,
            writer_name='html',
            settings=cls._settings_html,
        )
        head = b'\n</head>\n<body>\n<div class="document">'
        tail = b'</div>\n</body>\n</html>\n'
        return html.partition(head)[2].removesuffix(tail).strip().decode()

    @classmethod
    def html_firstchild(cls, tree):
        if not tree.children:
            return ''
        return cls.html(tree.children[0])
