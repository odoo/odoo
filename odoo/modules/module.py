# Part of Odoo. See LICENSE file for full copyright and licensing details.
"""Utility functions to manage module manifest files and discovery."""
from __future__ import annotations

import ast
import copy
import functools
import importlib
import importlib.metadata
import io
import logging
import os
import re
import sys
import tokenize
import traceback
import typing
from collections.abc import Collection, Iterable, Mapping
from os.path import join as opj

import odoo.addons
import odoo.release as release
import odoo.tools as tools
import odoo.upgrade

if typing.TYPE_CHECKING:
    from unittest import TestCase

try:
    from packaging.requirements import InvalidRequirement, Requirement
except ImportError:
    class InvalidRequirement(Exception):  # type: ignore[no-redef]
        ...

    class Requirement:  # type: ignore[no-redef]
        def __init__(self, pydep):
            if not re.fullmatch(r'[\w\-]+', pydep):  # check that we have no versions or marker in pydep
                msg = f"Package `packaging` is required to parse `{pydep}` external dependency and is not installed"
                raise Exception(msg)
            self.marker = None
            self.specifier = None
            self.name = pydep

__all__ = [
    "Manifest",
    "adapt_version",
    "check_dependency_declarations",
    "get_manifest",
    "get_module_path",
    "get_modules",
    "get_resource_from_path",
    "initialize_sys_path",
    "load_openerp_module",
]

MODULE_NAME_RE = re.compile(r'^\w{1,256}$')
MANIFEST_NAMES = ['__manifest__.py']
README = ['README.rst', 'README.md', 'README.txt', 'README']

