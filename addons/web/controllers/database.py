import datetime
import functools
import ipaddress
import logging
import os
import pathlib
import re
import tempfile

from lxml import html
from markupsafe import Markup
from werkzeug.datastructures import (
    FileStorage,
)

import odoo
import odoo.modules.registry
from odoo import http
from odoo.exceptions import UserError
from odoo.http import (
    Response,
    dispatch_rpc,
    prepare_content_disposition_header,
    request,
)
from odoo.service import db
from odoo.service.db import DBNAME_PATTERN
from odoo.tools.misc import file_open, str2bool
from odoo.tools.translate import _

from ..tools import debug_log as dbg
from odoo.addons.base.models.ir_qweb import render as qweb_render

_logger = logging.getLogger(__name__)

REJECTED_INPUT_ERRORS = (ValueError, odoo.exceptions.AccessDenied)


def _renders_failure(operation: str):
    def decorate(handler):
        @functools.wraps(handler)
        def wrapper(self, *args, **kwargs):
            try:
                return handler(self, *args, **kwargs)
            except Exception as exc:
                dbg.logic.debug(
                    "[dbmanager] %s failed (%s)", operation, type(exc).__name__
                )
                if isinstance(exc, REJECTED_INPUT_ERRORS):
                    _logger.warning("%s: %s", operation, exc)
                else:
                    _logger.error(operation, exc_info=exc)
                return self._render_template(
                    error=f"{operation}: {str(exc) or repr(exc)}"
                )

        return wrapper

    return decorate


def _check_db_name(name: str) -> None:
    if not re.match(DBNAME_PATTERN, name):
        dbg.logic.debug("[db:%s] name rejected by pattern", name)
        raise UserError(
            _(
                "Houston, we have a database naming issue! Make sure you only use letters, numbers, underscores, hyphens, or dots in the database name, and you'll be golden."
            )
        )


def _is_loopback(addr: str | None) -> bool:
    try:
        ip = ipaddress.ip_address(addr)
    except ValueError, TypeError:
        return False
    mapped = getattr(ip, "ipv4_mapped", None)
    return (mapped or ip).is_loopback


DATABASE_MANAGER_TEMPLATES = {
    "database_manager": "web/static/src/public/database_manager.qweb.html",
    "master_input": "web/static/src/public/database_manager.master_input.qweb.html",
    "create_form": "web/static/src/public/database_manager.create_form.qweb.html",
}


def render_database_manager(values: dict) -> Markup:
    templates = {}
    with dbg.timer(
        None, "[dbmanager] read %d templates", len(DATABASE_MANAGER_TEMPLATES)
    ):
        for name, path in DATABASE_MANAGER_TEMPLATES.items():
            with file_open(path, "r") as fd:
                templates[name] = fd.read()

    def load(template_name):
        fromstring = (
            html.document_fromstring
            if template_name == "database_manager"
            else html.fragment_fromstring
        )
        return (fromstring(templates[template_name]), template_name)

    with dbg.timer(None, "[dbmanager] qweb render"):
        return Markup("<!DOCTYPE html>\n") + qweb_render(
            "database_manager", values, load
        )


