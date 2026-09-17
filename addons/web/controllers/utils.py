import collections
import logging
from collections.abc import Iterator
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from werkzeug.urls import iri_to_uri

from odoo import http
from odoo.http import abort, request

from ..tools import debug_log as dbg

_logger = logging.getLogger(__name__)


_URL_IGNORED_CHARS = ("\t", "\r", "\n")


def _is_local_url(url: str | None) -> bool:
    if not url or not isinstance(url, str):
        return False
    for char in _URL_IGNORED_CHARS:
        url = url.replace(char, "")
    if not url:
        return False
    if "\\" in url or url.startswith("//"):
        return False
    try:
        parsed = urlsplit(url)
    except ValueError:
        return False
    return not parsed.scheme and not parsed.netloc


def clean_action(action: dict, env: Any) -> dict:
    action_type = action.setdefault("type", "ir.actions.act_window_close")
    if action_type == "ir.actions.act_window" and not action.get("views"):
        dbg.logic.debug(
            "[clean_action:%s] no views, derive from view_mode=%r",
            action.get("id"),
            action.get("view_mode"),
        )
        update_action_views(action)

    action_model = env[action["type"]]
    readable_fields = (
        action_model._get_fields_readable() | action_model._get_keys_client_only()
    )
    action_type_fields = action_model._fields.keys()

    cleaned_action = {
        field: value
        for field, value in action.items()
        if field in readable_fields or field not in action_type_fields
    }

    action_name = action.get("name") or action
    custom_properties = action.keys() - readable_fields - action_type_fields
    dbg.pipeline.debug(
        "[clean_action:%s] %s: %d keys -> %d kept, %d custom",
        action.get("id"),
        action_type,
        len(action),
        len(cleaned_action),
        len(custom_properties),
    )
    if custom_properties:
        _logger.warning(
            "Action %r contains custom properties %s. Passing them "
            "via the `params` or `context` properties is recommended instead",
            action_name,
            ", ".join(map(repr, custom_properties)),
        )

    return cleaned_action


def select_db(redirect: str = "/web/database/selector", db: str | None = None) -> None:
    dbg.lifecycle.debug(
        "[select_db] %s explicit=%r param=%r session=%r",
        dbg.req(),
        db,
        request.params.get("db"),
        request.session.db,
    )
    if db is None:
        db = (raw_db := request.params.get("db")) and raw_db.strip()

    if db and db not in request.app.filter_dbs_served([db]):
        dbg.logic.debug("[select_db] %r not served, dropped", db)
        db = None

    if db and not request.session.db:
        r = request.httprequest
        url_redirect = urlsplit(r.base_url)
        if r.query_string:
            query_string = iri_to_uri(r.query_string.decode())
            url_redirect = url_redirect._replace(query=query_string)
        request.session.db = db
        dbg.pipeline.debug(
            "[select_db] session had no db: bind %r, 302 to re-route through it", db
        )
        abort(request.redirect(urlunsplit(url_redirect), 302))

    if (
        not db
        and request.session.db
        and request.app.filter_dbs_served([request.session.db])
    ):
        db = request.session.db
        dbg.logic.debug("[select_db] from session: %r", db)

    if not db:
        all_dbs = request.app.get_dbs_served()
        dbg.logic.debug("[select_db] no db yet, %d served (forced scan)", len(all_dbs))
        if len(all_dbs) == 1:
            db = all_dbs[0]

    if not db:
        dbg.pipeline.debug("[select_db] unresolved -> 303 %s", redirect)
        abort(request.redirect(redirect, 303))

    if db != request.session.db:
        dbg.pipeline.debug(
            "[select_db] session db %r != %r: new session, redirect 302",
            request.session.db,
            db,
        )
        request.session = http.root.session_store.new()
        request.session.update(http.prepare_default_session(), db=db)
        request.session.context["lang"] = request.get_default_lang()
        abort(request.redirect(request.httprequest.url, 302))
    dbg.logic.debug("[select_db] settled on %r", db)