_DEFAULT_MANIFEST = {
    # Mandatory fields (with no defaults):
    # - author
    # - license
    # - name
    # Derived fields are computed in the Manifest class.
    'application': False,
    'bootstrap': False,  # web
    'assets': {},
    'auto_install': False,
    'category': 'Uncategorized',
    'cloc_exclude': [],
    'configurator_snippets': {},  # website themes
    'configurator_snippets_addons': {},  # website themes
    'countries': [],
    'data': [],
    'demo': [],
    'demo_xml': [],
    'depends': [],
    'description': '',  # defaults to README file
    'external_dependencies': {},
    'iap_paid_service': False,
    'init_xml': [],
    'installable': True,
    'images': [],  # website
    'images_preview_theme': {},  # website themes
    'kpi_providers': [],
    'live_test_url': '',  # website themes
    'new_page_templates': {},  # website themes
    'other_files': [],
    'post_init_hook': '',
    'post_load': '',
    'pre_init_hook': '',
    'sequence': 100,
    'summary': '',
    'test': [],
    'theme_customizations': {},  # themes
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

current_test: TestCase | None = None
"""The current test being run, if any"""


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

    # hook for upgrades and namespace freeze
    if not getattr(initialize_sys_path, 'called', False):  # only initialize once
        odoo.addons.__path__._path_finder = lambda *a: None  # prevent path invalidation
        odoo.upgrade.__path__._path_finder = lambda *a: None  # prevent path invalidation
        sys.meta_path.insert(0, UpgradeHook())
        initialize_sys_path.called = True  # type: ignore


@typing.final
class Manifest(Mapping[str, typing.Any]):
    """The manifest data of a module."""

    def __init__(self, *, path: str, manifest_content: dict):
        assert os.path.isabs(path), "path of module must be absolute"
        self.path = path
        _, self.name = os.path.split(path)
        if not MODULE_NAME_RE.match(self.name):
            raise FileNotFoundError(f"Invalid module name: {self.name}")
        self.__manifest_content = manifest_content

    @property
    def addons_path(self) -> str:
        parent_path, name = os.path.split(self.path)
        assert name == self.name
        return parent_path

    @functools.cached_property
    def __manifest_cached(self) -> dict:
        """Parsed and validated manifest data from the file."""
        return _load_manifest(self.name, self.__manifest_content)

    @functools.cached_property
    def description(self):
        """The description of the module defaulting to the README file."""
        if (desc := self.__manifest_cached.get('description')):
            return desc
        for file_name in README:
            try:
                with tools.file_open(opj(self.path, file_name)) as f:
                    return f.read()
            except OSError:
                pass
        return ''

    @functools.cached_property
    def version(self):
        try:
            return self.__manifest_cached['version']
        except Exception:  # noqa: BLE001
            return adapt_version('1.0')

    @functools.cached_property
    def icon(self) -> str:
        return get_module_icon(self.name)

    @functools.cached_property
    def static_path(self) -> str | None:
        static_path = opj(self.path, 'static')
        manifest = self.__manifest_cached
        if (manifest['installable'] or manifest['assets']) and os.path.isdir(static_path):
            return static_path
        return None

    def __getitem__(self, key: str):
        if key in ('description', 'icon', 'addons_path', 'version', 'static_path'):
            return getattr(self, key)
        return copy.deepcopy(self.__manifest_cached[key])

    def raw_value(self, key):
        return copy.deepcopy(self.__manifest_cached.get(key))

    def __iter__(self):
        manifest = self.__manifest_cached
        yield from manifest
        for key in ('description', 'icon', 'addons_path', 'version', 'static_path'):
            if key not in manifest:
                yield key

    def check_manifest_dependencies(self) -> None:
        """Check that the dependecies of the manifest are available.

        - Checking for external python dependencies
        - Checking binaries are available in PATH

        On missing dependencies, raise an error.
        """
        depends = self.get('external_dependencies')
        if not depends:
            return
        for pydep in depends.get('python', []):
            check_python_external_dependency(pydep)

        for binary in depends.get('bin', []):
            try:
                tools.find_in_path(binary)
            except OSError:
                msg = "Unable to find {dependency!r} in path"
                raise MissingDependency(msg, binary)

    def __bool__(self):
        return True

    def __len__(self):
        return sum(1 for _ in self)

    def __repr__(self):
        return f'Manifest({self.name})'

    # limit cache size because this may get called from any module with any input
    @staticmethod
    @functools.lru_cache(10_000)
    def _get_manifest_from_addons(module: str) -> Manifest | None:
        """Get the module's manifest from a name. Searching only in addons paths."""
        for adp in odoo.addons.__path__:
            if manifest := Manifest._from_path(opj(adp, module)):
                return manifest
        return None

    @staticmethod
    def for_addon(module_name: str, *, display_warning: bool = True) -> Manifest | None:
        """Get the module's manifest from a name.

        :param module: module's name
        :param display_warning: log a warning if the module is not found
        """
        if not MODULE_NAME_RE.match(module_name):
            # invalid module name
            return None
        if mod := Manifest._get_manifest_from_addons(module_name):
            return mod
        if display_warning:
            _logger.warning('module %s: manifest not found', module_name)
        return None

    @staticmethod
    def _from_path(path: str, env=None) -> Manifest | None:
        """Given a path, read the manifest file."""
        for manifest_name in MANIFEST_NAMES:
            try:
                with tools.file_open(opj(path, manifest_name), env=env) as f:
                    manifest_content = ast.literal_eval(f.read())
            except OSError:
                pass
            except Exception:  # noqa: BLE001
                _logger.debug("Failed to parse the manifest file at %r", path, exc_info=True)
            else:
                return Manifest(path=path, manifest_content=manifest_content)
        return None

    @staticmethod
    def all_addon_manifests() -> list[Manifest]:
        """Read all manifests in the addons paths."""
        modules: dict[str, Manifest] = {}
        for adp in odoo.addons.__path__:
            if not os.path.isdir(adp):
                _logger.warning("addons path is not a directory: %s", adp)
                continue
            for file_name in os.listdir(adp):
                if file_name in modules:
                    continue
                if mod := Manifest._from_path(opj(adp, file_name)):
                    assert file_name == mod.name
                    modules[file_name] = mod
        return sorted(modules.values(), key=lambda m: m.name)


def get_module_path(module: str, display_warning: bool = True) -> str | None:
    """Return the path of the given module.

    Search the addons paths and return the first path where the given
    module is found. If downloaded is True, return the default addons
    path if nothing else is found.

    """
    # TODO deprecate
    mod = Manifest.for_addon(module, display_warning=display_warning)
    return mod.path if mod else None


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
    """ Get the path to the module's icon. Invalid module names are accepted. """
    manifest = Manifest.for_addon(module, display_warning=False)
    if manifest and 'icon' in manifest.__dict__:
        # we have a value in the cached property
        return manifest.icon
    fpath = ''
    if manifest:
        fpath = manifest.raw_value('icon') or ''
        fpath = fpath.lstrip('/')
    if not fpath:
        fpath = f"{module}/static/description/icon.png"
    try:
        tools.file_path(fpath)
        return "/" + fpath
    except FileNotFoundError:
        return "/base/static/description/icon.png"


def _load_manifest(module: str, manifest_content: dict) -> dict:
    """ Load and validate the module manifest.

    Return a new dictionary with cleaned and validated keys.
    """

    manifest = copy.deepcopy(_DEFAULT_MANIFEST)
    manifest.update(manifest_content)

    if not manifest.get('author'):
        # Altought contributors and maintainer are not documented, it is
        # not uncommon to find them in manifest files, use them as
        # alternative.
        author = manifest.get('contributors') or manifest.get('maintainer') or ''
        manifest['author'] = str(author)
        _logger.warning("Missing `author` key in manifest for %r, defaulting to %r", module, str(author))

    if not manifest.get('license'):
        manifest['license'] = 'LGPL-3'
        _logger.warning("Missing `license` key in manifest for %r, defaulting to LGPL-3", module)

    if module == 'base':
        manifest['depends'] = []
    elif not manifest['depends']:
        # prevent the hack `'depends': []` except 'base' module
        manifest['depends'] = ['base']

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

    return manifest


def get_manifest(module: str, mod_path: str | None = None) -> Mapping[str, typing.Any]:
    """
    Get the module manifest.

    :param str module: The name of the module (sale, purchase, ...).
    :param Optional[str] mod_path: The optional path to the module on
        the file-system. If not set, it is determined by scanning the
        addons-paths.
    :returns: The module manifest as a dict or an empty dict
        when the manifest was not found.
    """
    if mod_path:
        mod = Manifest._from_path(mod_path)
        if mod and mod.name != module:
            raise ValueError(f"Invalid path for module {module}: {mod_path}")
    else:
        mod = Manifest.for_addon(module, display_warning=False)
    return mod if mod is not None else {}


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
        manifest = Manifest.for_addon(module_name)
        if post_load := manifest.get('post_load'):
            getattr(sys.modules[qualname], post_load)()

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
    return [m.name for m in Manifest.all_addon_manifests()]


def check_dependency_declarations() -> None:
    """Check the ``depends`` declared by every available module and log a
    warning for each improvable declaration:

    - missing explicit dependency: an auto-installable module whose whole
      dependency closure is already contained in the checked module's one
      (it is therefore always installed alongside it, and depending on it
      installs nothing more) and which subsumes one of the declared
      dependencies; the checked module can depend on it instead, and safely
      extend it.
    - redundant implicit dependency: a declared dependency that is already
      implied by another declared dependency. A comment (``# ...``) on the
      dependency's line in the manifest (or on the ``'depends'`` opening
      line) marks it as deliberately explicit and silences the warning.
    - improvable auto_install trigger: a trigger element that is already
      implied by another one (vacuous), or that can be replaced by a declared
      dependency which is always auto-installed alongside the rest of the
      trigger, letting the replaced element become an implicit dependency.
      The same comment convention on the ``'auto_install'`` list applies.
    """
    manifests = {m.name: m for m in Manifest.all_addon_manifests()}
    depends = {name: [d for d in manifest['depends'] if d in manifests]
               for name, manifest in manifests.items()}

    closures: dict[str, set] = {}

    def closure(module: str) -> set:
        stack, opened = [module], set()
        while stack:
            name = stack[-1]
            if name in closures:
                stack.pop()
                continue
            if name in opened:
                result = set()
                for dep in depends[name]:
                    result.add(dep)
                    # a dependency cycle leaves some closures unresolved;
                    # under-approximating keeps the warnings sound
                    result |= closures.get(dep, set())
                closures[name] = result
                stack.pop()
                continue
            opened.add(name)
            stack.extend(dep for dep in depends[name]
                         if dep not in closures and dep not in opened)
        return closures[module]

    def trigger(name: str) -> set | None:
        auto_install = manifests[name]['auto_install']  # normalized: set or False
        if auto_install is False:
            return None
        return {dep for dep in auto_install if dep in manifests} or None

    # relevance filter, not a correctness one (whether a suggested glue is
    # co-installed is guaranteed by the closure check below): glue triggered
    # by the base/web/mail application layer alone bridges no specific
    # feature, so suggesting it would be noise for almost every module
    generic = {'base', 'web', 'mail'} & manifests.keys()
    changed = True
    while changed:
        changed = False
        for name in manifests:
            if name not in generic and manifests[name]['installable'] \
                    and not manifests[name]['countries'] \
                    and (auto_trigger := trigger(name)) and auto_trigger <= generic:
                generic |= {name} | closure(name)
                changed = True

    # glue candidates: guaranteed auto-installation (installable, no country
    # gating), a trigger that carries a signal (not generic, not a
    # localization pack installed with accounting on any database)
    candidates = {
        name: auto_trigger
        for name in manifests
        if (auto_trigger := trigger(name))
        and manifests[name]['installable']
        and not manifests[name]['countries']
        and not (auto_trigger & generic)
        and not (name.startswith('l10n_') and auto_trigger == {'account'})
    }

    def commented_deps(module: str, manifest_key: str = 'depends') -> set:
        """elements of a manifest list whose line (or the list's opening
        line) has a '# ...' comment: deliberately explicit, exempt from
        warnings"""
        try:
            with tools.file_open(opj(manifests[module].path, MANIFEST_NAMES[0])) as f:
                source = f.read()
            tree = ast.parse(source)
        except (OSError, SyntaxError, ValueError):
            return set()
        node = None
        for statement in tree.body:
            if isinstance(statement, (ast.Expr, ast.Assign)) \
                    and isinstance(statement.value, ast.Dict):
                for key, val in zip(statement.value.keys, statement.value.values):
                    if isinstance(key, ast.Constant) and key.value == manifest_key \
                            and isinstance(val, ast.List):
                        node = val
        if node is None:
            return set()
        comment_lines = set()
        try:
            for token in tokenize.generate_tokens(io.StringIO(source).readline):
                if token.type == tokenize.COMMENT \
                        and node.lineno <= token.start[0] <= node.end_lineno:
                    comment_lines.add(token.start[0])
        except tokenize.TokenizeError:
            return set()
        dep_lines = {element.value: element.lineno
                     for element in node.elts if isinstance(element, ast.Constant)}
        if node.lineno in comment_lines:
            return set(dep_lines)
        return {dep for dep, line in dep_lines.items() if line in comment_lines}

    for name in sorted(manifests):
        deps = depends[name]
        if not deps or not manifests[name]['installable']:
            continue
        auto_install = manifests[name]['auto_install'] or set()
        exempt = None  # lazy: most modules need no manifest re-read
        # redundant implicit dependencies
        for dep in deps:
            if dep in auto_install:
                continue  # removing it would change the auto_install trigger
            implier = next((other for other in deps
                            if other != dep and dep in closure(other)), None)
            if implier is None:
                continue
            if exempt is None:
                exempt = commented_deps(name)
            if dep not in exempt:
                _logger.warning(
                    "Module %s: dependency %r is redundant, already implied by"
                    " %r; remove it, or comment (# ...) its line in the"
                    " manifest to keep it explicit.", name, dep, implier)
        # improvable auto_install trigger (explicit list only); all trigger
        # elements must be known modules to reason about them
        if auto_install and auto_install != set(manifests[name]['depends']) \
                and auto_install <= set(deps):
            trigger_closure = set()
            for t in auto_install:
                trigger_closure |= {t} | closure(t)
            exempt_triggers = commented_deps(name, 'auto_install')
            for t in sorted(auto_install - exempt_triggers):
                implied = next((other for other in auto_install
                                if other != t and t in closure(other)), None)
                if implied is not None:
                    _logger.warning(
                        "Module %s: auto_install trigger %r is redundant,"
                        " already implied by trigger %r.", name, t, implied)
                    continue
                glue = next(
                    (g for g in deps
                     if g not in auto_install and g != t
                     and manifests[g]['installable']
                     and not manifests[g]['countries']
                     and (glue_trigger := trigger(g)) is not None
                     and t in closure(g)
                     and glue_trigger <= trigger_closure
                     and not glue_trigger <= {t} | closure(t)),
                    None)
                if glue is not None:
                    _logger.warning(
                        "Module %s: auto_install trigger %r can be replaced by"
                        " the declared dependency %r, which is always"
                        " auto-installed alongside the rest of the trigger;"
                        " %r then becomes an implicit dependency.",
                        name, t, glue, t)
        # missing explicit dependencies on always-installed glue modules
        available = {name}
        for dep in deps:
            available |= {dep} | closure(dep)
        # glue may only be suggested from the addons directories the module
        # already spans: its own and those of its explicit and implicit
        # dependencies (e.g. community modules never get enterprise glue)
        allowed_paths = {manifests[mod].addons_path for mod in available}
        for glue, auto_trigger in candidates.items():
            if glue == name or glue in available or manifests[glue].addons_path not in allowed_paths:
                continue
            if name in closure(glue) or not closure(glue) <= available:
                continue
            subsumed = next(
                (dep for dep in deps
                 if dep in closure(glue)
                 and not auto_trigger <= {dep} | closure(dep)
                 and not any(dep in closure(other) for other in deps if other != dep)),
                None)
            if subsumed is not None:
                _logger.warning(
                    "Module %s: missing explicit dependency %r: it is always"
                    " auto-installed alongside %s, and it subsumes the"
                    " dependency on %r.", name, glue, name, subsumed)


def adapt_version(version: str) -> str:
    """Reformat the version of the module into a canonical format."""
    version_str_parts = version.split('.')
    if not (2 <= len(version_str_parts) <= 5):
        raise ValueError(f"Invalid version {version!r}, must have between 2 and 5 parts")
    serie = release.major_version
    if version.startswith(serie) and not version_str_parts[0].isdigit():
        # keep only digits for parsing
        version_str_parts[0] = ''.join(c for c in version_str_parts[0] if c.isdigit())
    try:
        version_parts = [int(v) for v in version_str_parts]
    except ValueError as e:
        raise ValueError(f"Invalid version {version!r}") from e
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


class MissingDependency(Exception):
    def __init__(self, msg_template: str, dependency: str):
        self.dependency = dependency
        super().__init__(msg_template.format(dependency=dependency))


def check_python_external_dependency(pydep: str) -> None:
    try:
        requirement = Requirement(pydep)
    except InvalidRequirement as e:
        msg = f"{pydep} is an invalid external dependency specification: {e}"
        raise ValueError(msg) from e
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
            _logger.warning("python external dependency on '%s' does not appear to be a valid PyPI package. Using a PyPI package name is recommended.", pydep)
            return
        except ImportError:
            pass
        msg = "External dependency {dependency!r} not installed: %s" % (e,)
        raise MissingDependency(msg, pydep) from e
    if requirement.specifier and not requirement.specifier.contains(version):
        msg = f"External dependency version mismatch: {{dependency}} (installed: {version})"
        raise MissingDependency(msg, pydep)


def load_script(path: str, module_name: str):
    full_path = tools.file_path(path) if not os.path.isabs(path) else path
    spec = importlib.util.spec_from_file_location(module_name, full_path)
    assert spec and spec.loader, f"spec not found for {module_name}"
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
