from __future__ import annotations

from collections.abc import Callable

from mypy.nodes import MypyFile, StrExpr, TypeInfo
from mypy.plugin import MethodContext, Plugin
from mypy.types import Instance, LiteralType, Type, get_proper_type

STUB_MODULE = "odoo_registry_stubs"
ENVIRONMENT_GETITEM = "odoo.orm.runtime.environment.Environment.__getitem__"


def _model_name(ctx: MethodContext) -> str | None:
    if not ctx.args or not ctx.args[0]:
        return None
    expr = ctx.args[0][0]
    if isinstance(expr, StrExpr):
        return expr.value
    arg_type = get_proper_type(ctx.arg_types[0][0]) if ctx.arg_types[0] else None
    if isinstance(arg_type, Instance) and arg_type.last_known_value is not None:
        arg_type = arg_type.last_known_value
    if isinstance(arg_type, LiteralType) and isinstance(arg_type.value, str):
        return arg_type.value
    return None


class RegistryStubsPlugin(Plugin):
    _classes: dict[str, TypeInfo] | None = None

    def _class_for(self, ctx: MethodContext, model_name: str) -> TypeInfo | None:
        if self._classes is None:
            classes: dict[str, TypeInfo] = {}
            module = ctx.api.modules.get(STUB_MODULE)  # type: ignore[attr-defined]
            for symbol in module.names.values() if module is not None else ():
                info = symbol.node
                if not isinstance(info, TypeInfo):
                    continue
                name = info.names.get("_name")
                literal = get_proper_type(name.type) if name is not None else None
                if isinstance(literal, LiteralType) and isinstance(literal.value, str):
                    classes[literal.value] = info
            self._classes = classes
        return self._classes.get(model_name)

    def _typed_model(self, ctx: MethodContext) -> Type:
        model_name = _model_name(ctx)
        info = self._class_for(ctx, model_name) if model_name is not None else None
        if info is None:
            return ctx.default_return_type
        return Instance(info, [])

    def get_additional_deps(self, file: MypyFile) -> list[tuple[int, str, int]]:
        # the stub is imported by nobody; every checked file depends on it so
        # its classes are loaded before a method hook asks for them
        if file.fullname == STUB_MODULE or file.fullname.startswith("mypy."):
            return []
        return [(10, STUB_MODULE, -1)]

    def get_method_hook(self, fullname: str) -> Callable[[MethodContext], Type] | None:
        if fullname == ENVIRONMENT_GETITEM:
            return self._typed_model
        return None


def plugin(version: str) -> type[Plugin]:
    return RegistryStubsPlugin