def update_action_views(action: dict) -> None:
    view_id = action.get("view_id") or False
    if isinstance(view_id, (list, tuple)):
        view_id = view_id[0]

    view_modes = action["view_mode"].split(",")
    dbg.logic.debug("[update_action_views] view_id=%s modes=%s", view_id, view_modes)

    if len(view_modes) > 1:
        if view_id:
            raise ValueError(
                f"Non-db action dictionaries should provide "
                f"either multiple view modes or a single view "
                f"mode and an optional view id.\n\n Got view "
                f"modes {view_modes!r} and view id {view_id!r} for action {action!r}"
            )
        action["views"] = [(False, mode) for mode in view_modes]
        return
    action["views"] = [(view_id, view_modes[0])]


def get_action(env: Any, path_part: str) -> Any:
    Actions = env["ir.actions.actions"]

    if path_part.startswith("action-"):
        someid = path_part.removeprefix("action-")
        if someid.isdigit():
            dbg.logic.debug("[action_path:%s] by id", path_part)
            action = Actions.sudo().browse(int(someid)).exists()
        elif "." in someid:
            dbg.logic.debug("[action_path:%s] by xmlid", path_part)
            action = env.ref(someid, False)
            if not action or not action._name.startswith("ir.actions"):
                dbg.logic.debug("[action_path:%s] xmlid is not an action", path_part)
                action = Actions
        else:
            dbg.logic.debug("[action_path:%s] malformed action- part", path_part)
            action = Actions
    elif path_part.startswith("m-") or "." in path_part:
        model = path_part.removeprefix("m-")
        if model in env and not env[model]._abstract:
            action = (
                env["ir.actions.act_window"]
                .sudo()
                .search([("res_model", "=", model)], limit=1)
            )
            dbg.logic.debug(
                "[action_path:%s] by model %s: %s",
                path_part,
                model,
                "first act_window" if action else "synthetic formview",
            )
            if not action:
                action = env["ir.actions.act_window"].new(
                    env[model].get_formview_action()
                )
        else:
            dbg.logic.debug("[action_path:%s] unknown or abstract model", path_part)
            action = Actions
    else:
        dbg.logic.debug("[action_path:%s] by path", path_part)
        return Actions._get_action_by_path(path_part)

    if action and action._name == "ir.actions.actions":
        action = action._get_concrete()

    dbg.pipeline.debug("[action_path:%s] -> %s", path_part, dbg.rec(action))
    return action


def get_action_triples(
    env: Any, path: str, *, start_pos: int = 0
) -> Iterator[tuple[int | None, Any, int | None]]:
    parts = collections.deque(path.strip("/").split("/"))
    active_id = None
    record_id = None

    while parts:
        action_name = parts.popleft()
        action = get_action(env, action_name)
        if not action:
            dbg.logic.debug(
                "[action_path:%s] no action at word %d of %r",
                action_name,
                path.count("/") - len(parts) + start_pos,
                path,
            )
            raise ValueError(
                f"expected action at word {path.count('/') - len(parts) + start_pos} but found “{action_name}”"
            )

        record_id = None
        if parts:
            if parts[0] == "new":
                parts.popleft()
                record_id = None
            elif parts[0].isdigit():
                record_id = int(parts.popleft())

        dbg.pipeline.debug(
            "[action_path:%s] triple active_id=%s record_id=%s rest=%d",
            action_name,
            active_id,
            record_id,
            len(parts),
        )
        yield (active_id, action, record_id)

        if len(parts) > 1 and parts[0].isdigit():
            active_id = int(parts.popleft())
        elif record_id:
            active_id = record_id


def _get_login_redirect_url(uid: int, redirect: str | None = None) -> str:
    if request.session.uid:
        if redirect and _is_local_url(redirect):
            dbg.logic.debug("[login_redirect] uid=%s local redirect %r", uid, redirect)
            return redirect
        internal = is_user_internal(request.session.uid)
        dbg.logic.debug(
            "[login_redirect] uid=%s internal=%s redirect=%r dropped",
            uid,
            internal,
            redirect,
        )
        return "/odoo" if internal else "/web/login_successful"

    url = request.env(user=uid)["res.users"].browse(uid)._get_mfa_url()
    dbg.logic.debug(
        "[login_redirect] uid=%s session not authenticated: mfa url, redirect=%r",
        uid,
        redirect,
    )
    if not redirect or not _is_local_url(redirect):
        return url

    parsed = urlsplit(url)
    qs = dict(parse_qsl(parsed.query))
    qs["redirect"] = redirect
    return urlunsplit(parsed._replace(query=urlencode(qs)))


def is_user_internal(uid: int) -> bool:
    return request.env["res.users"].browse(uid)._is_internal()
