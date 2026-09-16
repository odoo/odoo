"""The hand-written typing stubs restate members the classes actually have.

`_ModelStubs` and `_FieldStubs` declare, under `if TYPE_CHECKING:`, the
sibling members a mixin reaches through `self`; mypy reads them, the runtime
never does. A stub that outlives its member -- renamed, removed, re-signed --
lets mypy accept a call the runtime refuses, and nothing else notices. Each
declared method must exist on the composed class with the same parameters
(names, kinds, which carry defaults); each declared attribute must resolve.
"""

import annotationlib
import ast
import functools
import inspect
import pathlib
import unittest

from odoo import fields, models
from odoo.orm.fields import base as fields_base
from odoo.orm.model_test_env import model_test_env
from odoo.orm.models.base import BaseModel

ORM = pathlib.Path(fields_base.__file__).parent.parent


def _stub_class(path: pathlib.Path, name: str) -> ast.ClassDef:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and node.name == name:
            return node
    raise AssertionError(f"{path} declares no class {name}")


def _declared(cls: ast.ClassDef):
    methods: dict[str, ast.FunctionDef] = {}
    attributes: set[str] = set()

    def walk(nodes):
        for node in nodes:
            if isinstance(node, ast.If):
                walk(node.body)
                walk(node.orelse)
            elif isinstance(node, ast.FunctionDef):
                methods[node.name] = node
            elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
                attributes.add(node.target.id)

    walk(cls.body)
    return methods, attributes


def _stub_parameters(node: ast.FunctionDef) -> list[tuple[str, str, bool]]:
    args = node.args
    params = []
    positional = args.posonlyargs + args.args
    defaults = [None] * (len(positional) - len(args.defaults)) + list(args.defaults)
    for arg, default in zip(positional, defaults, strict=True):
        kind = "POSITIONAL_ONLY" if arg in args.posonlyargs else "POSITIONAL_OR_KEYWORD"
        params.append((arg.arg, kind, default is not None))
    if args.vararg:
        params.append((args.vararg.arg, "VAR_POSITIONAL", False))
    for arg, default in zip(args.kwonlyargs, args.kw_defaults, strict=True):
        params.append((arg.arg, "KEYWORD_ONLY", default is not None))
    if args.kwarg:
        params.append((args.kwarg.arg, "VAR_KEYWORD", False))
    return params


def _real_parameters(function) -> list[tuple[str, str, bool]]:
    return [
        (p.name, p.kind.name, p.default is not inspect.Parameter.empty)
        for p in inspect.signature(
            function, annotation_format=annotationlib.Format.STRING
        ).parameters.values()
    ]


_MISSING = object()


def _member(classes, name):
    for cls in classes:
        try:
            return inspect.getattr_static(cls, name)
        except AttributeError:
            continue
    return _MISSING


def _is_wildcard(params: list[tuple[str, str, bool]]) -> bool:
    # `def f(self, *args, **kwargs): ...` declares nothing about the signature
    return [kind for _name, kind, _default in params[1:]] == [
        "VAR_POSITIONAL",
        "VAR_KEYWORD",
    ]


def _all_field_classes(root: type) -> tuple[type, ...]:
    found = [root]
    for cls in root.__subclasses__():
        found.extend(_all_field_classes(cls))
    return tuple(found)


def _unwrap(member):
    if isinstance(member, property):
        return member.fget
    if isinstance(member, staticmethod | classmethod):
        return member.__func__
    return member


class _StubContract(unittest.TestCase):
    path: pathlib.Path
    stub_name: str
    classes: tuple[type, ...]

    def _check(self):
        methods, attributes = _declared(_stub_class(self.path, self.stub_name))
        for name, node in sorted(methods.items()):
            with self.subTest(member=name):
                member = _member(self.classes, name)
                self.assertIsNot(
                    member,
                    _MISSING,
                    f"{self.stub_name}.{name} exists on none of {[c.__name__ for c in self.classes]}",
                )
                is_property = any(
                    isinstance(d, ast.Name) and d.id == "property"
                    for d in node.decorator_list
                )
                if is_property:
                    self.assertIsInstance(
                        member,
                        property | functools.cached_property,
                        f"{name} is declared a property",
                    )
                    continue
                real = _unwrap(member)
                if not callable(real):
                    self.fail(
                        f"{self.stub_name}.{name} is declared a method, the class holds {type(member).__name__}"
                    )
                real_params = _real_parameters(real)
                stub_params = _stub_parameters(node)
                if _is_wildcard(stub_params):
                    continue
                if isinstance(member, staticmethod):
                    stub_params = (
                        stub_params[1:]
                        if stub_params and stub_params[0][0] == "self"
                        else stub_params
                    )
                self.assertEqual(
                    stub_params,
                    real_params,
                    f"{self.stub_name}.{name} declares {stub_params}, the class has {real_params}",
                )
        for name in sorted(attributes):
            with self.subTest(member=name):
                if name.startswith("__"):
                    continue
                self.assertTrue(
                    _member(self.classes, name) is not _MISSING
                    or any(name in getattr(c, "__slots__", ()) for c in self.classes)
                    or any(
                        name in getattr(c, "__annotations__", {}) for c in self.classes
                    ),
                    f"{self.stub_name}.{name} resolves on none of {[c.__name__ for c in self.classes]}",
                )


class _Registered(models.Model):
    _name = "stub.registered"
    _module = "test_typing_stubs"
    _description = "a registered model, for the attributes the registry sets"

    name = fields.Char()


class TestModelStubs(_StubContract):
    path = ORM / "models" / "mixins" / "_model_stubs.py"
    stub_name = "_ModelStubs"
    classes: tuple[type, ...] = (BaseModel,)

    def test_every_stub_names_a_member_of_basemodel_with_its_signature(self):
        with model_test_env(_Registered) as env:
            self.classes = (BaseModel, type(env["stub.registered"]))
            self._check()


class TestFieldStubs(_StubContract):
    path = ORM / "fields" / "_field_stubs.py"
    stub_name = "_FieldStubs"
    classes = _all_field_classes(fields_base.Field)

    def test_every_stub_names_a_member_of_a_field_class_with_its_signature(self):
        self._check()
