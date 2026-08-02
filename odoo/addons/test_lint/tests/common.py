import ast
import fnmatch
import functools
import os
from os.path import join as opj

from odoo.modules import Manifest
from odoo.modules.registry import Registry
from odoo.tests.common import BaseCase, get_db_name, no_retry, tagged
from odoo.tools.misc import file_open


@tagged('at_install', '-post_install')
@no_retry
class LintCase(BaseCase):
    """ Utility method for lint-type cases
    """
    @functools.cached_property
    def registry(self):
        # lazily referenced for some tests that may need it
        return Registry(get_db_name())

    def iter_module_files(self, *globs: str, modules=None):
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

    def visit_python_file(self, path: str, node_visitor: ast.NodeVisitor, should_parse=lambda content: True) -> None:
        with file_open(path, 'rb') as f:
            content = f.read()
        if not should_parse(content):
            return
        tree = ast.parse(content, path)
        node_visitor.visit(tree)


@tagged('-at_install', 'post_install')
class RegistryLintCase(LintCase):
    """ Utility method for lint-type cases that use the registry.
    """
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.registry = Registry(get_db_name())
