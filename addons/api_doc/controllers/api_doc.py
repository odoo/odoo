# Part of Odoo. See LICENSE file for full copyright and licensing details.
from __future__ import annotations

import contextlib
import dataclasses
import inspect
import io
import json
import logging
import typing
from http import HTTPStatus

import docutils.core
from werkzeug.exceptions import NotFound
from werkzeug.http import is_resource_modified, parse_cache_control_header

import odoo
from odoo import http
from odoo.exceptions import AccessError
from odoo.http import request
from odoo.modules.module_graph import ModuleGraph
from odoo.service.model import get_public_method
from odoo.tools import hmac, json_default, lazy_classproperty, py_to_js_locale

logger = logging.getLogger(__name__)


class DocController(http.Controller):
    """
    A single page application that provides an OpenAPI-like interface
    feeded by a reflection of the registry (fields and methods) in JSON
    documents.
    """

    @http.route(['/doc', '/doc/<model_name>', '/doc/index.html'], type='http', auth='user')
    def doc_client(self, mod=None, **kwargs):
        if not self.env.user.has_group('api_doc.group_allow_doc'):
            raise AccessError(self.env._(
                "This page is only accessible to %s users.",
                self.env.ref('api_doc.group_allow_doc').sudo().name))
        res = request.render('api_doc.docclient')
        res.headers['X-Frame-Options'] = 'deny'
        return res

    @http.route('/doc-bearer/index.json', type='http', auth='bearer')
    def doc_bearer_index(self):
        return self.doc_index()

    @http.route('/doc/index.json', type='http', auth='user')
    def doc_index(self):
        """
        Get a listing of all modules, models, methods and fields. But
        only their technical name and translated "human" name.

        It returns a json-serialized dictionnary with the following
        structure:

        .. code-block:: python
            {
                'modules': list[str],
                'models': [
                    {
                        'model': str,
                        'name': str,
                        'fields': {
                            name: {'string': str}
                            for name in fields_get()
                        },
                        'methods': list[str],
                    }
                    for model in ...
                ]
            }
        """
        if not self.env.user.has_group('api_doc.group_allow_doc'):
            raise AccessError(self.env._(
                "This page is only accessible to %s users.",
                self.env.ref('api_doc.group_allow_doc').sudo().name))

        # Cache key
        db_registry_sequence, _ = self.env.registry.get_sequences(self.env.cr)
        unique = hmac(
            self.env(su=True),
            scope='/doc/index.json',
            message=(
                db_registry_sequence,
                self.env.lang,
                sorted(self.env.user.all_group_ids.ids),
            ),
        )

        # Client cache
        use_cache = not parse_cache_control_header(
            request.httprequest.headers.get('Cache-Control')).no_cache
        if use_cache and not is_resource_modified(request.httprequest.environ, etag=unique):
            return request.make_response('', status=HTTPStatus.NOT_MODIFIED)

        # Server cache, use an attachment and not ormcache because the
        # index gets very large (>1MiB) when there are many modules
        # installed.
        # TODO: gzip
        filename = f'odoo-doc-index-{db_registry_sequence}-{unique}.json'
        index_attach = self.env['ir.attachment'].sudo().search([('name', '=', filename)], limit=1)
        if not index_attach:
            # No cache, generate the index and save it.
            modules, models = self._doc_index()
            index_attach = index_attach.create({
                'name': filename,
                'description': (
                    "Generated /doc/index.json document.\n\n"
                    f"Sequence: {db_registry_sequence}\n"
                    f"Lang: {self.env.lang}\n"
                    f"Groups: {sorted(self.env.user.all_group_ids.ids)}"
                ),
                'mimetype': 'application/json; charset=utf-8',
                'raw': json.dumps(
                    {'modules': modules, 'models': models},
                    ensure_ascii=False,
                    default=json_default,
                ),
                'public': False,
            })
            logger.info("new index attachment: %s", filename)

        response = index_attach._to_http_stream().get_response(etag=unique)
        response.headers['Content-Language'] = py_to_js_locale(self.env.lang)
        return response

    def _doc_index(self):
        modules = get_sorted_installed_modules(self.env)
        models = [
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
                # sorted(..., key=partial(sort_key_method, modules, type(Model))),
            }
            for ir_model in self.env['ir.model'].sudo().search([])
            if (Model := self.env[ir_model.model]).has_access('read')
        ]
        return modules, models

    @http.route('/doc-bearer/<model_name>.json', type='http', auth='bearer', readonly=True)
    def doc_bearer_modec(self, model_name):
        return self.doc_model(model_name)

    @http.route('/doc/<model_name>.json', type='http', auth='user', readonly=True)
    def doc_model(self, model_name):
        """
        Get a complete listing of all the methods and fields for a
        specific model. The listing includes the htmlified docstring of
        the model, an enriched fields_get(), the methods signature,
        parameters and htmlified docstrings.

        It returns a json-serialized dictionnary with the following
        structure:

        .. code-block:: python

            {
                'model': str,
                'name': str,
                'doc': str | None,
                'fields': dict[str, dict],  # fields_get indexed by field name
                'methods': dict[str, dict],  # _doc_method indexed by method name
            }
        """
        if not self.env.user.has_group('api_doc.group_allow_doc'):
            raise AccessError(self.env._(
                "This page is only accessible to %s users.",
                self.env.ref('api_doc.group_allow_doc').sudo().name))
        if model_name not in self.env:
            raise NotFound()

        Model = self.env[model_name]
        Model.check_access('read')
        ir_model = self.env['ir.model']._get(model_name)

        # Client cache
        db_registry_sequence, _ = self.env.registry.get_sequences(self.env.cr)
        unique = hmac(
            self.env(su=True),
            scope='/doc/<model_name>.json',
            message=(
                db_registry_sequence,
                self.env.lang,
                sorted(self.env.user.all_group_ids.ids),
            ),
        )
        use_cache = not parse_cache_control_header(
            request.httprequest.headers.get('Cache-Control')).no_cache
        if use_cache and not is_resource_modified(request.httprequest.environ, etag=unique):
            return request.make_response('', status=HTTPStatus.NOT_MODIFIED)

        # No cache, generate the document and send it.
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
        response.headers['ETag'] = unique
        response.headers['Cache-Control'] = 'no-cache, private'  # no-chache != no-store
        response.headers['Content-Language'] = py_to_js_locale(self.env.lang)
        return response

    def _doc_method(self, model, model_name, method, method_name):
        """
        Get the JSON reflection of a method.

        It returns a dict with the following structure:

        .. code-block:: python

            {
                'signature': str,
                'parameters': {
                    p.name: {
                        'name': str,
                        'kind': typing.Literal[
                            'POSITIONAL_ONLY',
                            'VAR_POSITIONAL',
                            'KEYWORD_ONLY',
                            'VAR_KEYWORD',
                        ],
                        'default': typing.Any,
                        'annotation': str,
                        'doc': str,
                    }
                    for p in function_parameters
                },
                'return': {
                    'annotation': str,
                    'doc': str,
                },
                'raise': dict[str, str],  # {exception name: doc}
                'doc': str,
                'api': list[str],
                'model': str,
                'module': str,
            }

        Of the above structure, only the entries ``signature``,
        ``parameters``, ``model`` and ``module`` are garanteed to be
        present. All other entries are optional and mean the information
        is absent.

        Inside the sub-dict for the parameters, only ``name`` is
        guaranteed to be present. When ``kind`` is absent it means the
        parameter is ``'POSITIONAL_OR_KEYWORD'``. When the other entries
        are absent it means that the information is missing.
        """

        # find what module/model introduced the method, for grouping
        introducing_class = next(
            parent_class
            for parent_class in reversed(type(model).mro())
            if hasattr(parent_class, method_name)
        )
        introducing_method = getattr(introducing_class, method_name)

        signature = parse_signature(introducing_method)
        return signature.as_dict() | {
            'model': introducing_class._name or 'core',
            'module': introducing_class._module or 'core',
        }


