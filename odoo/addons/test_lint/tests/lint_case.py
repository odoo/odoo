import fnmatch
import os
j = os.path.join

from odoo.modules import get_modules, get_module_path
from odoo.tests import BaseCase


class LintCase(BaseCase):
    """ Utility method for lint-type cases
    """

    def iter_module_files(self, *globs):
        """ Yields the paths of all the module files matching the provided globs
        (AND-ed)
        """
        for modroot in map(get_module_path, get_modules()):
            for root, _, fnames in os.walk(modroot):
                fnames = [j(root, n) for n in fnames]
                for glob in globs:
                    fnames = fnmatch.filter(fnames, glob)
                yield from fnames
