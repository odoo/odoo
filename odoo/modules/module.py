# Part of Odoo. See LICENSE file for full copyright and licensing details.
"""Utility functions to manage module manifest files and discovery."""

import ast
import copy
import functools
import importlib
import importlib.metadata
import logging
import os
import re
import sys
import traceback
from collections.abc import Collection, Iterable
from os.path import join as opj
from os.path import normpath

import odoo.addons
import odoo.release as release
import odoo.tools as tools
import odoo.upgrade
from odoo.tools.misc import file_path

try:
    from packaging.requirements import InvalidRequirement, Requirement
except ImportError:
    class InvalidRequirement(Exception):  # type: ignore[no-redef]
        ...

    class Requirement:  # type: ignore[no-redef]
        def __init__(self, pydep):
            if not re.fullmatch(r'\w+', pydep):  # check that we have no versions or marker in pydep
                msg = f"Package `packaging` is required to parse `{pydep}` external dependency and is not installed"
                raise Exception(msg)
            self.marker = None
            self.specifier = None
            self.name = pydep

__all__ = [
    "adapt_version",
    "check_manifest_dependencies",
    "get_manifest",
    "get_module_path",
    "get_modules",
    "get_modules_with_version",
    "get_resource_from_path",
    "initialize_sys_path",
    "load_openerp_module",
]

MANIFEST_NAMES = ['__manifest__.py']
README = ['README.rst', 'README.md', 'README.txt']

_DEFAULT_MANIFEST = {
    #addons_path: f'/path/to/the/addons/path/of/{module}',  # automatic
    'application': False,
    'bootstrap': False,  # web
    'assets': {},
    'author': 'Odoo S.A.',
    'auto_install': False,
    'category': 'Uncategorized',
    'cloc_exclude': [],
    'configurator_snippets': {},  # website themes
    'countries': [],
    'data': [],
    'demo': [],
    'demo_xml': [],
    'depends': [],
    'description': '',
    'external_dependencies': {},
    #icon: f'/{module}/static/description/icon.png',  # automatic
    'init_xml': [],
    'installable': True,
    'images': [],  # website
    'images_preview_theme': {},  # website themes
    #license, mandatory
    'live_test_url': '',  # website themes
    'new_page_templates': {},  # website themes
    #name, mandatory
    'post_init_hook': '',
    'post_load': '',
    'pre_init_hook': '',
    'sequence': 100,
    'summary': '',
    'test': [],
    'update_xml': [],
    'uninstall_hook': '',
    'version': '1.0',
    'web': False,
    'website': '',
}

# matches field definitions like
#     partner_id: base.ResPartner = fields.Many2one
#     partner_id = fields.Many2one[base.ResPartner]
TYPED_FIELD_DEFINITION_RE = re.compile(r'''
    \b (?P<field_name>\w+) \s*
    (:\s*(?P<field_type>[^ ]*))? \s*
    = \s*
    fields\.(?P<field_class>Many2one|One2many|Many2many)
    (\[(?P<type_param>[^\]]+)\])?
''', re.VERBOSE)

_logger = logging.getLogger(__name__)

current_test: bool = False
"""Indicates whteher we are in a test mode"""


class UpgradeHook:
    """Makes the legacy `migrations` package being `odoo.upgrade`"""

    def find_spec(self, fullname, path=None, target=None):
        if re.match(r"^odoo\.addons\.base\.maintenance\.migrations\b", fullname):
            # We can't trigger a DeprecationWarning in this case.
            # In order to be cross-versions, the multi-versions upgrade scripts (0.0.0 scripts),
            # the tests, and the common files (utility functions) still needs to import from the
            # legacy name.
            return importlib.util.spec_from_loader(fullname, self)

    def load_module(self, name):
        assert name not in sys.modules

        canonical_upgrade = name.replace("odoo.addons.base.maintenance.migrations", "odoo.upgrade")

        if canonical_upgrade in sys.modules:
            mod = sys.modules[canonical_upgrade]
        else:
            mod = importlib.import_module(canonical_upgrade)

        sys.modules[name] = mod

        return sys.modules[name]


