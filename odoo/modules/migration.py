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
import odoo.tools as tools
from odoo.tools.parse_version import parse_version

_logger = logging.getLogger(__name__)


def load_script(path, module_name):
    full_path = get_resource_path(*path.split(os.path.sep)) if not os.path.isabs(path) else path
    spec = importlib.util.spec_from_file_location(module_name, full_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class MigrationManager(object):
    """
        This class manage the migration of modules
        Migrations files must be python files containing a `migrate(cr, installed_version)`
        function. Theses files must respect a directory tree structure: A 'migrations' folder
        which containt a folder by version. Version can be 'module' version or 'server.module'
        version (in this case, the files will only be processed by this version of the server).
        Python file names must start by `pre-` or `post-` and will be executed, respectively,
        before and after the module initialisation. `end-` scripts are run after all modules have
        been updated.
        A special folder named `0.0.0` can contain scripts that will be run on any version change.
        In `pre` stage, `0.0.0` scripts are run first, while in `post` and `end`, they are run last.
        Example:
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
        def _get_upgrades_paths(pkg):
            for path in tools.config['upgrades_paths'].split(','):
                upgrade_path = opj(path, pkg)
                if os.path.exists(upgrade_path):
                    return upgrade_path
            return None

        def get_scripts(path):
            if not path:
                return {}
            return {
                version: glob.glob1(opj(path, version), '*.py')
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
                'maintenance': get_scripts(get_resource_path('base', 'maintenance', 'migrations', pkg.name)),
                'maintenance_upgrades': get_scripts(get_resource_path('base', 'maintenance', 'upgrades', pkg.name)),
                'upgrades': get_scripts(_get_upgrades_paths(pkg.name)),
            }

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
                return version  # the version number already containt the server version
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
            lst = []

            mapping = {
                'module': opj(pkg.name, 'migrations'),
                'module_upgrades': opj(pkg.name, 'upgrades'),
                'maintenance': opj('base', 'maintenance', 'migrations', pkg.name),
                'maintenance_upgrades': opj('base', 'maintenance', 'upgrades', pkg.name),
            }

            for path in tools.config['upgrades_paths'].split(','):
                if os.path.exists(opj(path, pkg.name)):
                    mapping['upgrades'] = opj(path, pkg.name)
                    break

            for x in mapping:
                if version in m.get(x):
                    for f in m[x][version]:
                        if not f.startswith(stage + '-'):
                            continue
                        lst.append(opj(mapping[x], version, f))
            lst.sort()
            return lst

        installed_version = getattr(pkg, 'load_version', pkg.installed_version) or ''
        parsed_installed_version = parse_version(installed_version)
        current_version = parse_version(convert_version(pkg.data['version']))

        versions = _get_migration_versions(pkg, stage)

        for version in versions:
            if ((version == "0.0.0" and parsed_installed_version < current_version)
               or parsed_installed_version < parse_version(convert_version(version)) <= current_version):

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