class Database(http.Controller):
    def _handle_insecure_password(self, master_pwd: str) -> None:
        if not (odoo.tools.config.is_valid_admin_password("admin") and master_pwd):
            return
        remote_addr = request.httprequest.remote_addr
        dbg.logic.debug(
            "[dbmanager] default master password in place, request from %s loopback=%s",
            remote_addr,
            _is_loopback(remote_addr),
        )
        if not _is_loopback(remote_addr):
            _logger.warning(
                "Refusing to auto-promote the default master password for a "
                "non-loopback request from %s. Set 'admin_passwd' in the "
                "config, or change the master password from localhost.",
                remote_addr,
            )
            return
        _logger.warning(
            "Auto-promoting the default master password ('admin') to the value "
            "submitted from loopback (%s).",
            remote_addr,
        )
        dispatch_rpc("db", "change_admin_password", ["admin", master_pwd])

    def _render_template(self, **d) -> str:
        d.setdefault("manage", True)
        d["insecure"] = odoo.tools.config.is_valid_admin_password("admin")
        d["list_db"] = odoo.tools.config["list_db"]
        with dbg.timer(None, "[dbmanager] list langs + countries"):
            d["langs"] = odoo.service.db.exp_list_lang()
            d["countries"] = odoo.service.db.exp_list_countries()
        d["pattern"] = DBNAME_PATTERN
        try:
            with dbg.timer(None, "[dbmanager] list databases + incompatible"):
                d["databases"] = request.app.get_dbs_served()
                d["incompatible_databases"] = odoo.service.db.list_db_incompatible(
                    d["databases"]
                )
            dbg.logic.debug(
                "[dbmanager] render manage=%s error=%s: %d databases, %d incompatible",
                d["manage"],
                "error" in d,
                len(d["databases"]),
                len(d["incompatible_databases"]),
            )
        except odoo.exceptions.AccessDenied:
            d["databases"] = [request.db] if request.db else []
            dbg.logic.debug(
                "[dbmanager] render: db list denied, showing %s", d["databases"]
            )

        return render_database_manager(d)

    @http.route("/web/database/selector", type="http", auth="none")
    def selector(self, **kw) -> str:
        dbg.lifecycle.debug("[dbmanager] selector: %s", dbg.req())
        if request.db:
            dbg.logic.debug("[dbmanager] selector: detach %s", request.db)
            request.detach_database()
        return self._render_template(manage=False)

    @http.route("/web/database/manager", type="http", auth="none")
    def manager(self, **kw) -> str:
        dbg.lifecycle.debug("[dbmanager] manager: %s", dbg.req())
        if request.db:
            dbg.logic.debug("[dbmanager] manager: detach %s", request.db)
            request.detach_database()
        return self._render_template()

    @http.route(
        "/web/database/create",
        type="http",
        auth="none",
        methods=["POST"],
        csrf=False,
    )
    @_renders_failure("Database creation error")
    def create(  # noqa: E8528 - the database manager runs without a database and checks the master password
        self, master_pwd: str, name: str, lang: str, password: str, **post
    ) -> str | Response:
        dbg.lifecycle.debug(
            "[db:%s] create: %s lang=%s demo=%s country=%s login=%r",
            name,
            dbg.req(),
            lang,
            bool(post.get("demo")),
            post.get("country_code") or None,
            post.get("login"),
        )
        self._handle_insecure_password(master_pwd)
        _check_db_name(name)
        country_code = post.get("country_code") or False
        with dbg.timer(None, "[db:%s] create_database rpc", name):
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
        dbg.pipeline.debug("[db:%s] create: created -> authenticate admin", name)
        with odoo.modules.registry.Registry(name).cursor() as cr:
            env = odoo.api.Environment(cr, None, {})
            request.session.authenticate(env, credential)
            request._save_session(env)
            request.session.db = name
        dbg.pipeline.debug(
            "[db:%s] create: session uid=%s -> /odoo", name, request.session.uid
        )
        return request.redirect("/odoo")

    @http.route(
        "/web/database/duplicate",
        type="http",
        auth="none",
        methods=["POST"],
        csrf=False,
    )
    @_renders_failure("Database duplication error")
    def duplicate(  # noqa: E8528 - the database manager runs without a database and checks the master password
        self,
        master_pwd: str,
        name: str,
        new_name: str,
        neutralize_database: bool | str = False,
    ) -> str | Response:
        dbg.lifecycle.debug(
            "[db:%s] duplicate: %s -> %s neutralize=%r",
            name,
            dbg.req(),
            new_name,
            neutralize_database,
        )
        self._handle_insecure_password(master_pwd)
        _check_db_name(new_name)
        with dbg.timer(None, "[db:%s] duplicate_database rpc -> %s", name, new_name):
            dispatch_rpc(
                "db",
                "duplicate_database",
                [master_pwd, name, new_name, str2bool(neutralize_database)],
            )
        if request.db == name:
            dbg.logic.debug("[db:%s] duplicate: source is request db, detach", name)
            request.detach_database()
        return request.redirect("/web/database/manager")

    @http.route(
        "/web/database/drop",
        type="http",
        auth="none",
        methods=["POST"],
        csrf=False,
    )
    @_renders_failure("Database deletion error")
    def drop(self, master_pwd: str, name: str) -> str | Response:  # noqa: E8528 - the database manager runs without a database and checks the master password
        dbg.lifecycle.debug("[db:%s] drop: %s", name, dbg.req())
        self._handle_insecure_password(master_pwd)
        with dbg.timer(None, "[db:%s] drop rpc", name):
            dropped = dispatch_rpc("db", "drop", [master_pwd, name])
        if not dropped:
            dbg.logic.debug("[db:%s] drop: not found", name)
            raise RuntimeError(f"Database {name!r} was not found")
        if request.session.db == name:
            dbg.logic.debug("[db:%s] drop: was session db, detach + logout", name)
            request.detach_database()
            request.session.logout()
        return request.redirect("/web/database/manager")

    @http.route(
        "/web/database/backup",
        type="http",
        auth="none",
        methods=["POST"],
        csrf=False,
    )
    @_renders_failure("Database backup error")
    def backup(  # noqa: E8528 - the database manager runs without a database and checks the master password
        self,
        master_pwd: str,
        name: str,
        backup_format: str = "zip",
        filestore: bool | str = True,
    ) -> str | Response:
        filestore = str2bool(filestore)
        dbg.lifecycle.debug(
            "[db:%s] backup: %s format=%s filestore=%s",
            name,
            dbg.req(),
            backup_format,
            filestore,
        )
        self._handle_insecure_password(master_pwd)
        if backup_format not in odoo.service.db.BACKUP_FORMATS:
            expected = ", ".join(
                repr(f) for f in sorted(odoo.service.db.BACKUP_FORMATS)
            )
            raise ValueError(
                f"Invalid backup format {backup_format!r}; expected {expected}"
            )
        odoo.service.db.check_super(master_pwd)
        if name not in request.app.get_dbs_served():
            dbg.logic.debug("[db:%s] backup: not served", name)
            raise ValueError(f"Database {name!r} is not known")
        ts = datetime.datetime.now(datetime.UTC).strftime("%Y-%m-%d_%H-%M-%S")
        filename = f"{name}_{ts}.{backup_format}"
        with dbg.timer(None, "[db:%s] dump_db %s", name, backup_format):
            dump_stream = odoo.service.db.dump_db(name, None, backup_format, filestore)
        dump_size = dump_stream.seek(0, os.SEEK_END)
        dump_stream.seek(0)
        dbg.performance.debug(
            "[db:%s] backup: %s, %d bytes (buffered before streaming)",
            name,
            filename,
            dump_size,
        )
        headers = [
            ("Content-Type", "application/octet-stream; charset=binary"),
            ("Content-Disposition", prepare_content_disposition_header(filename)),
            ("Content-Length", str(dump_size)),
        ]
        return Response(dump_stream, headers=headers, direct_passthrough=True)

    @http.route(
        "/web/database/restore",
        type="http",
        auth="none",
        methods=["POST"],
        csrf=False,
        max_content_length=None,
    )
    @_renders_failure("Database restore error")
    def restore(  # noqa: E8528 - the database manager runs without a database and checks the master password
        self,
        master_pwd: str,
        backup_file: FileStorage,
        name: str,
        copy: bool | str = False,
        neutralize_database: bool | str = False,
    ) -> str | Response:
        dbg.lifecycle.debug(
            "[db:%s] restore: %s copy=%r neutralize=%r upload=%r",
            name,
            dbg.req(),
            copy,
            neutralize_database,
            getattr(backup_file, "filename", None),
        )
        self._handle_insecure_password(master_pwd)
        db.check_super(master_pwd)
        _check_db_name(name)
        with (
            dbg.timer(None, "[db:%s] restore: spool upload", name),
            tempfile.NamedTemporaryFile(delete=False) as tmp,
        ):
            tmp_path = pathlib.Path(tmp.name)
            backup_file.save(tmp)
        try:
            dbg.pipeline.debug(
                "[db:%s] restore: spooled %d bytes -> restore_db",
                name,
                tmp_path.stat().st_size,
            )
            with dbg.timer(None, "[db:%s] restore_db", name):
                db.restore_db(
                    name,
                    str(tmp_path),
                    str2bool(copy),
                    str2bool(neutralize_database),
                )
        finally:
            tmp_path.unlink(missing_ok=True)
        return request.redirect("/web/database/manager")

    @http.route(
        "/web/database/change_password",
        type="http",
        auth="none",
        methods=["POST"],
        csrf=False,
    )
    @_renders_failure("Master password update error")
    def change_password(self, master_pwd: str, master_pwd_new: str) -> str | Response:  # noqa: E8528 - the database manager runs without a database and checks the master password
        dbg.lifecycle.debug(
            "[dbmanager] change_password: %s has_new=%s",
            dbg.req(),
            bool(master_pwd_new),
        )
        if odoo.tools.config.is_valid_admin_password("admin"):
            remote_addr = request.httprequest.remote_addr
            if not _is_loopback(remote_addr):
                dbg.logic.debug(
                    "[dbmanager] change_password: default pwd, non-loopback, refused"
                )
                _logger.warning(
                    "Refusing a non-loopback master-password change from %s "
                    "while the default password is still in place.",
                    remote_addr,
                )
                raise UserError(
                    _(
                        "For security, the master password can only be changed "
                        "from localhost while it is still the default. Set "
                        "'admin_passwd' in the configuration file instead."
                    )
                )
        dispatch_rpc("db", "change_admin_password", [master_pwd, master_pwd_new])
        dbg.pipeline.debug("[dbmanager] change_password: changed")
        return request.redirect("/web/database/manager")

    @http.route("/web/database/list", type="jsonrpc", auth="none")
    def list(self) -> list[str]:
        dbs = request.app.get_dbs_served()
        dbg.lifecycle.debug("[dbmanager] list: %s -> %d", dbg.req(), len(dbs))
        return dbs