def initialize_sys_path() -> None:
    """
    Setup the addons path ``odoo.addons.__path__`` with various defaults
    and explicit directories.
    """
    for path in (
        # tools.config.addons_base_dir,  # already present
        tools.config.addons_data_dir,
        *tools.config['addons_path'],
        tools.config.addons_community_dir,
    ):
        if os.access(path, os.R_OK) and path not in odoo.addons.__path__:
            odoo.addons.__path__.append(path)

    # hook odoo.upgrade on upgrade-path
    legacy_upgrade_path = os.path.join(tools.config.addons_base_dir, 'base/maintenance/migrations')
    for up in tools.config['upgrade_path'] or [legacy_upgrade_path]:
        if up not in odoo.upgrade.__path__:
            odoo.upgrade.__path__.append(up)

    # create decrecated module alias from odoo.addons.base.maintenance.migrations to odoo.upgrade
    spec = importlib.machinery.ModuleSpec("odoo.addons.base.maintenance", None, is_package=True)
    maintenance_pkg = importlib.util.module_from_spec(spec)
    maintenance_pkg.migrations = odoo.upgrade  # type: ignore
    sys.modules["odoo.addons.base.maintenance"] = maintenance_pkg
    sys.modules["odoo.addons.base.maintenance.migrations"] = odoo.upgrade

    # hook deprecated module alias from openerp to odoo and "crm"-like to odoo.addons
    if not getattr(initialize_sys_path, 'called', False):  # only initialize once
        sys.meta_path.insert(0, UpgradeHook())
        initialize_sys_path.called = True  # type: ignore


def get_module_path(module: str, downloaded: bool = False, display_warning: bool = True) -> str | None:
    """Return the path of the given module.

    Search the addons paths and return the first path where the given
    module is found. If downloaded is True, return the default addons
    path if nothing else is found.

    """
    if re.search(r"[\/\\]", module):
        return None
    for adp in odoo.addons.__path__:
        files = [opj(adp, module, manifest) for manifest in MANIFEST_NAMES] +\
                [opj(adp, module + '.zip')]
        if any(os.path.exists(f) for f in files):
            return opj(adp, module)

    if downloaded:
        return opj(tools.config.addons_data_dir, module)
    if display_warning:
        _logger.warning('module %s: module not found', module)
    return None


def get_resource_from_path(path: str) -> tuple[str, str, str] | None:
    """Tries to extract the module name and the resource's relative path
    out of an absolute resource path.

    If operation is successful, returns a tuple containing the module name, the relative path
    to the resource using '/' as filesystem seperator[1] and the same relative path using
    os.path.sep seperators.

    [1] same convention as the resource path declaration in manifests

    :param path: absolute resource path

    :rtype: tuple
    :return: tuple(module_name, relative_path, os_relative_path) if possible, else None
    """
    resource = None
    sorted_paths = sorted(odoo.addons.__path__, key=len, reverse=True)
    for adpath in sorted_paths:
        # force trailing separator
        adpath = os.path.join(adpath, "")
        if os.path.commonprefix([adpath, path]) == adpath:
            resource = path.replace(adpath, "", 1)
            break

    if resource:
        relative = resource.split(os.path.sep)
        if not relative[0]:
            relative.pop(0)
        module = relative.pop(0)
        return (module, '/'.join(relative), os.path.sep.join(relative))
    return None


def get_module_icon(module: str) -> str:
    fpath = f"{module}/static/description/icon.png"
    try:
        file_path(fpath)
        return "/" + fpath
    except FileNotFoundError:
        return "/base/static/description/icon.png"


def get_module_icon_path(module: str) -> str:
    try:
        return file_path(f"{module}/static/description/icon.png")
    except FileNotFoundError:
        return file_path("base/static/description/icon.png")


def module_manifest(path: str | None) -> str | None:
    """Returns path to module manifest if one can be found under `path`, else `None`."""
    if not path:
        return None
    for manifest_name in MANIFEST_NAMES:
        candidate = opj(path, manifest_name)
        if os.path.isfile(candidate):
            return candidate
    return None


def get_module_root(path: str) -> str | None:
    """
    Get closest module's root beginning from path

        # Given:
        # /foo/bar/module_dir/static/src/...

        get_module_root('/foo/bar/module_dir/static/')
        # returns '/foo/bar/module_dir'

        get_module_root('/foo/bar/module_dir/')
        # returns '/foo/bar/module_dir'

        get_module_root('/foo/bar')
        # returns None

    @param path: Path from which the lookup should start

    @return:  Module root path or None if not found
    """
    while not module_manifest(path):
        new_path = os.path.abspath(opj(path, os.pardir))
        if path == new_path:
            return None
        path = new_path
    return path


