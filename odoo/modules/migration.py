# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

""" Modules migration handling. """

from collections import defaultdict
import glob
import logging
import os
from os.path import join as opj

from odoo.modules.module import get_resource_path
import odoo.release as release
import odoo.tools as tools
from odoo.tools.parse_version import parse_version
from odoo.tools import pycompat

if pycompat.PY2:
    import imp
    def load_script(path, module_name):
        fp, fname = tools.file_open(path, pathinfo=True)
        fp2 = None

        # pylint: disable=file-builtin,undefined-variable
        if not isinstance(fp, file):
            # imp.load_source need a real file object, so we create
            # one from the file-like object we get from file_open
            fp2 = os.tmpfile()
            fp2.write(fp.read())
            fp2.seek(0)

        try:
            return imp.load_source(module_name, fname, fp2 or fp)
        finally:
            if fp:
                fp.close()
            if fp2:
                fp2.close()

else:
    import importlib.util
    def load_script(path, module_name):
        full_path = get_resource_path(*path.split(os.path.sep))
        spec = importlib.util.spec_from_file_location(module_name, full_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module


_logger = logging.getLogger(__name__)

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
                `-- foo.py                              # not processed
    """

    def __init__(self, cr, graph):
        self.cr = cr
        self.graph = graph
        self.migrations = defaultdict(dict)
        self._get_files()
        self._init_migration_history()

    def _init_migration_history(self):
        """
        Create stages for a module graph to allow restarting the migration.

        For each module, an ir_logging entry is created for the three possible stages of the migration
        (pre, post, end) and the `line` column will contain either an empty string (the scripts have
        not yet been applied for that stage) or a non-empty string (the scripts have been applied).
        This trick is necessary for 'end' scripts, since we need to possibly restart them even if
        the module's version is already up-to-date (since the `latest_version` is updated after
        post scripts are run on an ir_module record).

        Note that this mechanism assumes previous migrations were clean - there should be no
        ir_logging entries of level `UPGRADE` prior to migration.

        Also, explicit commits in a migration script will very, very probably break this feature
        and prevent restarting a migration properly.
        """
        if not tools.table_exists(self.cr, 'ir_logging'):
            # database is brand new, skip
            return
        for pkg in self.graph:
            if parse_version(pkg.installed_version) > parse_version(release.major_version):
                continue
            version = pkg.installed_version or '0.0'  # new modules have None as installed_version
            vals = ('server', self.cr.dbname, 'UPGRADE', version, pkg.name, 'migrate')
            self.cr.execute("""
                SELECT count(*)
                FROM ir_logging
                WHERE type=%s AND dbname=%s AND level=%s
                AND message=%s AND path=%s AND func=%s
            """, vals)
            count = self.cr.fetchone()
            if count and count[0]:
                _logger.debug('skipping registration of migration stages for module %s currently in version %s, already done' % (pkg.name, version))
                continue
            _logger.debug('registering migration stages for module %s currently in version %s' % (pkg.name, version))
            for stage in ('pre', 'post', 'end'):
                vals = (stage, 'server', self.cr.dbname, 'UPGRADE', version, pkg.name, 'migrate', '')
                self.cr.execute("""
                    INSERT INTO ir_logging(name,type,dbname,level,message,path,func,line,create_date,write_date)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, now() at time zone 'UTC', now() at time zone 'UTC')
                """, vals)

    def _clean_migration_history(self):
        """
        Remove the whole migration history in one go.

        This step **must** be called once all scripts have been loaded and should
        be followed by an explicit commit.
        """
        _logger.debug('cleaning migration history after successful upgrade to version %s' % release.major_version)
        self.cr.execute("""DELETE FROM ir_logging WHERE level='UPGRADE'""")

    def _get_files(self):
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
                'maintenance': get_scripts(get_resource_path('base', 'maintenance', 'migrations', pkg.name)),
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

        def _get_migration_versions(pkg):
            versions = sorted({
                ver
                for lv in self.migrations[pkg.name].values()
                for ver, lf in lv.items()
                if lf
            }, key=lambda k: parse_version(convert_version(k)))
            return versions

        def _get_migration_files(pkg, version, stage):
            """ return a list of migration script files
            """
            m = self.migrations[pkg.name]
            lst = []

            mapping = {
                'module': opj(pkg.name, 'migrations'),
                'maintenance': opj('base', 'maintenance', 'migrations', pkg.name),
            }

            for x in mapping:
                if version in m.get(x):
                    for f in m[x][version]:
                        if not f.startswith(stage + '-'):
                            continue
                        lst.append(opj(mapping[x], version, f))
            lst.sort()
            return lst

        def _check_migration_stage(pkg, stage):
            """Check if a module's migration stage has already been applied."""
            vals = (stage, 'server', self.cr.dbname, 'UPGRADE', pkg.name, 'migrate')
            self.cr.execute("""
                SELECT count(*)
                FROM ir_logging
                WHERE name=%s AND type=%s AND dbname=%s
                AND level=%s AND path=%s AND func=%s
                AND line!=''
            """, vals)
            done = bool(self.cr.fetchone()[0])
            _logger.debug('checking migration stage %s for module %s: %s' % (stage, pkg.name, 'done' if done else 'not done'))
            return done

        def _register_migration_stage(pkg, stage):
            """Mark a module's migration stage as having been applied."""
            _logger.debug('marking migration stage %s for module %s as done' % (stage, pkg.name))
            vals = (stage, 'server', self.cr.dbname, 'UPGRADE', pkg.name, 'migrate')
            self.cr.execute("""
                UPDATE ir_logging
                SET line='done', write_date=now() at time zone 'UTC'
                WHERE name=%s AND type=%s AND dbname=%s
                AND level=%s AND path=%s AND func=%s
            """, vals)

        def _get_pkg_version(pkg):
            vals = ('end', 'server', self.cr.dbname, 'UPGRADE', pkg.name, 'migrate')
            self.cr.execute("""
                SELECT message
                FROM ir_logging
                WHERE name=%s AND type=%s AND dbname=%s
                AND level=%s AND path=%s AND func=%s
            """, vals)
            version = self.cr.fetchone()
            return version and version[0]

        installed_version = getattr(pkg, 'load_version', pkg.installed_version) if stage != 'end' else _get_pkg_version(pkg) or ''
        parsed_installed_version = parse_version(installed_version)
        current_version = parse_version(convert_version(pkg.data['version']))

        if _check_migration_stage(pkg, stage):
            _logger.info('module %s: Skipping %s migration step as it was marked as done in a previous upgrade attempt' % (pkg.name, stage))
            return

        versions = _get_migration_versions(pkg)

        for version in versions:
            if parsed_installed_version < parse_version(convert_version(version)) <= current_version:

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
        _register_migration_stage(pkg, stage)
