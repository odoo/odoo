import inspect
import logging

import docutils

from odoo.modules.registry import Registry
from odoo.tests.common import BaseCase, get_db_name, tagged

logger = logging.getLogger(__name__)

POSITIONAL_ONLY = inspect.Parameter.POSITIONAL_ONLY
POSITIONAL_OR_KEYWORD = inspect.Parameter.POSITIONAL_OR_KEYWORD
VAR_POSITIONAL = inspect.Parameter.VAR_POSITIONAL
KEYWORD_ONLY = inspect.Parameter.KEYWORD_ONLY
VAR_KEYWORD = inspect.Parameter.VAR_KEYWORD

RST_INFO_FIELDS_DOC = (
    "https://www.sphinx-doc.org/en/master/usage/domains/python.html#info-field-lists")

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


ABUSE_KWARGS = """\
module={module!r}, model={model!r}, method={method!r}:
Function signature:
  {function}
Docstring:
  {docstring}
Absent from function: {func_missing}
Absent from docstring: {doc_missing}
"""


def extract_docstring_params(method):
    docstring = inspect.cleandoc(method.__doc__)
    doctree = docutils.core.publish_doctree(docstring, settings_overrides={
        'report_level': 5,
        'halt_level': 5,
    })

    params = {}  # sorted set
    types = {}
    rtype = inspect._empty

    field_lists = [node for node in doctree if node.tagname == 'field_list']
    for field_list in field_lists:
        for field in field_list:
            field_name, field_body = field.children
            kind, _, name = str(field_name[0]).partition(' ')
            if kind not in RST_INFO_FIELDS:
                e = f"unknown rst: {kind!r}\n{RST_INFO_FIELDS_DOC}"
                raise ValueError(e)
            kind = RST_INFO_FIELDS[kind]

            if kind == 'param':
                if not name:
                    e = "empty :param:"
                    raise ValueError(e)
                type_param, _, name = name.rpartition(' ')
                params[name] = None
                if type_param:
                    type_type = types.setdefault(name, type_param)
                    if type_type != type_param:
                        e = f"conflicting type: {type_param} (:param:) vs {type_type} (:type:)"
                        raise ValueError(e)

            elif kind == 'type':
                if not name:
                    e = "empty :type:"
                    raise ValueError(e)
                params[name] = None
                try:
                    type_type = field_body.children[0].astext().strip()
                except IndexError as exc:
                    if name:
                        e = f'invalid ":{kind} {name}:", did you mean ":{kind}: {name}"?'
                        raise ValueError(e) from exc
                    raise
                type_param = types.setdefault(name, type_type)
                if type_param != type_type:
                    e = f"conflicting type: {type_param} (:param:) vs {type_type} (:type:)"
                    raise ValueError(e)

            elif kind == 'rtype':
                try:
                    rtype = field_body.children[0].astext().strip()
                except IndexError as exc:
                    if name:
                        e = f'invalid ":{kind} {name}:", did you mean ":{kind}: {name}"?'
                        raise ValueError(e) from exc
                    raise

    return list(params), types, rtype


@tagged('-at_install', 'post_install')
class TestDocstring(BaseCase):
    def test_docstring(self):
        """ Verify that the function signature and its docstring match. """
        registry = Registry(get_db_name())
        seen_methods = set()

        for model_name, model_cls in registry.items():
            for method_name, _ in inspect.getmembers(model_cls, inspect.isroutine):
                if method_name.startswith('__'):
                    continue
                if method_name in seen_methods:
                    continue
                seen_methods.add((model_name, method_name))
                reverse_mro = reversed(model_cls.mro()[1:-1])
                for parent_class in reverse_mro:
                    method = getattr(parent_class, method_name, None)
                    if callable(method):
                        break
                if not method.__doc__:
                    continue

                with self.subTest(
                    module=parent_class._module,
                    model=parent_class._name,
                    method=method_name,
                ):
                    doc_params, doc_types, doc_rtype = extract_docstring_params(method)

                    signature = inspect.signature(method)
                    sign_params = list(signature.parameters.values())
                    sign_types = {param.name: param.annotation for param in sign_params}
                    sign_rtype = signature.return_annotation

                    if sign_rtype != signature.empty and doc_rtype != signature.empty:
                        self.assertEqual(sign_rtype, doc_rtype)

                    try:
                        m = "the docstring is documenting non-existing parameters"
                        self.assertGreaterEqual(set(sign_types), set(doc_params), m)
                    except AssertionError:
                        if sign_params[-1].kind != VAR_KEYWORD:
                            raise
                        # TODO: increase verbosity to warning
                        logger.info(ABUSE_KWARGS.format(
                            module=parent_class._module,
                            model=parent_class._name,
                            method=method_name,
                            function=signature,
                            docstring=', '.join(tuple(doc_params)),
                            func_missing=set(doc_params) - set(sign_types),
                            doc_missing=(set(sign_types) - set(doc_params) - {
                              # self               , kwargs
                                sign_params[0].name, sign_params[-1].name}
                            ) or {},
                        ))

                    for param, doc_type in doc_types.items():
                        sign_type = sign_types.get(param, signature.empty)
                        if sign_type != signature.empty:
                            if isinstance(sign_type, type):
                                sign_type = sign_type.__name__
                            self.assertEqual(sign_type, doc_type)
