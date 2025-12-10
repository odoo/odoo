# Part of Odoo. See LICENSE file for full copyright and licensing details.

import csv
import datetime
import logging
import os
import tempfile
from collections.abc import Iterable
from operator import itemgetter
from xml.etree import ElementTree as ET

from lxml import html
from werkzeug.exceptions import UnprocessableEntity
from werkzeug.utils import send_file

import odoo
import odoo.modules.db
import odoo.modules.registry
from odoo import http, release
from odoo.http import Response, request
from odoo.sql_db import db_connect
from odoo.tools.misc import file_open, str2bool
from odoo.tools.translate import _

from odoo.addons.base.models.ir_qweb import render as qweb_render

_logger = logging.getLogger(__name__)


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


def _render_template(**d):
    d.setdefault('manage', True)
    d['insecure'] = odoo.tools.config.verify_admin_password('admin')
    d['list_db'] = odoo.tools.config['list_db']
    try:
        d['langs'] = scan_languages()
    except Exception:
        _logger.exception("Could not read res.lang.csv")
        d['langs'] = []
    d['countries'] = list_countries()
    d['pattern'] = odoo.modules.db.DB_NAME_RE.pattern
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


def _render_exception(exception, **d):
    http_status = getattr(exception, 'http_status', 422)
    verb = request.httprequest.path.rpartition('/')[2]  # create, backup, restore, ...
    error = f"Could not {verb} database. {exception.args[0]}"
    http_body = _render_template(error=error, **d)
    return Response(http_body, http_status)


def verify_access(master_pwd):
    odoo.modules.db.verify_db_management_enabled()
    insecure = odoo.tools.config.verify_admin_password('admin')
    if insecure and master_pwd:
        # if the .odoorc admin password is "admin", use the provided
        # master_pwd as new password.
        odoo.tools.config.set_admin_password(master_pwd)
        odoo.tools.config.save(['admin_passwd'])
    odoo.modules.db.verify_admin_password(master_pwd)


class Database(http.Controller):
    @http.route('/web/database/selector', type='http', auth="none")
    def selector(self, **kw):
        if request.db:
            request.env.cr.close()
        return _render_template(manage=False)

    @http.route('/web/database/manager', type='http', auth="none")
    def manager(self, **kw):
        if request.db:
            request.env.cr.close()
        return _render_template()

    @http.route('/web/database/create', type='http', auth="none", methods=['POST'], csrf=False)
    def create(self, master_pwd, name, lang, password, **post):
        if not odoo.modules.db.DB_NAME_RE.fullmatch(name):
            e = _("Houston, we have a database naming issue! Make sure you only use letters, numbers, underscores, hyphens, or dots in the database name, and you'll be golden.")
            res = Response(_render_template(error=e), UnprocessableEntity.code)
            raise UnprocessableEntity(response=res)
        try:
            verify_access(master_pwd)
            odoo.modules.db.create(
                name,
                demo=str2bool(post.get('demo', False)),
                user_login=post['login'],
                user_password=password,
                lang=lang,
                country_code=post.get('country_code', '') or False,
                phone=post['phone'],
            )
            # log the current user in the new database
            credential = {'login': post['login'], 'password': password, 'type': 'password'}
            with odoo.modules.registry.Registry(name).cursor() as cr:
                env = odoo.api.Environment(cr, None, {})
                request.session.authenticate(env, credential)
                request._save_session(env)
                request.session.db = name
            return request.redirect('/odoo')
        except Exception as e:
            e.error_response = _render_exception(e)
            raise

    @http.route('/web/database/duplicate', type='http', auth="none", methods=['POST'], csrf=False)
    def duplicate(self, master_pwd, name, new_name, neutralize_database=False):
        if not odoo.modules.db.DB_NAME_RE.fullmatch(name):
            e = _("Houston, we have a database naming issue! Make sure you only use letters, numbers, underscores, hyphens, or dots in the database name, and you'll be golden.")
            res = Response(_render_template(error=e), UnprocessableEntity.code)
            raise UnprocessableEntity(response=res)
        try:
            verify_access(master_pwd)
            odoo.modules.db.duplicate(
                name,
                new_name,
                neutralize_database=str2bool(neutralize_database),
            )
            if request.db == name:
                request.env.cr.close()  # duplicating a database leads to an unusable cursor
            return request.redirect('/web/database/manager')
        except Exception as e:
            e.error_response = _render_exception(e)
            raise

    @http.route('/web/database/drop', type='http', auth="none", methods=['POST'], csrf=False)
    def drop(self, master_pwd, name):
        try:
            verify_access(master_pwd)
            odoo.modules.db.drop(name)
            if request.session.db == name:
                request.session.logout()
            return request.redirect('/web/database/manager')
        except Exception as e:
            e.error_response = _render_exception(e)
            raise

    @http.route('/web/database/backup', type='http', auth="none", methods=['POST'], csrf=False)
    def backup(self, master_pwd, name, backup_format='zip', filestore=True):
        dump_file = None
        try:
            verify_access(master_pwd)
            dump_file = tempfile.TemporaryFile()  # noqa: SIM115

            odoo.modules.db.dump(
                name,
                dump_file,
                backup_format=backup_format,
                with_filestore=str2bool(filestore),
            )
            dump_file.seek(0)
            ts = datetime.datetime.utcnow().strftime("%Y-%m-%d_%H-%M-%S")
            return send_file(
                dump_file,
                request.httprequest.environ,
                mimetype=('application/zip' if backup_format == 'zip'
                     else 'application/octet-stream'),
                as_attachment=True,
                download_name=f'{name}_{ts}.{backup_format}',
            )
        except Exception as e:
            if dump_file is not None:
                dump_file.close()
            e.error_response = _render_exception(e)
            raise

    @http.route('/web/database/restore', type='http', auth="none", methods=['POST'], csrf=False, max_content_length=None)
    def restore(self, master_pwd, backup_file, name, copy=False, neutralize_database=False):
        data_file = None
        try:
            verify_access(master_pwd)
            with tempfile.NamedTemporaryFile(delete=False) as data_file:
                backup_file.save(data_file)
            odoo.modules.db.restore(
                name,
                data_file.name,
                copy=str2bool(copy),
                neutralize_database=str2bool(neutralize_database),
            )
            return request.redirect('/web/database/manager')
        except Exception as e:
            e.error_response = _render_exception(e)
            raise
        finally:
            if data_file:
                os.unlink(data_file.name)

    @http.route('/web/database/change_password', type='http', auth="none", methods=['POST'], csrf=False)
    def change_password(self, master_pwd, master_pwd_new):
        try:
            odoo.modules.db.verify_admin_password(master_pwd)
            odoo.tools.config.set_admin_password(master_pwd_new)
            odoo.tools.config.save(['admin_passwd'])
            return request.redirect('/web/database/manager')
        except Exception as e:
            e.error_response = _render_exception(e)
            raise

    @http.route('/web/database/list', type='jsonrpc', auth='none')
    def list(self):
        """
        Used by Mobile application for listing database

        :return: List of databases
        :rtype: list
        """
        return http.db_list()
