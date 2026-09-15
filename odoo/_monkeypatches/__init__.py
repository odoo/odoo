import importlib
import os
import pkgutil
import sys
import time
from importlib.abc import Loader
from types import ModuleType
from typing import Any

from odoo.libs.debug_log import DebugLog

_debug = DebugLog(__name__)

_SELF_PREFIX = __name__ + "."


class _PatchingLoader(Loader):
    def __init__(self, loader: Any, target: str) -> None:
        self._loader = loader
        self._target = target

    def create_module(self, spec: Any) -> ModuleType | None:
        return self._loader.create_module(spec)

    def exec_module(self, module: ModuleType) -> None:
        with _debug.perf(
            "monkeypatch.import", module=module.__name__, target=self._target
        ):
            self._loader.exec_module(module)
        patch_module(self._target)

    def __getattr__(self, name: str) -> Any:
        return getattr(self._loader, name)

    def __repr__(self) -> str:
        return f"<_PatchingLoader for {self._target!r} wrapping {self._loader!r}>"


class PatchImportHook:
    def __init__(self) -> None:
        self.hooks: set[str] = set()

    def add_hook(self, fullname: str) -> None:
        self.hooks.add(fullname)
        already_imported = fullname in sys.modules
        _debug.lifecycle(
            "monkeypatch.hook_registered",
            target=fullname,
            already_imported=already_imported,
        )
        if already_imported:
            patch_module(fullname)

    def _get_hook_target(self, fullname: str) -> str | None:
        if fullname in self.hooks:
            return fullname
        if fullname.startswith(_SELF_PREFIX):
            target = fullname[len(_SELF_PREFIX) :]
            if target in self.hooks:
                return target
        return None

    def find_spec(
        self, fullname: str, path: Any = None, target: ModuleType | None = None
    ) -> Any:
        patched = self._get_hook_target(fullname)
        if patched is None:
            return None

        finders = sys.meta_path
        try:
            start = finders.index(self) + 1
        except ValueError:
            start = 0
        for finder in finders[start:]:
            if finder is self:
                continue
            spec = finder.find_spec(fullname, path, target)
            if spec is not None:
                _debug.logic(
                    "monkeypatch.import_intercepted",
                    module=fullname,
                    target=patched,
                    finder=getattr(finder, "__name__", type(finder).__name__),
                    wrapped=spec.loader is not None,
                )
                if spec.loader is not None:
                    spec.loader = _PatchingLoader(spec.loader, patched)
                return spec
        _debug.logic("monkeypatch.import_unresolved", module=fullname, target=patched)
        return None


HOOK_IMPORT = PatchImportHook()
sys.meta_path.insert(0, HOOK_IMPORT)


def patch_init() -> None:
    os.environ["TZ"] = "UTC"
    if hasattr(time, "tzset"):
        time.tzset()

    for submodule in pkgutil.iter_modules(__path__):
        if submodule.name.startswith("_"):
            continue
        HOOK_IMPORT.add_hook(submodule.name)
    _debug.lifecycle(
        "monkeypatch.init",
        hooks=len(HOOK_IMPORT.hooks),
        applied=len(_APPLIED),
        tz=os.environ["TZ"],
    )


_APPLIED: set[str] = set()


def patch_module(name: str) -> None:
    if name in _APPLIED:
        return
    module = importlib.import_module(f".{name}", __name__)
    if name in _APPLIED:
        _debug.logic("monkeypatch.applied_on_import", target=name)
        return
    patch = getattr(module, "patch_module", None)
    if not callable(patch):
        spec = getattr(module, "__spec__", None)
        if spec is not None and getattr(spec, "_initializing", False):
            _debug.logic("monkeypatch.deferred_initializing", target=name)
            return
        raise TypeError(
            f"odoo._monkeypatches.{name} must define a callable patch_module() "
            f"(see odoo/_monkeypatches/README.md); found {patch!r}."
        )
    with _debug.perf("monkeypatch.apply", target=name, applied=len(_APPLIED)):
        patch()
    _APPLIED.add(name)
    _debug.lifecycle("monkeypatch.applied", target=name, applied=len(_APPLIED))


def applied() -> frozenset[str]:
    return frozenset(_APPLIED)