def get_sorted_installed_modules(env):
    names = env['ir.module.module'].sudo().search([
        ('state', '=', 'installed'),
    ]).mapped('name')
    graph = ModuleGraph(env.cr)
    graph.extend(names)
    return [p.name for p in graph]


def is_public_method(model, name):
    try:
        method = get_public_method(model, name)
        return not hasattr(method, '__deprecated__')
    except (AttributeError, AccessError):
        return None


DOC_API_MAGIC_COLUMNS = list(odoo.models.MAGIC_COLUMNS)
DOC_API_MAGIC_COLUMNS.insert(1, 'display_name')
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

    if field['name'] in DOC_API_MAGIC_COLUMNS:
        return 1, DOC_API_MAGIC_COLUMNS.index(field['name'])

    assert field['name'].startswith('x_'), field['name']
    return 3, field['name']


def sort_key_method(sorted_module_list, model_cls, method_name):
    """
    Key function to sort fields by the following criteria:

    1) Depth of the module that introduced the method in the dependency grap.
    2) Alphabetical order.
    """
    introducing_class = next(
        parent_class
        for parent_class
        in reversed(model_cls.mro())
        if hasattr(parent_class, method_name)
    )
    if introducing_class._module:
        depth = sorted_module_list.index(introducing_class._module)
    else:
        depth = -1
    return depth, method_name


