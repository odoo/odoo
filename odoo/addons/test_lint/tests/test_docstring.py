import contextlib
import docutils
import docutils.parsers.rst
from docutils.parsers.rst.directives.admonitions import Note
import docutils.nodes
import inspect
import io

from odoo.modules.registry import Registry
from odoo.tests.common import get_db_name, tagged
from odoo.addons.test_lint.tests.lint_case import LintCase

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


def extract_docstring_types(doctree):
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
                if type_param:
                    type_type = types.setdefault(name, type_param)
                    if type_type != type_param:
                        e = f"conflicting type: {type_param} (:param:) vs {type_type} (:type:)"
                        raise ValueError(e)

            elif kind == 'type':
                if not name:
                    e = "empty :type:"
                    raise ValueError(e)
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

    return types, rtype


@tagged('-at_install', 'post_install')
class TestDocstring(LintCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # The docstrings can use many more roles and directives than the
        # one present natively in docutils. That's because we use Sphinx
        # to render them in the documentation, and Sphinx defines the
        # "Python Domain", a set of additional rules and directive to
        # understand the python language.
        # 
        # It is not desirable to add a dependency on Sphinx in
        # community, at least not only for this linter.
        #
        # The following code adds a bunch of dummy elements for the
        # missing roles and directives, so docutils is able to parse
        # them with no warning.

        def role_function(name, rawtext, text, lineno, inliner, options=None, content=None):
            return [docutils.nodes.inline(rawtext, text)], []

        for role in ('attr', 'class', 'func', 'meth', 'ref', 'const', 'samp', 'term'):
            docutils.parsers.rst.roles.register_local_role(role, role_function)

        for directive in ('attribute', ):
            docutils.parsers.rst.directives.register_directive(
                directive, docutils.parsers.rst.directives.admonitions.Note)

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
                seen_methods.add(method_name)

                # We don't care of the docstring in overrides, find the
                # class that introduced the method.
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
                    method=method_name
                ):
                    with contextlib.redirect_stderr(io.StringIO()) as stderr:
                        doctree = docutils.core.publish_doctree(
                            inspect.cleandoc(method.__doc__),
                            settings_overrides={
                                'report_level': 2,  # WARNING
                                'halt_level': 5,  # CRITICAL TICAL!
                            }
                        )
                        if stderr.tell():
                            self.fail(stderr.getvalue())

                    self._test_docstring_params(method, doctree)

    def _test_docstring_params(self, method, doctree):
        doc_types, doc_rtype = extract_docstring_types(doctree)

        signature = inspect.signature(method)
        sign_types = {
            param.name: param.annotation
            for param in signature.parameters.values()
        }
        sign_rtype = signature.return_annotation

        if sign_rtype != signature.empty and doc_rtype != signature.empty:
            self.assertEqual(sign_rtype, doc_rtype)

        self.assertGreaterEqual(set(sign_types), set(doc_types))

        for param, doc_type in doc_types.items():
            sign_type = sign_types[param]
            if sign_type != signature.empty:
                self.assertEqual(sign_type, doc_type)
