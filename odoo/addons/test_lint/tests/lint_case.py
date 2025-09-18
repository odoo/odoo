import ast
import fnmatch
import inspect
from collections.abc import Iterable
from pathlib import Path

from odoo.modules import Manifest
from odoo.modules.registry import Registry
from odoo.tests import BaseCase
from odoo.tests.common import get_db_name


def get_odoo_module_name(python_module_name: str) -> str:
    """Map a Python module path to its Odoo addon name.

    >>> get_odoo_module_name("odoo.addons.sale.models.sale_order")
    'sale'
    >>> get_odoo_module_name("odoo.models")
    'odoo'
    """
    if python_module_name.startswith("odoo.addons."):
        return python_module_name.split(".")[2]
    if python_module_name == "odoo.models":
        return "odoo"
    return python_module_name


class LintCase(BaseCase):
    """Utility methods for lint-type test cases."""

    @staticmethod
    def _module_roots(modules=None) -> list[str]:
        """Return the filesystem paths of addon modules."""
        if modules is None:
            return [m.path for m in Manifest.all_addon_manifests()]
        return [m.path for name in modules if (m := Manifest.for_addon(name))]

    def iter_module_files(self, *globs: str, modules=None):
        """Yield paths of all module files matching the provided globs (AND-ed).

        Globs use fnmatch semantics on full paths, so ``"*.py"`` matches any
        ``.py`` file at any depth and ``"**/static/**/*.js"`` matches JS files
        inside ``static/`` subdirectories.
        """
        for modroot in self._module_roots(modules):
            for dirpath, _, filenames in Path(modroot).walk():
                fnames = [str(dirpath / n) for n in filenames]
                for glob in globs:
                    fnames = fnmatch.filter(fnames, glob)
                yield from fnames


def iter_registry_methods(registry=None):
    """Yield ``(model_name, model_cls, method_name, method, parent_class)`` tuples.

    For each method on each model, walks the reversed MRO to find the class
    that first introduced the method (the "original definition").  This is the
    shared iteration pattern used by ``test_override_signatures``,
    ``test_docstring``, and ``test_naming``.
    """
    if registry is None:
        registry = Registry(get_db_name())
    for model_name, model_cls in registry.items():
        for method_name, _ in inspect.getmembers(model_cls, inspect.isroutine):
            if method_name.startswith("__"):
                continue
            # Walk reversed MRO to find the class that introduced the method
            for parent_class in reversed(model_cls.mro()[1:-1]):
                method = getattr(parent_class, method_name, None)
                if callable(method):
                    break
            else:
                continue
            yield model_name, model_cls, method_name, method, parent_class


class NodeVisitor[T]:
    """An expanded NodeVisitor which yields / returns the result of its visits.

    WARNING: ``visit_$NODE`` methods *must* return an iterable, and the result
             of ``visit`` *must* be consumed.
    """

    def visit(self, node: ast.AST) -> Iterable[T]:
        """Dispatch to a ``visit_<NodeType>`` method or ``generic_visit``."""
        visitor = getattr(self, f"visit_{node.__class__.__name__}", self.generic_visit)
        return visitor(node)

    def generic_visit(self, node: ast.AST) -> Iterable[T]:
        """Recursively visit all child nodes, yielding results."""
        for child in ast.iter_child_nodes(node):
            yield from self.visit(child)
