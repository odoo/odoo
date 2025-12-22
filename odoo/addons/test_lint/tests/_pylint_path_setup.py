from __future__ import annotations

import inspect
import os
import sys
from typing import Sequence

from astroid import modutils
from astroid.interpreter._import import spec
from pylint.lint import utils

def register(linter):
    # very old pylint (/ astroid) versions not compatible with this plugin but
    # not really needing it either as they don't try importing stuff nearly as
    # hard
    if 'type' not in inspect.signature(spec.ModuleSpec).parameters:
        return

    # prevent pylint from messing with sys.path
    utils._augment_sys_path = lambda _: sys.path
    modutils.modpath_from_file = modpath_from_file
    spec._SPEC_FINDERS = (AddonsPackageFinder,) + spec._SPEC_FINDERS

    addons_path = os.environ.get('ADDONS_PATH')
    if addons_path:
        import odoo.addons
        for p in addons_path.split(os.pathsep):
            normp = os.path.normcase(os.path.abspath(p.strip()))
            odoo.addons.__path__.append(normp)

def modpath_from_file(filename, path):
    if filename == "./addons":
        return ['odoo', 'addons']
    return modutils.modpath_from_file_with_callback(
        filename,
        path,
        modutils.check_modpath_has_init,
    )

class AddonsPackageFinder(spec.Finder):
    """Finder which special cases odoo and odoo.addons, such that they're
    forcefully discovered as namespace packages since otherwise they get
    discovered as directory packages.
    """
    @staticmethod
    def find_module(
        modname: str,
        module_parts: Sequence[str],
        processed: list[str],
        submodule_path: Sequence[str] | None,
    ) -> spec.ModuleSpec | None:
        modname = '.'.join([*processed, modname])
        if modname in ('odoo', 'odoo.addons'):
            return spec.ModuleSpec(
                name=modname,
                location="",
                origin="namespace",
                type=spec.ModuleType.PY_NAMESPACE,
                submodule_search_locations=sys.modules[modname].__path__,
            )
        else:
            return None

    def contribute_to_path(self, spec: spec.ModuleSpec, processed: list[str]) -> Sequence[str] | None:
        return spec.submodule_search_locations