def parse_signature(method) -> Signature:
    isign = inspect.signature(method)

    # strip self and cls from the signature
    param_iter = iter(isign.parameters.values())
    for param in param_iter:
        if param.name in ('self', 'cls'):
            isign = isign.replace(parameters=param_iter)
        break

    # replace BaseModel and such by list[int], see /json/2
    return_type = str(isign.return_annotation).strip("'\"").rpartition('.')[2]
    if return_type in ('Self', 'BaseModel', 'Model'):
        isign = isign.replace(return_annotation='list[int]')

    # parse the signature
    parameters = {
        param_name: Param.from_inspect(param)
        for param_name, param in isign.parameters.items()
    }
    returns = Return.from_inspect(isign.return_annotation)

    # accumate the decorators such as @api.model
    api = []
    if getattr(method, '_api_model', False):
        api.append('model')
    if getattr(method, '_readonly', False):
        api.append('readonly')

    signature = Signature(parameters, returns, api, raise_={}, doc=None)

    # if the method has a docstring, use it to enhance the signature
    if method.__doc__:
        enhance_signature_using_docstring(signature, method)

    return signature


def enhance_signature_using_docstring(signature, method):
    docstring = inspect.cleandoc(method.__doc__)
    doctree = _DocUtils.tree(docstring)

    # extract the ":param [annotation] <name>: text" and alike fields
    # from the docstring
    field_lists = [node for node in doctree if node.tagname == 'field_list']
    for field_list in field_lists:
        for field in field_list:
            field_name, field_body = field.children
            kind, _, name = str(field_name[0]).partition(' ')
            match (RST_INFO_FIELDS.get(kind), name.strip()):
                # unrecognized kind, e.g. var, meta, ...
                case (None, _):
                    pass
                # :param <annotation> <name>: <rst>
                case ('param', annotation_name) if ' ' in annotation_name:
                    annotation, _, name = annotation_name.rpartition(' ')
                    if param := signature.parameters.get(name.strip()):
                        if not param.annotation:
                            param.annotation = annotation.strip()
                        param.doc = _DocUtils.html_firstchild(field_body)
                # :param <name>: <rst>
                case ('param', name):
                    if param := signature.parameters.get(name):
                        param.doc = _DocUtils.html_firstchild(field_body)
                # :type <name>: <annotation>
                case ('type', name):
                    if (param := signature.parameters.get(name)) and not param.annotation:
                        param.annotations = field_body.children[0].astext().strip()
                # :returns: <rst>
                case ('returns', ''):
                    signature.return_.doc = _DocUtils.html_firstchild(field_body)
                # :rtype: <annotation>
                case ('rtype', ''):
                    if not signature.return_.annotation:
                        signature.return_.annotation = field_body.children[0].astext().strip()
                # :raises <exception>: <rst>
                case ('raises', exception):
                    signature.raise_[exception] = _DocUtils.html_firstchild(field_body)
                case _:
                    logger.warning(RST_PARSE_ERROR.format(docstring, f"cannot parse {field_name[0]}"))
        doctree.remove(field_list)

    signature.doc = _DocUtils.html(doctree)


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
RST_PARSE_ERROR = '''\
Unable to parse the docstring as reStructuredText.
Want to help fix the docstrings? Check out the test_docstring linter!
"""
{}
"""
{}'''


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
    parameters: dict[str, Param]
    return_: Return
    api: list[str]
    raise_: dict[str, str]
    doc: str | None

    def as_dict(self):
        d = {
            'signature': self.stringify(annotation=False),
            'parameters': {
                (p := param.as_dict()).pop('name'): p
                for param in self.parameters.values()
            },
        }
        if return_dict := self.return_.as_dict():
            d['return'] = return_dict
        if self.api:
            d['api'] = self.api
        if self.raise_:
            d['raise'] = self.raise_
        if self.doc is not None:
            d['doc'] = self.doc
        return d

    def stringify(self, annotation=True, default=True, return_annotation=True):
        out = ['(']
        for name, param in self.parameters.items():
            out.append(name)
            if annotation and param.annotation:
                out.append(f': {param.annotation}')
                if default and param.default is not inspect._empty:
                    out.append(f' = {param.default!r}')
            elif default and param.default is not inspect._empty:
                out.append(f'={param.default!r}')
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
        d = dict(vars(self))
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
            except (ValueError, TypeError):
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
        d = dict(vars(self))
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
            'raw_enabled': False,
            'file_insertion_enabled': False,
        })

    @lazy_classproperty
    def _settings_html(cls):
        return cls._make_settings('html', {
            'report_level': 3,
            'halt_level': 5,
            'embed_stylesheet': False,
            'raw_enabled': False,
            'file_insertion_enabled': False,
        })

    @classmethod
    def tree(cls, docstring):
        with contextlib.redirect_stderr(io.StringIO()) as stderr:
            doctree = docutils.core.publish_doctree(
                docstring,
                settings=cls._settings_pseudoxml,
            )
            if stderr.tell():
                logger.warning(RST_PARSE_ERROR.format(docstring, stderr.getvalue()))
            return doctree

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
