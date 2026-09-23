from __future__ import annotations

import sys
import types
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import pytest

__all__ = ["stub_odoo_packages"]


def _stub_package(name: str, path: Path) -> None:
    if name in sys.modules:
        return
    module = types.ModuleType(name)
    module.__path__ = [str(path)]
    module.__package__ = name
    module.__file__ = str(path / "__init__.py")
    sys.modules[name] = module


def _package_chain(directory: Path) -> list[tuple[str, Path]] | None:
    intermediates: list[Path] = []
    current = directory.parent
    while current.name and current.name != "odoo":
        intermediates.append(current)
        current = current.parent

    if current.name != "odoo":
        return None

    chain = [("odoo", current)]
    name = "odoo"
    for package_dir in reversed(intermediates):
        name = f"{name}.{package_dir.name}"
        chain.append((name, package_dir))
    return chain


def stub_odoo_packages(conftest_file: str) -> None:
    tests_dir = Path(conftest_file).resolve().parent
    chain = _package_chain(tests_dir)
    if chain is None:
        raise RuntimeError(
            f"could not locate the 'odoo' package root above {conftest_file!r}"
        )
    for name, path in chain:
        _stub_package(name, path)


def _stub_for_target(target: Path) -> None:
    directory = target if target.is_dir() else target.parent
    if not (directory / "conftest.py").is_file():
        return
    chain = _package_chain(directory)
    if chain is None:
        return
    for name, path in chain:
        _stub_package(name, path)


def pytest_load_initial_conftests(
    early_config: pytest.Config, parser: pytest.Parser, args: list[str]
) -> None:
    rootpath = Path(early_config.rootpath)

    testpaths = [
        (rootpath / entry).resolve() for entry in early_config.getini("testpaths")
    ]
    if not testpaths:
        return

    selected = [arg for arg in args if not arg.startswith("-")]
    targets = [(rootpath / arg.split("::")[0]).resolve() for arg in selected]
    if not targets:
        targets = testpaths

    for target in targets:
        within = any(
            target == testpath or testpath in target.parents for testpath in testpaths
        )
        if within:
            _stub_for_target(target)


pytest_load_initial_conftests.tryfirst = True  # type: ignore[attr-defined]
