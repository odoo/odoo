import datetime
import logging
import pathlib
import re
import tempfile

from lxml import html

from werkzeug.datastructures import FileStorage

import odoo
import odoo.modules.registry
from odoo import http
from odoo.http import Response, content_disposition, dispatch_rpc, request
from odoo.service import db
from odoo.tools.misc import file_open, str2bool
from odoo.tools.translate import _

from odoo.addons.base.models.ir_qweb import render as qweb_render

_logger = logging.getLogger(__name__)


DBNAME_PATTERN = r"^[a-zA-Z0-9][a-zA-Z0-9_.-]+\Z"


class Database(http.Controller):
    def _render_template(self, **d) -> str:
        d.setdefault("manage", True)
        d["insecure"] = odoo.tools.config.verify_admin_password("admin")
        d["list_db"] = odoo.tools.config["list_db"]
        d["langs"] = odoo.service.db.exp_list_lang()
        d["countries"] = odoo.service.db.exp_list_countries()
        d["pattern"] = DBNAME_PATTERN
        # databases list
        try:
            d["databases"] = http.db_list()
            d["incompatible_databases"] = odoo.service.db.list_db_incompatible(
                d["databases"]
            )
        except odoo.exceptions.AccessDenied:
            d["databases"] = [request.db] if request.db else []

        templates = {}

        with file_open("web/static/src/public/database_manager.qweb.html", "r") as fd:
            templates["database_manager"] = fd.read()
        with file_open(
            "web/static/src/public/database_manager.master_input.qweb.html", "r"
        ) as fd:
            templates["master_input"] = fd.read()
        with file_open(
            "web/static/src/public/database_manager.create_form.qweb.html", "r"
        ) as fd:
            templates["create_form"] = fd.read()

        def load(template_name):
            fromstring = (
                html.document_fromstring
                if template_name == "database_manager"
                else html.fragment_fromstring
            )
            return (fromstring(templates[template_name]), template_name)

        return qweb_render("database_manager", d, load)

    @http.route("/web/database/selector", type="http", auth="none")
    def selector(self, **kw) -> str:
        if request.db:
            request.env.cr.close()
        return self._render_template(manage=False)

    @http.route("/web/database/manager", type="http", auth="none")
    def manager(self, **kw) -> str:
        if request.db:
            request.env.cr.close()
        return self._render_template()

    @http.route(
        "/web/database/create",
        type="http",
        auth="none",
        methods=["POST"],
        csrf=False,
    )
    def create(
        self, master_pwd: str, name: str, lang: str, password: str, **post
    ) -> str | Response:
        insecure = odoo.tools.config.verify_admin_password("admin")
        if insecure and master_pwd:
            dispatch_rpc("db", "change_admin_password", ["admin", master_pwd])
        try:
            if not re.match(DBNAME_PATTERN, name):
                raise ValueError(
                    _(
                        "Houston, we have a database naming issue! Make sure you only use letters, numbers, underscores, hyphens, or dots in the database name, and you'll be golden."
                    )
                )
            # country code could be = "False" which is actually True in python
            country_code = post.get("country_code") or False
            dispatch_rpc(
                "db",
                "create_database",
                [
                    master_pwd,
                    name,
                    bool(post.get("demo")),
                    lang,
                    password,
                    post["login"],
                    country_code,
                    post["phone"],
                ],
            )
            credential = {
                "login": post["login"],
                "password": password,
                "type": "password",
            }
            with odoo.modules.registry.Registry(name).cursor() as cr:
                env = odoo.api.Environment(cr, None, {})
                request.session.authenticate(env, credential)
                request._save_session(env)
                request.session.db = name
            return request.redirect("/odoo")
        except Exception as e:
            _logger.exception("Database creation error.")
            error = f"Database creation error: {str(e) or repr(e)}"
        return self._render_template(error=error)

    @http.route(
        "/web/database/duplicate",
        type="http",
        auth="none",
        methods=["POST"],
        csrf=False,
    )
    def duplicate(
        self,
        master_pwd: str,
        name: str,
        new_name: str,
        neutralize_database: bool | str = False,
    ) -> str | Response:
        insecure = odoo.tools.config.verify_admin_password("admin")
        if insecure and master_pwd:
            dispatch_rpc("db", "change_admin_password", ["admin", master_pwd])
        try:
            if not re.match(DBNAME_PATTERN, new_name):
                raise ValueError(
                    _(
                        "Houston, we have a database naming issue! Make sure you only use letters, numbers, underscores, hyphens, or dots in the database name, and you'll be golden."
                    )
                )
            dispatch_rpc(
                "db",
                "duplicate_database",
                [master_pwd, name, new_name, str2bool(neutralize_database)],
            )
            if request.db == name:
                request.env.cr.close()  # duplicating a database leads to an unusable cursor
            return request.redirect("/web/database/manager")
        except Exception as e:
            _logger.exception("Database duplication error.")
            error = f"Database duplication error: {str(e) or repr(e)}"
            return self._render_template(error=error)

    @http.route(
        "/web/database/drop",
        type="http",
        auth="none",
        methods=["POST"],
        csrf=False,
    )
    def drop(self, master_pwd: str, name: str) -> str | Response:
        insecure = odoo.tools.config.verify_admin_password("admin")
        if insecure and master_pwd:
            dispatch_rpc("db", "change_admin_password", ["admin", master_pwd])
        try:
            dispatch_rpc("db", "drop", [master_pwd, name])
            if request.session.db == name:
                request.env.cr.close()  # dropping this database killed our cursor
                request.session.logout()
            return request.redirect("/web/database/manager")
        except Exception as e:
            _logger.exception("Database deletion error.")
            error = f"Database deletion error: {str(e) or repr(e)}"
            return self._render_template(error=error)

    @http.route(
        "/web/database/backup",
        type="http",
        auth="none",
        methods=["POST"],
        csrf=False,
    )
    def backup(
        self,
        master_pwd: str,
        name: str,
        backup_format: str = "zip",
        filestore: bool | str = True,
    ) -> str | Response:
        filestore = str2bool(filestore)
        insecure = odoo.tools.config.verify_admin_password("admin")
        if insecure and master_pwd:
            dispatch_rpc("db", "change_admin_password", ["admin", master_pwd])
        try:
            odoo.service.db.check_super(master_pwd)
            if name not in http.db_list():
                raise ValueError(f"Database {name!r} is not known")
            ts = datetime.datetime.now(datetime.UTC).strftime("%Y-%m-%d_%H-%M-%S")
            filename = f"{name}_{ts}.{backup_format}"
            headers = [
                ("Content-Type", "application/octet-stream; charset=binary"),
                ("Content-Disposition", content_disposition(filename)),
            ]
            dump_stream = odoo.service.db.dump_db(name, None, backup_format, filestore)
            return Response(dump_stream, headers=headers, direct_passthrough=True)
        except Exception as e:
            _logger.exception("Database.backup")
            error = f"Database backup error: {str(e) or repr(e)}"
            return self._render_template(error=error)

    @http.route(
        "/web/database/restore",
        type="http",
        auth="none",
        methods=["POST"],
        csrf=False,
        max_content_length=None,
    )
    def restore(
        self,
        master_pwd: str,
        backup_file: FileStorage,
        name: str,
        copy: bool | str = False,
        neutralize_database: bool | str = False,
    ) -> str | Response:
        insecure = odoo.tools.config.verify_admin_password("admin")
        if insecure and master_pwd:
            dispatch_rpc("db", "change_admin_password", ["admin", master_pwd])
        tmp_path = None
        try:
            db.check_super(master_pwd)
            with tempfile.NamedTemporaryFile(delete=False) as tmp:
                backup_file.save(tmp)
                tmp_path = pathlib.Path(tmp.name)
            db.restore_db(
                name,
                str(tmp_path),
                str2bool(copy),
                str2bool(neutralize_database),
            )
            return request.redirect("/web/database/manager")
        except Exception as e:
            error = f"Database restore error: {str(e) or repr(e)}"
            return self._render_template(error=error)
        finally:
            if tmp_path:
                tmp_path.unlink()

    @http.route(
        "/web/database/change_password",
        type="http",
        auth="none",
        methods=["POST"],
        csrf=False,
    )
    def change_password(self, master_pwd: str, master_pwd_new: str) -> str | Response:
        try:
            dispatch_rpc("db", "change_admin_password", [master_pwd, master_pwd_new])
            return request.redirect("/web/database/manager")
        except Exception as e:
            error = f"Master password update error: {str(e) or repr(e)}"
            return self._render_template(error=error)

    @http.route("/web/database/list", type="jsonrpc", auth="none")
    def list(self) -> list[str]:
        """
        Used by Mobile application for listing database
        :return: List of databases
        :rtype: list
        """
        return http.db_list()
