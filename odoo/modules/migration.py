# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

""" Modules migration handling. """
import glob
import importlib.util
import inspect
import itertools
import logging
import os
import re
from collections import defaultdict
from os.path import join as opj

import odoo.release as release
import odoo.upgrade
from odoo.tools.parse_version import parse_version
from odoo.tools.misc import file_path

_logger = logging.getLogger(__name__)


VERSION_RE = re.compile(
    r"""^
        # Optional prefix with Odoo version
        ((
            6\.1|

            # "x.0" version, with x >= 6.
            [6-9]\.0|

            # multi digits "x.0" versions
            [1-9]\d+\.0|

            # x.saas~y, where x >= 7 and x <= 10
            (7|8|9|10)\.saas~[1-9]\d*|

            # saas~x.y, where x >= 11 and y between 1 and 9
            # FIXME handle version >= saas~100 (expected in year 2106)
            saas~(1[1-9]|[2-9]\d+)\.[1-9]
        )\.)?
        # After Odoo version we allow precisely 2 or 3 parts
        # note this will also allow 0.0.0 which has a special meaning
        \d+\.\d+(\.\d+)?
    $""",
    re.VERBOSE | re.ASCII,
)


def load_script(path, module_name):
    full_path = file_path(path) if not os.path.isabs(path) else path
    spec = importlib.util.spec_from_file_location(module_name, full_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class MigrationManager(object):
    """ Manages the migration of modules.

        Migrations files must be python files containing a ``migrate(cr, installed_version)``
        function. These files must respect a directory tree structure: A 'migrations' folder
        which contains a folder by version. Version can be 'module' version or 'server.module'
        version (in this case, the files will only be processed by this version of the server).
        Python file names must start by ``pre-`` or ``post-`` and will be executed, respectively,
        before and after the module initialisation. ``end-`` scripts are run after all modules have
        been updated.

        A special folder named ``0.0.0`` can contain scripts that will be run on any version change.
        In `pre` stage, ``0.0.0`` scripts are run first, while in ``post`` and ``end``, they are run last.

        Example::

            <moduledir>
            `-- migrations
                |-- 1.0
                |   |-- pre-update_table_x.py
                |   |-- pre-update_table_y.py
                |   |-- post-create_plop_records.py
                |   |-- end-cleanup.py
                |   `-- README.txt                      # not processed
                |-- 9.0.1.1                             # processed only on a 9.0 server
                |   |-- pre-delete_table_z.py
                |   `-- post-clean-data.py
                |-- 0.0.0
                |   `-- end-invariants.py               # processed on all version update
                `-- foo.py                              # not processed
    """

    def __init__(self, cr, graph):
        self.cr = cr
        self.graph = graph
        self.migrations = defaultdict(dict)
        self._get_files()

    def _get_files(self):
        def _get_upgrade_path(pkg):
            for path in odoo.upgrade.__path__:
                upgrade_path = opj(path, pkg)
                if os.path.exists(upgrade_path):
                    yield upgrade_path

        def _verify_upgrade_version(path, version):
            full_path = opj(path, version)
            if not os.path.isdir(full_path):
                return False

            if version == "tests":
                return False

            if not VERSION_RE.match(version):
                _logger.warning("Invalid version for upgrade script %r", full_path)
                return False

            return True

        def get_scripts(path):
            if not path:
                return {}
            return {
                version: glob.glob(opj(path, version, '*.py'))
                for version in os.listdir(path)
                if _verify_upgrade_version(path, version)
            }

        def check_path(path):
            try:
                return file_path(path)
            except FileNotFoundError:
                return False

        for pkg in self.graph:
            if not (hasattr(pkg, 'update') or pkg.state == 'to upgrade' or
                    getattr(pkg, 'load_state', None) == 'to upgrade'):
                continue


            self.migrations[pkg.name] = {
                'module': get_scripts(check_path(pkg.name + '/migrations')),
                'module_upgrades': get_scripts(check_path(pkg.name + '/upgrades')),
            }

            scripts = defaultdict(list)
            for p in _get_upgrade_path(pkg.name):
                for v, s in get_scripts(p).items():
                    scripts[v].extend(s)
            self.migrations[pkg.name]["upgrade"] = scripts

    def migrate_module(self, pkg, stage):
        assert stage in ('pre', 'post', 'end')
        stageformat = {
            'pre': '[>%s]',
            'post': '[%s>]',
            'end': '[$%s]',
        }
        state = pkg.state if stage in ('pre', 'post') else getattr(pkg, 'load_state', None)

        if not (hasattr(pkg, 'update') or state == 'to upgrade') or state == 'to install':
            return

        def convert_version(version):
            if version == "0.0.0":
                return version
            if version.count(".") > 2:
                return version  # the version number already contains the server version, see VERSION_RE for details
            return "%s.%s" % (release.major_version, version)

        def _get_migration_versions(pkg, stage):
            versions = sorted({
                ver
                for lv in self.migrations[pkg.name].values()
                for ver, lf in lv.items()
                if lf
            }, key=lambda k: parse_version(convert_version(k)))
            if "0.0.0" in versions:
                # reorder versions
                versions.remove("0.0.0")
                if stage == "pre":
                    versions.insert(0, "0.0.0")
                else:
                    versions.append("0.0.0")
            return versions

        def _get_migration_files(pkg, version, stage):
            """ return a list of migration script files
            """
            m = self.migrations[pkg.name]

            return sorted(
                (
                    f
                    for k in m
                    for f in m[k].get(version, [])
                    if os.path.basename(f).startswith(f"{stage}-")
                ),
                key=os.path.basename,
            )

        installed_version = getattr(pkg, 'load_version', pkg.installed_version) or ''
        parsed_installed_version = parse_version(installed_version)
        current_version = parse_version(convert_version(pkg.data['version']))

        def compare(version):
            if version == "0.0.0" and parsed_installed_version < current_version:
                return True

            full_version = convert_version(version)
            majorless_version = (version != full_version)

            if majorless_version:
                # We should not re-execute major-less scripts when upgrading to new Odoo version
                # a module in `9.0.2.0` should not re-execute a `2.0` script when upgrading to `10.0.2.0`.
                # In which case we must compare just the module version
                return parsed_installed_version[2:] < parse_version(full_version)[2:] <= current_version[2:]

            return parsed_installed_version < parse_version(full_version) <= current_version

        versions = _get_migration_versions(pkg, stage)
        for version in versions:
            if compare(version):
                for pyfile in _get_migration_files(pkg, version, stage):
                    exec_script(self.cr, installed_version, pyfile, pkg.name, stage, stageformat[stage] % version)


VALID_MIGRATE_PARAMS = list(itertools.product(
    ['cr', '_cr'],
    ['version', '_version'],
))

def exec_script(cr, installed_version, pyfile, addon, stage, version=None):
    version = version or installed_version
    name, ext = os.path.splitext(os.path.basename(pyfile))
    if ext.lower() != '.py':
        return
    try:
        mod = load_script(pyfile, name)
    except ImportError as e:
        raise ImportError('module %(addon)s: Unable to load %(stage)s-migration file %(file)s' % dict(locals(), file=pyfile)) from e

    if not hasattr(mod, 'migrate'):
        raise AttributeError(
            'module %(addon)s: Each %(stage)s-migration file must have a "migrate(cr, installed_version)" function, not found in %(file)s' % dict(
                locals(),
                file=pyfile,
            ))

    try:
        sig = inspect.signature(mod.migrate)
    except TypeError as e:
        raise TypeError("module %(addon)s: `migrate` needs to be a function, got %(migrate)r" % dict(locals(), migrate=mod.migrate)) from e

    if not (
            tuple(sig.parameters.keys()) in VALID_MIGRATE_PARAMS
        and all(p.kind in (p.POSITIONAL_ONLY, p.POSITIONAL_OR_KEYWORD) for p in sig.parameters.values())
    ):
        raise TypeError("module %(addon)s: `migrate`'s signature should be `(cr, version)`, %(func)s is %(sig)s" % dict(locals(), func=mod.migrate, sig=sig))

    _logger.info('module %(addon)s: Running migration %(version)s %(name)s' % dict(locals(), name=mod.__name__))  # noqa: G002
    mod.migrate(cr, installed_version)
