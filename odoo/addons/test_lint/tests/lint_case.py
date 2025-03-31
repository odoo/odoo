import ast
import fnmatch
import os
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


class NodeVisitor():
    """Simple NodeVisitor."""

    def visit(self, node):
        method = 'visit_' + node.__class__.__name__
        visitor = getattr(self, method, self.generic_visit)
        return visitor(node)

    def generic_visit(self, node):
        for child in ast.iter_child_nodes(node):
            yield from self.visit(child)
