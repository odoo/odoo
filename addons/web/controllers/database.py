# Part of Odoo. See LICENSE file for full copyright and licensing details.

import csv
import datetime
import logging
import os
import re
import tempfile
from collections.abc import Iterable
from operator import itemgetter
from xml.etree import ElementTree as ET

from lxml import html

import odoo
import odoo.modules.registry
from odoo import http, release
from odoo.http import Response, content_disposition, dispatch_rpc, request
from odoo.service import db
from odoo.sql_db import db_connect
from odoo.tools.misc import file_open, str2bool
from odoo.tools.translate import _

from odoo.addons.base.models.ir_qweb import render as qweb_render

_logger = logging.getLogger(__name__)


DBNAME_PATTERN = '^[a-zA-Z0-9][a-zA-Z0-9_.-]+$'


def list_db_incompatible(databases: Iterable[str]) -> list[str]:
    """
    Check a list of databases if they are compatible with this version
    of Odoo.

    :param databases: A list of existing Postgresql databases.
    :returns: A sub-list of incompatible databases.
    """
    incompatible_databases = []
    for database_name in databases:
        with db_connect(database_name, readonly=True).cursor() as cr:
            if odoo.tools.sql.table_exists(cr, 'ir_module_module'):
                cr.execute("SELECT latest_version FROM ir_module_module WHERE name=%s", ('base',))
                base_version = cr.fetchone()
                if not base_version or not base_version[0]:
                    incompatible_databases.append(database_name)
                else:
                    # e.g. 19.1.1.3 -> 19.1
                    local_version = '.'.join(base_version[0].split('.')[:2])
                    if local_version != release.serie:
                        incompatible_databases.append(database_name)
            else:
                incompatible_databases.append(database_name)
    for database_name in incompatible_databases:
        # don't fill the pool with connections to incompatible databases
        odoo.sql_db.close_db(database_name)
    return incompatible_databases


def list_countries():
    list_countries = []
    root = ET.parse(os.path.join(odoo.tools.config.root_path, 'addons/base/data/res_country_data.xml')).getroot()
    for country in root.find('data').findall('record[@model="res.country"]'):
        name = country.find('field[@name="name"]').text
        code = country.find('field[@name="code"]').text
        list_countries.append((code, name))
    return sorted(list_countries, key=lambda c: c[1])


def scan_languages() -> list[tuple[str, str]]:
    """ Returns all languages supported for translation

    :returns: a list of (lang_code, lang_name) pairs
    :rtype: [(str, unicode)]
    """
    # read (code, name) from languages in base/data/res.lang.csv
    with file_open('base/data/res.lang.csv') as csvfile:
        reader = csv.reader(csvfile, delimiter=',', quotechar='"')
        fields = next(reader)
        code_index = fields.index("code")
        name_index = fields.index("name")
        result = [
            (row[code_index], row[name_index])
            for row in reader
        ]
    return sorted(result or [('en_US', 'English')], key=itemgetter(1))


