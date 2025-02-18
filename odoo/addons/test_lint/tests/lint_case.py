import ast
import fnmatch
import os
from collections.abc import Iterable
from typing import Generic, TypeVar

j = os.path.join

from odoo.modules import get_modules, get_module_path
from odoo.tests import BaseCase


class LintCase(BaseCase):
    """ Utility method for lint-type cases
    """

    def iter_module_files(self, *globs, modules=None):
        """ Yields the paths of all the module files matching the provided globs
        (AND-ed)
        """
        for modroot in map(get_module_path, modules or get_modules()):
            for root, _, fnames in os.walk(modroot):
                fnames = [j(root, n) for n in fnames]
                for glob in globs:
                    fnames = fnmatch.filter(fnames, glob)
                yield from fnames


T = TypeVar('T')
class NodeVisitor(Generic[T]):
    """An expanded NodeVisitor which yields / returns the result of its visits.

    WARNING: ``visit_$NODE`` methods *must* return an iterable, and the result
             of ``visit`` *must* be consumed
    """

    def visit(self, node: ast.AST) -> Iterable[T]:
        method = 'visit_' + node.__class__.__name__
        visitor = getattr(self, method, self.generic_visit)
        return visitor(node)

    def generic_visit(self, node: ast.AST) -> Iterable[T]:
        for child in ast.iter_child_nodes(node):
            yield from self.visit(child)
