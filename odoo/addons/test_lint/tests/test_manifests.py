# Part of Odoo. See LICENSE file for full copyright and licensing details.

import ast
import io
import logging
import tokenize
from os.path import join as opj
from pathlib import Path

from odoo.modules.module import _DEFAULT_MANIFEST, Manifest
from odoo.tests import HttpCase, tagged
from odoo.tools.misc import file_open, file_path

from .common import LintCase

_logger = logging.getLogger(__name__)

MANIFEST_KEYS = {
    # mandatory keys
    'name', 'icon', 'addons_path', 'author', 'license',
    # optional keys
    *_DEFAULT_MANIFEST,
    # unused "informative" keys
    'contributors', 'maintainer', 'url',
    # for odoo apps store
    'price', 'currency', 'support', 'live_test_url',
}

MANIFEST_DATA_KEYS = {
    'data',
    'demo',
    'other_files',
    *[k for k in _DEFAULT_MANIFEST if k.endswith('_xml')],
}

DATA_DIRS = {
    'data',
    'demo',
    'report',
    'reports',
    'security',
    'template',
    'templates',
    'views',
    'wizard',
    'wizards',
}
# fix: addons/l10n_mt_pos/reports

DATA_EXTS = ('.csv', '.xml')


class ManifestLinter(LintCase):
    def test_manifests(self):
        module_logger = logging.getLogger('odoo.modules.module')
        assert_no_logs = self.assertNoLogs(module_logger, logging.DEBUG)
        try:
            with assert_no_logs:
                all_manifests = Manifest.all_addon_manifests()
        except AssertionError:
            for record in assert_no_logs.watcher.records:
                if "Failed to parse" in record.msg:
                    # requalify the verbosity from DEBUG to WARNING
                    record.levelno = logging.WARNING
                    record.levelname = "WARNING"
                if module_logger.isEnabledFor(record.levelno):
                    _logger.handle(record)

        for manifest in all_manifests:
            with self.subTest(module=manifest.name):
                # we want to check the content of the manifest directly without
                # parsed values
                self._test_manifest_keys(manifest)
                self._test_manifest_values(manifest)
                self._test_data_files(manifest)

    def test_manifest_depends(self):
        """Check that the dependency declarations are minimal:

        - a declared dependency already implied by another declared dependency
          is redundant: remove it, or mark it as deliberately explicit (a
          direct use) with a comment (``# ...``) on its line in the manifest;
        - an auto_install trigger element implied by another one is vacuous,
          and one that can be replaced by an equivalent declared dependency
          hides a removable dependency. The same comment convention on the
          ``'auto_install'`` list applies.
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
                    # a dependency cycle leaves some closures unresolved;
                    # under-approximating keeps the check sound
                    closures[name] = set(depends[name]).union(
                        *(closures.get(dep, set()) for dep in depends[name]))
                    stack.pop()
                    continue
                opened.add(name)
                stack.extend(dep for dep in depends[name]
                             if dep not in closures and dep not in opened)
            return closures[module]

        def auto_trigger(name: str) -> set | None:
            auto_install = manifests[name]['auto_install']  # normalized: set or False
            if auto_install is False:
                return None
            return {dep for dep in auto_install if dep in manifests} or None

        def commented_elements(name: str, manifest_key: str) -> set:
            """elements of a manifest list whose line (or the list's opening
            line) has a '# ...' comment: deliberately explicit, exempt"""
            try:
                with file_open(opj(manifests[name].path, '__manifest__.py')) as manifest_file:
                    source = manifest_file.read()
                tree = ast.parse(source)
            except (OSError, SyntaxError, ValueError):
                return set()
            node = None
            for statement in tree.body:
                if isinstance(statement, (ast.Expr, ast.Assign)) \
                        and isinstance(statement.value, ast.Dict):
                    for key, value in zip(statement.value.keys, statement.value.values):
                        if isinstance(key, ast.Constant) and key.value == manifest_key \
                                and isinstance(value, ast.List):
                            node = value
            if node is None:
                return set()
            comment_lines = set()
            for token in tokenize.generate_tokens(io.StringIO(source).readline):
                if token.type == tokenize.COMMENT \
                        and node.lineno <= token.start[0] <= node.end_lineno:
                    comment_lines.add(token.start[0])
            element_lines = {element.value: element.lineno
                             for element in node.elts if isinstance(element, ast.Constant)}
            if node.lineno in comment_lines:
                return set(element_lines)
            return {element for element, line in element_lines.items()
                    if line in comment_lines}

        for name in sorted(manifests):
            deps = depends[name]
            if not deps or not manifests[name]['installable']:
                continue
            errors = []
            auto_install = manifests[name]['auto_install'] or set()
            exempt = None  # lazy: most modules need no manifest re-read
            for dep in deps:
                if dep in auto_install:
                    continue  # removing it would change the auto_install trigger
                implier = next((other for other in deps
                                if other != dep and dep in closure(other)), None)
                if implier is None:
                    continue
                if exempt is None:
                    exempt = commented_elements(name, 'depends')
                if dep not in exempt:
                    errors.append(
                        f"dependency {dep!r} is redundant, already implied by"
                        f" {implier!r}; remove it, or comment (# ...) its line"
                        " in the manifest to keep it explicit")
            # improvable auto_install trigger (explicit list only: with True
            # the trigger simply follows the dependencies, and a list equal
            # to all of them is indistinguishable after normalization)
            if auto_install and auto_install != set(manifests[name]['depends']) \
                    and auto_install <= set(deps):
                trigger_closure = set()
                for trigger_element in auto_install:
                    trigger_closure |= {trigger_element} | closure(trigger_element)
                exempt_triggers = commented_elements(name, 'auto_install')
                for trigger_element in sorted(auto_install - exempt_triggers):
                    implied = next((other for other in auto_install
                                    if other != trigger_element
                                    and trigger_element in closure(other)), None)
                    if implied is not None:
                        errors.append(
                            f"auto_install trigger {trigger_element!r} is"
                            f" redundant, already implied by trigger {implied!r}")
                        continue
                    glue = next(
                        (g for g in deps
                         if g not in auto_install and g != trigger_element
                         and manifests[g]['installable']
                         and not manifests[g]['countries']
                         and (glue_trigger := auto_trigger(g)) is not None
                         and trigger_element in closure(g)
                         and glue_trigger <= trigger_closure
                         and not glue_trigger <= {trigger_element} | closure(trigger_element)),
                        None)
                    if glue is not None:
                        errors.append(
                            f"auto_install trigger {trigger_element!r} can be"
                            f" replaced by the declared dependency {glue!r},"
                            " which is always auto-installed alongside the rest"
                            f" of the trigger; {trigger_element!r} then becomes"
                            " an implicit dependency")
            if errors:
                with self.subTest(module=name):
                    self.fail(f"Improvable dependency declarations in module {name!r}:\n"
                              + "\n".join(f"- {error}" for error in errors))

    def _test_manifest_keys(self, manifest_data: Manifest):
        manifest_keys = manifest_data._Manifest__manifest_content.keys()
        unknown_keys = manifest_keys - MANIFEST_KEYS
        self.assertEqual(unknown_keys, set(), f"Unknown manifest keys in module {manifest_data.name!r}. Either there are typos or they must be white listed.")

    def _test_manifest_values(self, manifest_data: Manifest):
        module = manifest_data.name
        verified_keys = [
            'application',
            'auto_install',
            'category',
            'data',
            'demo',
            'description',
            'external_dependencies',
            'iap_paid_service',
            'installable',
            'post_init_hook',
            'post_load',
            'pre_init_hook',
            'summary',
            'test',
            'version',
            'website',
        ]

        if len(manifest_data.get('countries', [])) == 1 and 'l10n' not in module:
            _logger.warning(
                "Module %r specific to one single country %r should contain `l10n` in their name.",
                module, manifest_data['countries'][0])

        for key, value in manifest_data._Manifest__manifest_content.items():
            if key in _DEFAULT_MANIFEST:
                if key in verified_keys:
                    self.assertNotEqual(
                       value,
                        _DEFAULT_MANIFEST[key],
                        f"Setting manifest key {key} to the default manifest value for module {module!r}. "
                        "You can remove this key from the dict to reduce noise/inconsistencies"
                        " between manifests specifications and ease understanding of manifest"
                        " content."
                    )
                    if key == 'summary':
                        self.assertNotIn(
                            '\n',
                            value,
                            f"Module {module!r} summary should be a one-line short description",
                        )
                    elif key == 'website':
                        self.assertNotEqual(
                            value,
                            'https://www.odoo.com',
                            f"Module {module!r} website is redirecting to odoo.com, which is"
                            " useless and should be avoid unless there is a dedicated page for it.",
                        )
                        self.assertEqual(
                            bool(value),
                            value.startswith('https://'),
                            f"Module {module!r} website ({value}) should be a valid and secure url",
                        )

                expected_type = type(_DEFAULT_MANIFEST[key])
                if not isinstance(value, expected_type):
                    if key != 'auto_install':
                        _logger.warning(
                            "Wrong type for manifest value %s in module %s, expected %s",
                            key, module, expected_type)
                    elif not isinstance(value, list):
                        _logger.warning(
                            "Wrong type for manifest value %s in module %s, expected bool or list",
                            key, module)
                elif key == 'countries':
                    self._test_manifest_countries_value(module, value)
            elif key == 'icon':
                self._test_manifest_icon_value(module, value)
            elif key == 'license':
                self._test_manifest_license(module, manifest_data, value)

    def _test_manifest_icon_value(self, module, value):
        self.assertTrue(
            isinstance(value, str),
            f"Wrong type for manifest value icon in module {module!r}, expected string",
        )
        self.assertNotEqual(
            value,
            f"/{module}/static/description/icon.png",
            f"Setting manifest key icon to the default manifest value for module {module!r}. "
            "You can remove this key from the dict to reduce noise/inconsistencies between manifests specifications"
            " and ease understanding of manifest content."
        )
        if not value:
            _logger.warning(
                "Empty value specified as icon in manifest of module %r."
                " Please specify a correct value or remove this key from the manifest.",
                module)
        else:
            path_parts = value.split('/')
            try:
                file_path(opj(*path_parts[1:]))
            except FileNotFoundError:
                _logger.warning(
                    "Icon value specified in manifest of module %s wasn't found in given path."
                    " Please specify a correct value or remove this key from the manifest.",
                    module)

    def _test_manifest_countries_value(self, module, values):
        for value in values:
            if value and len(value) != 2:
                _logger.warning(
                    "Country value %s specified for the icon in manifest of module %s doesn't look like a country code."
                    "Please specify a correct value or remove this key from the manifest.",
                    value, module)

    def _test_manifest_license(self, module: str, manifest: Manifest, value: str):
        if "enterprise" in manifest.addons_path:
            self.assertEqual(
                "OEEL-1",
                value,
                f"Module {module!r} is an enterprise module and should be licensed under the Odoo"
                " Enterprise License (OEEL-1)",
            )
        else:
            self.assertEqual(
                "LGPL-3",
                value,
                f"Module {module!r} is opensource and should be licensed under the LGPL license.",
            )

    def _test_data_files(self, manifest):
        """
        Check that the data files present in a module are referenced in
        the manifest file.
        """
        # Kudos @moylop260 "file-not-used check" from the OCA pre-commit hooks
        # https://github.com/OCA/odoo-pre-commit-hooks
        modulepath = Path(manifest.path)
        module_files = {
            datafile
            for datadir in DATA_DIRS.intersection(d.name for d in modulepath.iterdir())
            for datafile in modulepath.joinpath(datadir).rglob('*.*')
            if datafile.suffix in DATA_EXTS
            # account @template files, not loaded via the manifest
            if datafile.relative_to(modulepath).parts[:2] != ('data', 'template')
        }
        manifest_files = {
            modulepath.joinpath(datafile)
            for data_key in MANIFEST_DATA_KEYS
            for datafile in manifest.get(data_key) or ()
            if datafile.partition('/')[0] in DATA_DIRS
            if datafile.endswith(DATA_EXTS)
        }

        with self.subTest(subtest="missing"):
            if unknown_files := module_files - manifest_files:
                self.fail((
                    "{count} files exist on disk but are absent from the manifest.\n\n"
                    "{module}:\n{unknown_files}\n"
                    "Delete them from disk or list them in one of {manifest_keys}."
                ).format(
                    count=len(unknown_files),
                    module=manifest.name,
                    unknown_files="".join(
                        f"- {file_not_used.relative_to(modulepath)}\n"
                        for file_not_used in unknown_files
                    ),
                    manifest_keys=sorted(MANIFEST_DATA_KEYS),
                ))

        with self.subTest(subtest="deadlink"):
            if unknown_manifest_files := manifest_files - module_files:
                self.fail((
                    "{count} missing files from disk but listed in the manifest.\n\n"
                    "{module}:\n{unknown_manifest_files}\n"
                    "Find where they actually are or delete them from the manifest."
                ).format(
                    count=len(unknown_manifest_files),
                    module=manifest.name,
                    unknown_manifest_files="".join(
                        f"- {unknown_manifest_file.relative_to(modulepath)}\n"
                        for unknown_manifest_file in unknown_manifest_files
                    )
                ))


@tagged('-standard', 'external', 'at_install', '-post_install')
class ManifestNightlyLinter(HttpCase):

    def test_manifests_websites(self):
        checked = set()
        for manifest in Manifest.all_addon_manifests():
            if (
                (url := manifest.get('website', ''))
                and url not in checked
                # Do not request non-odoo pages every night
                and url.startswith('https://www.odoo.com')
            ):
                module = manifest.name
                with self.subTest(module=module):
                    res = self.url_open(url)
                    checked.add(url)
                    self.assertEqual(
                        res.status_code, 200,
                        f"Module {module!r} website link is broken: '{url}'",
                    )