def load_manifest(module: str, mod_path: str | None = None) -> dict:
    """ Load the module manifest from the file system. """

    if not mod_path:
        mod_path = get_module_path(module, downloaded=True)
    manifest_file = module_manifest(mod_path)

    if not manifest_file:
        _logger.debug('module %s: no manifest file found %s', module, MANIFEST_NAMES)
        return {}
    assert mod_path, "We have a file, therefore we have a path"

    manifest = copy.deepcopy(_DEFAULT_MANIFEST)

    manifest['icon'] = get_module_icon(module)

    with tools.file_open(manifest_file, mode='r') as f:
        manifest.update(ast.literal_eval(f.read()))

    if not manifest['description']:
        readme_path = [opj(mod_path, x) for x in README
                       if os.path.isfile(opj(mod_path, x))]
        if readme_path:
            with tools.file_open(readme_path[0]) as fd:
                manifest['description'] = fd.read()

    if not manifest.get('license'):
        manifest['license'] = 'LGPL-3'
        _logger.warning("Missing `license` key in manifest for %r, defaulting to LGPL-3", module)

    depends = manifest['depends']
    assert isinstance(depends, Collection)

    # auto_install is either `False` (by default) in which case the module
    # is opt-in, either a list of dependencies in which case the module is
    # automatically installed if all dependencies are (special case: [] to
    # always install the module), either `True` to auto-install the module
    # in case all dependencies declared in `depends` are installed.
    if isinstance(manifest['auto_install'], Iterable):
        manifest['auto_install'] = auto_install_set = set(manifest['auto_install'])
        non_dependencies = auto_install_set.difference(depends)
        assert not non_dependencies, (
            "auto_install triggers must be dependencies,"
            f" found non-dependencies [{', '.join(non_dependencies)}] for module {module}"
        )
    elif manifest['auto_install']:
        manifest['auto_install'] = set(depends)

    try:
        manifest['version'] = adapt_version(str(manifest['version']))
    except ValueError as e:
        if manifest['installable']:
            raise ValueError(f"Module {module}: invalid manifest") from e
    if manifest['installable'] and not check_version(str(manifest['version']), should_raise=False):
        _logger.warning("The module %s has an incompatible version, setting installable=False", module)
        manifest['installable'] = False

    manifest['addons_path'] = normpath(opj(mod_path, os.pardir))

    return manifest


def get_manifest(module: str, mod_path: str | None = None) -> dict:
    """
    Get the module manifest.

    :param str module: The name of the module (sale, purchase, ...).
    :param Optional[str] mod_path: The optional path to the module on
        the file-system. If not set, it is determined by scanning the
        addons-paths.
    :returns: The module manifest as a dict or an empty dict
        when the manifest was not found.
    :rtype: dict
    """
    return copy.deepcopy(_get_manifest_cached(module, mod_path))


@functools.cache
def _get_manifest_cached(module, mod_path=None):
    return load_manifest(module, mod_path)


def load_openerp_module(module_name: str) -> None:
    """ Load an OpenERP module, if not already loaded.

    This loads the module and register all of its models, thanks to either
    the MetaModel metaclass, or the explicit instantiation of the model.
    This is also used to load server-wide module (i.e. it is also used
    when there is no model to register).
    """

    qualname = f'odoo.addons.{module_name}'
    if qualname in sys.modules:
        return

    try:
        __import__(qualname)

        # Call the module's post-load hook. This can done before any model or
        # data has been initialized. This is ok as the post-load hook is for
        # server-wide (instead of registry-specific) functionalities.
        info = get_manifest(module_name)
        if info['post_load']:
            getattr(sys.modules[qualname], info['post_load'])()

    except AttributeError as err:
        _logger.critical("Couldn't load module %s", module_name)
        trace = traceback.format_exc()
        match = TYPED_FIELD_DEFINITION_RE.search(trace)
        if match and "most likely due to a circular import" in trace:
            field_name = match['field_name']
            field_class = match['field_class']
            field_type = match['field_type'] or match['type_param']
            if "." not in field_type:
                field_type = f"{module_name}.{field_type}"
            raise AttributeError(
                f"{err}\n"
                "To avoid circular import for the the comodel use the annotation syntax:\n"
                f"    {field_name}: {field_type} = fields.{field_class}(...)\n"
                "and add at the beggining of the file:\n"
                "    from __future__ import annotations"
            ).with_traceback(err.__traceback__) from None
        raise
    except Exception:
        _logger.critical("Couldn't load module %s", module_name)
        raise


