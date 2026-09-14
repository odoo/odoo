import ast
import logging
from datetime import date
from http import HTTPStatus
from urllib.parse import urlencode

import psycopg.errors
from lxml import etree

from odoo import http
from odoo.exceptions import AccessError
from odoo.fields import Domain
from odoo.http import BadRequest, NotFound, request
from odoo.tools.safe_eval import safe_eval

from ..tools import debug_log as dbg
from .json_helpers import (
    get_domain_date,
    get_domain_default_filter,
    get_groupby,
    get_view_id_and_type,
)
from .utils import get_action_triples

_logger = logging.getLogger(__name__)


class WebJsonController(http.Controller):
    @http.route("/json/<path:subpath>", auth="user", type="http", readonly=True)
    def web_json(self, subpath, **kwargs):
        dbg.lifecycle.debug("[json:%s] unversioned: %s -> /json/1", subpath, dbg.req())
        self._check_json_route_active()
        return request.redirect(
            f"/json/1/{subpath}?{urlencode(kwargs)}",
            HTTPStatus.TEMPORARY_REDIRECT,
        )

    @http.route("/json/1/<path:subpath>", auth="bearer", type="http", readonly=True)
    def web_json_1(self, subpath, **kwargs):
        dbg.lifecycle.debug(
            "[json:%s] request: %s params=%s", subpath, dbg.req(), dbg.keys(kwargs)
        )
        self._check_json_route_active()
        if not request.env.user.has_group("base.group_allow_export"):
            dbg.logic.debug("[json:%s] no export group, refused", subpath)
            raise AccessError(
                request.env._("You need export permissions to use the /json route")
            )

        param_list = set(kwargs)

        def resolve_canonical_redirect():
            if param_list == set(kwargs):
                return None
            dbg.pipeline.debug(
                "[json:%s] params grew %s -> %s: canonical 307",
                subpath,
                sorted(param_list),
                dbg.keys(kwargs),
            )
            encoded_kwargs = urlencode(kwargs, safe="()[], '\"")
            return request.redirect(
                f"/json/1/{subpath}?{encoded_kwargs}",
                HTTPStatus.TEMPORARY_REDIRECT,
            )

        env = request.env
        with dbg.timer(env, "[json:%s] resolve action", subpath):
            action, context, eval_context, record_id = self._get_action(subpath)
        model = env[action.res_model].with_context(context)

        view_type = kwargs.get("view_type")
        if not view_type and record_id:
            view_type = "form"
        view_id, view_type = get_view_id_and_type(action, view_type)
        with dbg.timer(env, "[json:%s] get_view %s/%s", subpath, view_id, view_type):
            view = model.get_view(view_id, view_type)
        spec = model._get_fields_spec(view)
        dbg.pipeline.debug(
            "[json:%s] action=%s model=%s view=%s/%s record_id=%s spec=%d fields",
            subpath,
            action.id,
            model._name,
            view_id,
            view_type,
            record_id,
            len(spec),
        )

        if view_type == "form" or record_id:
            if redirect := resolve_canonical_redirect():
                return redirect
            return self._get_json_record(model, spec, record_id)

        domains = self._get_json_domains(model, action, context, eval_context, kwargs)
        limit, offset = self._get_json_window(action, kwargs)

        view_tree = etree.fromstring(view["arch"])

        if env["ir.ui.view"]._view_type_has_date_range(view_type):
            dbg.logic.debug("[json:%s] %s view has date range", subpath, view_type)
            domains.append(self._get_domain_json_date(view_tree, kwargs))

        if view_type == "activity":
            dbg.logic.debug("[json:%s] activity view: extend domain + spec", subpath)
            domains.append([("activity_ids", "!=", False)])
            self._update_json_activity_spec(model, spec)

        groupby, fields = get_groupby(
            view_tree, kwargs.get("groupby"), kwargs.get("fields")
        )
        aggregates = self._get_json_aggregates(model, fields)

        if groupby is not None and not kwargs.get("groupby"):
            kwargs["groupby"] = ",".join(groupby)
            if "fields" not in kwargs and fields:
                kwargs["fields"] = ",".join(fields)
        if groupby is None and fields:
            for field in fields:
                spec.setdefault(field, {})

        if redirect := resolve_canonical_redirect():
            return redirect
        dbg.pipeline.debug(
            "[json:%s] listing: %d domains groupby=%s aggregates=%s limit=%s offset=%s",
            subpath,
            len(domains),
            groupby,
            aggregates,
            limit,
            offset,
        )
        return self._get_json_listing(
            model, Domain.AND(domains), spec, groupby, aggregates, limit, offset
        )

    def _get_json_record(self, model, spec, record_id):
        if not record_id:
            dbg.logic.debug("[json] form view without record id, refused")
            raise BadRequest(request.env._("Missing record id"))
        with dbg.timer(model.env, "[json] web_read %s/%s", model._name, record_id):
            res = model.browse(int(record_id)).web_read(spec)
        if not res:
            dbg.logic.debug(
                "[json] %s/%s: web_read empty -> 404", model._name, record_id
            )
            raise NotFound
        return request.prepare_json_response(res[0])

    def _get_json_listing(
        self, model, domain, spec, groupby, aggregates, limit, offset
    ):
        if groupby:
            with dbg.timer(model.env, "[json] web_read_group %s", model._name):
                res = model.web_read_group(
                    domain,
                    aggregates=aggregates,
                    groupby=groupby,
                    limit=limit,
                    offset=offset,
                )
            for value in res["groups"]:
                del value["__extra_domain"]
            dbg.performance.debug(
                "[json] %s: %d groups of %s", model._name, len(res["groups"]), groupby
            )
        else:
            with dbg.timer(model.env, "[json] web_search_read %s", model._name):
                res = model.web_search_read(
                    domain,
                    spec,
                    limit=limit,
                    offset=offset,
                )
            dbg.performance.debug(
                "[json] %s: %d of %s records",
                model._name,
                len(res.get("records", ())),
                res.get("length"),
            )
        res.pop("__version", None)
        return request.prepare_json_response(res)

    def _get_json_domains(self, model, action, context, eval_context, kwargs):
        domains = [safe_eval(action.domain or "[]", eval_context)]
        if "domain" in kwargs:
            try:
                user_domain = ast.literal_eval(kwargs.get("domain") or "[]")
            except (ValueError, SyntaxError) as exc:
                dbg.logic.debug(
                    "[json] user domain unparsable (%s)", type(exc).__name__
                )
                raise BadRequest(f"Invalid domain: {exc}") from exc
            dbg.logic.debug("[json] user domain: %s terms", dbg.count(user_domain))
            domains.append(user_domain)
        else:
            default_domain = get_domain_default_filter(
                model, action, context, eval_context
            )
            if default_domain and not Domain(default_domain).is_true():
                dbg.logic.debug("[json] default filter domain pinned into params")
                kwargs["domain"] = repr(list(default_domain))
            domains.append(default_domain)
        return domains

    def _get_json_window(self, action, kwargs):
        try:
            limit = int(kwargs.get("limit", 0)) or action.limit
            offset = int(kwargs.get("offset", 0))
        except ValueError as exc:
            dbg.logic.debug("[json] window unparsable: %s", exc.args[0])
            raise BadRequest(exc.args[0]) from exc
        if "offset" not in kwargs:
            kwargs["offset"] = offset
        if "limit" not in kwargs:
            kwargs["limit"] = limit
        return limit, offset

    def _get_domain_json_date(self, view_tree, kwargs):
        try:
            start_date = date.fromisoformat(kwargs["start_date"])
            end_date = date.fromisoformat(kwargs["end_date"])
        except ValueError as exc:
            dbg.logic.debug("[json] date range unparsable: %s", exc.args[0])
            raise BadRequest(exc.args[0]) from exc
        except KeyError:
            start_date = end_date = None
        try:
            date_domain = get_domain_date(start_date, end_date, view_tree)
        except ValueError as exc:
            dbg.logic.debug("[json] date range rejected: %s", exc.args[0])
            raise BadRequest(exc.args[0]) from exc
        if "start_date" not in kwargs or "end_date" not in kwargs:
            kwargs.update(
                {
                    "start_date": date_domain[0][2].isoformat(),
                    "end_date": date_domain[1][2].isoformat(),
                }
            )
        return date_domain

    def _update_json_activity_spec(self, model, spec):
        added = 0  # debuglog
        for field_name, field in model._fields.items():
            if (
                field_name.startswith("activity_")
                and field_name not in spec
                and model._has_field_access(field, "read")
            ):
                spec[field_name] = {}
                added += 1
        dbg.logic.debug("[json] activity spec: %d activity_* fields added", added)

    def _get_json_aggregates(self, model, fields):
        if not fields:
            return ["__count"]
        env = request.env
        invalid = [f for f in fields if ":" not in f and f not in model._fields]
        if invalid:
            dbg.logic.debug("[json] %s: unknown fields %s", model._name, invalid)
            raise BadRequest(
                env._(
                    "Unknown fields for %(model)s: %(fields)s",
                    model=model._name,
                    fields=", ".join(invalid),
                )
            )
        not_aggregatable = [
            f for f in fields if ":" not in f and model._fields[f].aggregator is None
        ]
        if not_aggregatable:
            dbg.logic.debug(
                "[json] %s: not aggregatable %s", model._name, not_aggregatable
            )
            raise BadRequest(
                env._(
                    "Fields not aggregatable for %(model)s: %(fields)s",
                    model=model._name,
                    fields=", ".join(not_aggregatable),
                )
            )
        return [
            f"{fname}:{model._fields[fname].aggregator}" if ":" not in fname else fname
            for fname in fields
        ]

    def _check_json_route_active(self):
        sudo_env = request.env(su=True)
        if not (
            sudo_env.ref("base.module_base").demo
            or sudo_env["ir.config_parameter"].get_param("web.json.enabled")
        ):
            dbg.logic.debug("[json] route inactive (no demo, web.json.enabled unset)")
            raise NotFound

    def _get_action(self, subpath):
        def get_action_triples_():
            try:
                yield from get_action_triples(request.env, subpath, start_pos=1)
            except ValueError as exc:
                raise BadRequest(exc.args[0]) from exc

        context = dict(request.env.context)
        active_id, action, record_id = list(get_action_triples_())[-1]
        action = action.sudo()
        if action.usage == "ir_actions_server" and action.path:
            dbg.pipeline.debug(
                "[json:%s] server action %s: run on a read-only cursor",
                subpath,
                action.id,
            )
            try:
                with action.pool.cursor(readonly=True) as ro_cr:
                    if not ro_cr.readonly:
                        dbg.logic.debug(
                            "[json:%s] pool gave a rw cursor, forcing read_only",
                            subpath,
                        )
                        ro_cr.connection.read_only = True
                    if not ro_cr.readonly:
                        msg = "Failed to obtain a read-only cursor for server action evaluation"
                        raise RuntimeError(msg)
                    action_data = action.with_env(action.env(cr=ro_cr, su=False)).run()
            except psycopg.errors.ReadOnlySqlTransaction as e:
                dbg.logic.debug("[json:%s] server action tried to write", subpath)
                raise AccessError(action.env._("Unsupported server action")) from e
            except ValueError as e:
                if "ReadOnlySqlTransaction" not in e.args[0]:
                    raise
                dbg.logic.debug(
                    "[json:%s] server action tried to write (wrapped)", subpath
                )
                raise AccessError(action.env._("Unsupported server action")) from e
            action = action.env[action_data["type"]]
            action = action.new(
                action_data, origin=action.browse(action_data.pop("id"))
            )
            dbg.pipeline.debug(
                "[json:%s] server action -> %s %s",
                subpath,
                action._name,
                action._origin.id,
            )
        if action._name != "ir.actions.act_window":
            dbg.logic.debug(
                "[json:%s] %s unsupported server-side", subpath, action._name
            )
            e = f"{action._name} are not supported server-side"
            raise BadRequest(e)
        eval_context = dict(
            action._prepare_eval_context(action),
            active_id=active_id,
            context=context,
            allowed_company_ids=request.env.user.company_ids.ids,
        )
        context.update(safe_eval(action.context, eval_context))
        return action, context, eval_context, record_id
