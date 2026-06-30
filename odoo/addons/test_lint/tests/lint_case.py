import ast
import fnmatch
import os
from collections.abc import Iterable
from os.path import join as opj
from typing import Generic, TypeVar

from odoo.modules import Manifest
from odoo.tests import BaseCase


class LintCase(BaseCase):
    """ Utility method for lint-type cases
    """

    def iter_module_files(self, *globs, modules=None):
        """ Yields the paths of all the module files matching the provided globs
        (AND-ed)
        """
        if modules is None:
            module_roots = [m.path for m in Manifest.all_addon_manifests()]
        else:
            module_roots = [m.path for name in modules if (m := Manifest.for_addon(name))]
        for modroot in module_roots:
            for root, _, fnames in os.walk(modroot):
                fnames = [opj(root, n) for n in fnames]
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
