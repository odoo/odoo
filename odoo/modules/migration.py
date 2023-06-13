# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

""" Modules migration handling. """

from collections import defaultdict
import glob
import importlib.util
import logging
import os
from os.path import join as opj

from odoo.modules.module import get_resource_path
import odoo.release as release
import odoo.upgrade
from odoo.tools.parse_version import parse_version

_logger = logging.getLogger(__name__)


def load_script(path, module_name):
    full_path = get_resource_path(*path.split(os.path.sep)) if not os.path.isabs(path) else path
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

        def get_scripts(path):
            if not path:
                return {}
            return {
                version: glob.glob(opj(path, version, '*.py'))
                for version in os.listdir(path)
                if os.path.isdir(opj(path, version))
            }

        for pkg in self.graph:
            if not (hasattr(pkg, 'update') or pkg.state == 'to upgrade' or
                    getattr(pkg, 'load_state', None) == 'to upgrade'):
                continue

            self.migrations[pkg.name] = {
                'module': get_scripts(get_resource_path(pkg.name, 'migrations')),
                'module_upgrades': get_scripts(get_resource_path(pkg.name, 'upgrades')),
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
            if version.count('.') >= 2:
                return version  # the version number already contains the server version
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
                strfmt = {'addon': pkg.name,
                          'stage': stage,
                          'version': stageformat[stage] % version,
                          }

                for pyfile in _get_migration_files(pkg, version, stage):
                    name, ext = os.path.splitext(os.path.basename(pyfile))
                    if ext.lower() != '.py':
                        continue
                    mod = None
                    try:
                        mod = load_script(pyfile, name)
                        _logger.info('module %(addon)s: Running migration %(version)s %(name)s' % dict(strfmt, name=mod.__name__))
                        migrate = mod.migrate
                    except ImportError:
                        _logger.exception('module %(addon)s: Unable to load %(stage)s-migration file %(file)s' % dict(strfmt, file=pyfile))
                        raise
                    except AttributeError:
                        _logger.error('module %(addon)s: Each %(stage)s-migration file must have a "migrate(cr, installed_version)" function' % strfmt)
                    else:
                        migrate(self.cr, installed_version)
                    finally:
                        if mod:
                            del mod