def get_modules() -> list[str]:
    """Get the list of module names that can be loaded.
    """
    def listdir(dir):
        def clean(name):
            name = os.path.basename(name)
            if name[-4:] == '.zip':
                name = name[:-4]
            return name

        def is_really_module(name):
            for mname in MANIFEST_NAMES:
                if os.path.isfile(opj(dir, name, mname)):
                    return True
        return [
            clean(it)
            for it in os.listdir(dir)
            if is_really_module(it)
        ]

    plist: list[str] = []
    for ad in odoo.addons.__path__:
        if not os.path.exists(ad):
            _logger.warning("addons path does not exist: %s", ad)
            continue
        plist.extend(listdir(ad))
    return sorted(set(plist))


def get_modules_with_version() -> dict[str, str]:
    """Get the module list with the linked version."""
    modules = get_modules()
    res = dict.fromkeys(modules, adapt_version('1.0'))
    for module in modules:
        try:
            info = get_manifest(module)
            res[module] = info['version']
        except Exception:
            continue
    return res


def adapt_version(version: str) -> str:
    """Reformat the version of the module into a canonical format."""
    version_str_parts = version.split('.')
    if not (2 <= len(version_str_parts) <= 5):
        raise ValueError(f"Invalid version {version!r}, must have between 2 and 5 parts")
    try:
        version_parts = [int(v) for v in version_str_parts[-3:]]
    except ValueError as e:
        raise ValueError(f"Invalid version {version!r}") from e
    serie = release.major_version
    if len(version_parts) <= 3 and not version.startswith(serie):
        # prefix the version with serie
        return f"{serie}.{version}"
    return version


def check_version(version: str, should_raise: bool = True) -> bool:
    """Check that the version is in a valid format for the current release."""
    version = adapt_version(version)
    serie = release.major_version
    if version.startswith(serie + '.'):
        return True
    if should_raise:
        raise ValueError(
            f"Invalid version {version!r}. Modules should have a version in format"
            f" `x.y`, `x.y.z`, `{serie}.x.y` or `{serie}.x.y.z`.")
    return False


def check_python_external_dependency(pydep: str) -> None:
    try:
        requirement = Requirement(pydep)
    except InvalidRequirement as e:
        msg = f"{pydep} is an invalid external dependency specification: {e}"
        raise Exception(msg) from e
    if requirement.marker and not requirement.marker.evaluate():
        _logger.debug(
            "Ignored external dependency %s because environment markers do not match",
            pydep
        )
        return
    try:
        version = importlib.metadata.version(requirement.name)
    except importlib.metadata.PackageNotFoundError as e:
        try:
            # keep compatibility with module name but log a warning instead of info
            importlib.import_module(pydep)
            _logger.warning("python external dependency on '%s' does not appear o be a valid PyPI package. Using a PyPI package name is recommended.", pydep)
            return
        except ImportError:
            pass
        msg = f"External dependency {pydep} not installed: {e}"
        raise Exception(msg) from e
    if requirement.specifier and not requirement.specifier.contains(version):
        msg = f"External dependency version mismatch: {pydep} (installed: {version})"
        raise Exception(msg)


def check_manifest_dependencies(manifest: dict) -> None:
    """Check that the dependecies of the manifest are available.

    - Checking for external python dependencies
    - Checking binaries are available in PATH

    On missing dependencies, raise an error.
    """
    depends = manifest.get('external_dependencies')
    if not depends:
        return
    for pydep in depends.get('python', []):
        check_python_external_dependency(pydep)

    for binary in depends.get('bin', []):
        try:
            tools.find_in_path(binary)
        except OSError:
            raise Exception('Unable to find %r in path' % (binary,))
