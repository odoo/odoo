import dataclasses
import inspect
import json
import logging
import typing
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

logger = logging.getLogger(__name__)


class DocController(http.Controller):
    """
    A single page application that provides an OpenAPI-like interface
    feeded by a reflection of the registry (fields and methods) in JSON
    documents.
    """

    @http.route(['/doc', '/doc/<model_name>', '/doc/index.html'], type='http', auth='user')
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
                        for method_name in dir(Model)
                        if is_public_method(Model, method_name)
                    ],
                    # sorted(..., key=partial(sort_key_method, modules, Model)),
                }
                for ir_model in self.env['ir.model'].sudo().search([])
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
                for field in Model.fields_get().values()
            },
            'methods': {
                method_name: self._doc_method(Model, model_name, method, method_name)
                for method_name in dir(Model)
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

        # accumate the decorators such as @api.model
        api = []
        if getattr(method, '_api_model', False):
            api.append('model')

        signature = parse_signature(method)
        obj = {
            **signature.as_dict(),
            # signature: '',
            # parameters: {},
            # return: {}
            # raise: {}
            # doc: ''
            'model': introducing_model._name or 'core',
            'module': introducing_model._module or 'core',
            # api: []
        }
        if api:
            obj['api'] = api

        return obj


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


def parse_signature(method) -> 'Signature':
    isign = inspect.signature(method)

    # strip self and cls from the signature
    iter_params = iter(isign.parameters.items())
    if next(iter_params, (None, None))[0] in ('self', 'cls'):
        isign = isign.replace(parameters=(v for i, v in iter_params))

    # replace BaseModel and such by list[int], see /json/2
    return_type = str(isign.return_annotation).strip("'\"").rpartition('.')[2]
    if return_type in ('Self', 'BaseModel', 'Model'):
        isign = isign.replace(return_annotation='list[int]')

    # parse the signature proper
    parameters = {
        param_name: Param.from_inspect(param)
        for param_name, param in isign.parameters.items()
    }
    returns = Return.from_inspect(isign.return_annotation)
    signature = Signature(parameters, returns, raise_={}, doc=None)

    # if the method has a docstring, use it to enhance the signature
    if not method.__doc__:
        return signature
    docstring = inspect.cleandoc(method.__doc__)
    doctree = _DocUtils.tree(docstring)

    # extract the ":param [annotation] <name>: text" and alike fields
    # from the docstring
    field_lists = [node for node in doctree if node.tagname == 'field_list']
    for field_list in field_lists:
        for field in field_list:
            field_name, field_body = field.children
            kind, sp, name = str(field_name[0]).partition(' ')
            match (RST_INFO_FIELDS.get(kind), sp, name):
                # unrecognized kind, e.g. var, meta, ...
                case (None, _, _):
                    pass
                # :param [annotation] <name>: <rst>
                case ('param', ' ', annotation_name):
                    annotation, _, name = annotation_name.rpartition(' ')
                    if param := signature.parameters.get(name):
                        if annotation and not param.annotation:
                            param.annotation = annotation
                        param.doc = _DocUtils.html_firstchild(field_body)
                # :type <name>: <annotation>
                case ('type', ' ', name):
                    if (param := signature.parameters.get(name)) and not param.annotation:
                        param.annotations = field_body.children[0].astext().strip()
                # :returns: <rst>
                case ('returns', '', ''):
                    signature.return_.doc = _DocUtils.html_firstchild(field_body)
                # :rtype: <type>
                case ('rtype', '', ''):
                    if not signature.return_.annotation:
                        signature.return_.annotation = field_body.children[0].astext().strip()
                # :raises <exception>: <rst>
                case ('raises', ' ', name):
                    signature.raise_[name] = _DocUtils.html_firstchild(field_body)
                case _:
                    logger.warning(
                        'unable to parse %r in docstring of %s\n%s\n"""\n%s\n"""',
                        str(field_name[0]), method, RST_INFO_FIELDS_URL, docstring,
                    )
        doctree.remove(field_list)

    signature.doc = _DocUtils.html(doctree)
    return signature


RST_INFO_FIELDS_URL = "https://www.sphinx-doc.org/en/master/usage/domains/python.html#info-field-lists"
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

    'returns': 'returns',
    'return': 'returns',

    'rtype': 'rtype',
}


def stringify_annotation(annotation) -> str | None:
    if annotation is inspect._empty:
        return None
    if isinstance(annotation, str):
        return annotation
    if isinstance(annotation, type):
        return annotation.__name__
    return str(annotation)


@dataclasses.dataclass
class Signature:
    parameters: dict[str, 'Param']
    return_: 'Return'
    raise_: dict[str, str]
    doc: str | None

    def as_dict(self):
        d = {
            'signature': str(self),
            'parameters': {
                (p := param.as_dict()).pop('name'): p
                for param in self.parameters.values()
            },
        }
        if return_dict := self.return_.as_dict():
            d['return'] = return_dict
        if self.raise_:
            d['raise'] = self.raise_
        if self.doc is not None:
            d['doc'] = self.doc
        return d

    def __str__(self):
        return self.stringify(annotation=False)

    def stringify(self, annotation=True, default=True, return_annotation=True):
        out = ['(']
        for name, param in self.parameters.items():
            out.append(name)
            if annotation and param.annotation:
                out.append(f': {param.annotation}')
                if default and param.default is not inspect._empty:
                    out.append(f' = {param.default}')
            elif default and param.default is not inspect._empty:
                out.append(f'={param.default}')
            out.append(', ')
        if self.parameters:
            out.pop()  # remove trailing ', '
        out.append(')')
        if return_annotation and self.return_.annotation:
            out.append(f' -> {self.return_.annotation}')
        return ''.join(out)


@dataclasses.dataclass
class Param:
    name: str
    kind: typing.Literal[
        # def foo(pos_only, /, pos_or_kw, *var_pos, kw_only, **var_kw)
        'POSITIONAL_ONLY',
        'POSITIONAL_OR_KEYWORD',
        'VAR_POSITIONAL',
        'KEYWORD_ONLY',
        'VAR_KEYWORD',
    ]
    default: typing.Any | inspect._empty
    annotation: str | None
    doc: str | None

    @classmethod
    def from_inspect(cls, parameter):
        return cls(
            name=parameter.name,
            kind=parameter.kind.name,
            default=parameter.default,
            annotation=stringify_annotation(parameter.annotation),
            doc=None,
        )

    def as_dict(self):
        d = vars(self)
        if self.kind == 'POSITIONAL_OR_KEYWORD':
            # most (99%) params are POSITIONAL_OR_KEYWORD
            # make the export smaller by ignoring those
            d.pop('kind')
        if self.annotation is None:
            d.pop('annotation')
        if self.doc is None:
            d.pop('doc')
        if self.default is inspect._empty:
            d.pop('default')
        else:
            # ignore the default value when it is not json serializable
            try:
                json.dumps(self.default)
            except ValueError:
                d.pop('default')
        return d


@dataclasses.dataclass
class Return:
    annotation: str | None
    doc: str | None

    @classmethod
    def from_inspect(cls, return_annotation):
        return cls(stringify_annotation(return_annotation), doc=None)

    def as_dict(self):
        d = vars(self)
        if self.annotation is None:
            d.pop('annotation')
        if self.doc is None:
            d.pop('doc')
        return d


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