class Database(http.Controller):

    def _render_template(self, **d):
        d.setdefault('manage', True)
        d['insecure'] = odoo.tools.config.verify_admin_password('admin')
        d['list_db'] = odoo.tools.config['list_db']
        try:
            d['langs'] = scan_languages()
        except Exception:
            _logger.exception("Could not read res.lang.csv")
            d['langs'] = []
        d['countries'] = list_countries()
        d['pattern'] = DBNAME_PATTERN
        # databases list
        try:
            d['databases'] = http.db_list()
            d['incompatible_databases'] = list_db_incompatible(d['databases'])
        except odoo.exceptions.AccessDenied:
            d['databases'] = [request.db] if request.db else []

        templates = {}

        with file_open("web/static/src/public/database_manager.qweb.html", "r") as fd:
            templates['database_manager'] = fd.read()
        with file_open("web/static/src/public/database_manager.master_input.qweb.html", "r") as fd:
            templates['master_input'] = fd.read()
        with file_open("web/static/src/public/database_manager.create_form.qweb.html", "r") as fd:
            templates['create_form'] = fd.read()

        def load(template_name):
            fromstring = html.document_fromstring if template_name == 'database_manager' else html.fragment_fromstring
            return (fromstring(templates[template_name]), template_name)

        return qweb_render('database_manager', d, load)

    @http.route('/web/database/selector', type='http', auth="none")
    def selector(self, **kw):
        if request.db:
            request.env.cr.close()
        return self._render_template(manage=False)

    @http.route('/web/database/manager', type='http', auth="none")
    def manager(self, **kw):
        if request.db:
            request.env.cr.close()
        return self._render_template()

    @http.route('/web/database/create', type='http', auth="none", methods=['POST'], csrf=False)
    def create(self, master_pwd, name, lang, password, **post):
        insecure = odoo.tools.config.verify_admin_password('admin')
        if insecure and master_pwd:
            dispatch_rpc('db', 'change_admin_password', ["admin", master_pwd])
        try:
            if not re.match(DBNAME_PATTERN, name):
                raise Exception(_('Houston, we have a database naming issue! Make sure you only use letters, numbers, underscores, hyphens, or dots in the database name, and you\'ll be golden.'))
            # country code could be = "False" which is actually True in python
            country_code = post.get('country_code') or False
            dispatch_rpc('db', 'create_database', [master_pwd, name, bool(post.get('demo')), lang, password, post['login'], country_code, post['phone']])
            credential = {'login': post['login'], 'password': password, 'type': 'password'}
            with odoo.modules.registry.Registry(name).cursor() as cr:
                env = odoo.api.Environment(cr, None, {})
                request.session.authenticate(env, credential)
                request._save_session(env)
                request.session.db = name
            return request.redirect('/odoo')
        except Exception as e:
            _logger.exception("Database creation error.")
            error = "Database creation error: %s" % (str(e) or repr(e))
        return self._render_template(error=error)

    @http.route('/web/database/duplicate', type='http', auth="none", methods=['POST'], csrf=False)
    def duplicate(self, master_pwd, name, new_name, neutralize_database=False):
        insecure = odoo.tools.config.verify_admin_password('admin')
        if insecure and master_pwd:
            dispatch_rpc('db', 'change_admin_password', ["admin", master_pwd])
        try:
            if not re.match(DBNAME_PATTERN, new_name):
                raise Exception(_('Houston, we have a database naming issue! Make sure you only use letters, numbers, underscores, hyphens, or dots in the database name, and you\'ll be golden.'))
            dispatch_rpc('db', 'duplicate_database', [master_pwd, name, new_name, neutralize_database])
            if request.db == name:
                request.env.cr.close()  # duplicating a database leads to an unusable cursor
            return request.redirect('/web/database/manager')
        except Exception as e:
            _logger.exception("Database duplication error.")
            error = "Database duplication error: %s" % (str(e) or repr(e))
            return self._render_template(error=error)

    @http.route('/web/database/drop', type='http', auth="none", methods=['POST'], csrf=False)
    def drop(self, master_pwd, name):
        insecure = odoo.tools.config.verify_admin_password('admin')
        if insecure and master_pwd:
            dispatch_rpc('db', 'change_admin_password', ["admin", master_pwd])
        try:
            dispatch_rpc('db', 'drop', [master_pwd, name])
            if request.session.db == name:
                request.session.logout()
            return request.redirect('/web/database/manager')
        except Exception as e:
            _logger.exception("Database deletion error.")
            error = "Database deletion error: %s" % (str(e) or repr(e))
            return self._render_template(error=error)

    @http.route('/web/database/backup', type='http', auth="none", methods=['POST'], csrf=False)
    def backup(self, master_pwd, name, backup_format='zip', filestore=True):
        filestore = str2bool(filestore)
        insecure = odoo.tools.config.verify_admin_password('admin')
        if insecure and master_pwd:
            dispatch_rpc('db', 'change_admin_password', ["admin", master_pwd])
        try:
            odoo.service.db.check_super(master_pwd)
            if name not in http.db_list():
                raise Exception("Database %r is not known" % name)
            ts = datetime.datetime.utcnow().strftime("%Y-%m-%d_%H-%M-%S")
            filename = "%s_%s.%s" % (name, ts, backup_format)
            headers = [
                ('Content-Type', 'application/octet-stream; charset=binary'),
                ('Content-Disposition', content_disposition(filename)),
            ]
            dump_stream = odoo.service.db.dump_db(name, None, backup_format, filestore)
            response = Response(dump_stream, headers=headers, direct_passthrough=True)
            return response
        except Exception as e:
            _logger.exception('Database.backup')
            error = "Database backup error: %s" % (str(e) or repr(e))
            return self._render_template(error=error)

    @http.route('/web/database/restore', type='http', auth="none", methods=['POST'], csrf=False, max_content_length=None)
    def restore(self, master_pwd, backup_file, name, copy=False, neutralize_database=False):
        insecure = odoo.tools.config.verify_admin_password('admin')
        if insecure and master_pwd:
            dispatch_rpc('db', 'change_admin_password', ["admin", master_pwd])
        try:
            data_file = None
            db.check_super(master_pwd)
            with tempfile.NamedTemporaryFile(delete=False) as data_file:
                backup_file.save(data_file)
            db.restore_db(name, data_file.name, str2bool(copy), neutralize_database)
            return request.redirect('/web/database/manager')
        except Exception as e:
            error = "Database restore error: %s" % (str(e) or repr(e))
            return self._render_template(error=error)
        finally:
            if data_file:
                os.unlink(data_file.name)

    @http.route('/web/database/change_password', type='http', auth="none", methods=['POST'], csrf=False)
    def change_password(self, master_pwd, master_pwd_new):
        try:
            dispatch_rpc('db', 'change_admin_password', [master_pwd, master_pwd_new])
            return request.redirect('/web/database/manager')
        except Exception as e:
            error = "Master password update error: %s" % (str(e) or repr(e))
            return self._render_template(error=error)

    @http.route('/web/database/list', type='jsonrpc', auth='none')
    def list(self):
        """
        Used by Mobile application for listing database
        :return: List of databases
        :rtype: list
        """
        return http.db_list()
