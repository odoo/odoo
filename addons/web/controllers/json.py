"""HTTP controller for the /json API route.

View/domain resolution helpers live in ``json_helpers.py``.
"""

import ast
import logging
from datetime import date
from http import HTTPStatus
from urllib.parse import urlencode

import psycopg.errors
from lxml import etree
from werkzeug.exceptions import BadRequest, NotFound

from odoo import http
from odoo.exceptions import AccessError
from odoo.fields import Domain
from odoo.http import request
from odoo.tools.safe_eval import safe_eval

from .json_helpers import (
    get_date_domain,
    get_default_domain,
    get_groupby,
    get_view_id_and_type,
)
from .utils import get_action_triples

_logger = logging.getLogger(__name__)


class WebJsonController(http.Controller):
    # for /json, the route should work in a browser, therefore type=http
    @http.route("/json/<path:subpath>", auth="user", type="http", readonly=True)
    def web_json(self, subpath, **kwargs):
        self._check_json_route_active()
        return request.redirect(
            f"/json/1/{subpath}?{urlencode(kwargs)}",
            HTTPStatus.TEMPORARY_REDIRECT,
        )

    @http.route("/json/1/<path:subpath>", auth="bearer", type="http", readonly=True)
    def web_json_1(self, subpath, **kwargs):
        """Simple JSON representation of the views.

        Get the JSON representation of the action/view as it would be shown
        in the web client for the same /odoo `subpath`.

        Behaviour:
        - When, the action resolves to a pair (Action, id), `form` view_type.
          Otherwise when it resolves to (Action, None), use the given view_type
          or the preferred one.
        - View form uses `web_read`.
        - If a groupby is given, use a read group.
          Views pivot, graph redirect to a canonical URL with a groupby.
        - Otherwise use a search read.
        - If any parameter is missing, redirect to the canonical URL (one where
          all parameters are set).

        :param subpath: Path to the (window) action to execute
        :param view_type: View type from which we generate the parameters
        :param domain: The domain for searches
        :param offset: Offset for search
        :param limit: Limit for search
        :param groupby: Comma-separated string; when set, executes a `web_read_group`
                        and groups by the given fields
        :param fields: Comma-separates aggregates for the "group by" query
        :param start_date: When applicable, minimum date (inclusive bound)
        :param end_date: When applicable, maximum date (exclusive bound)
        """
        self._check_json_route_active()
        if not request.env.user.has_group("base.group_allow_export"):
            raise AccessError(
                request.env._("You need export permissions to use the /json route")
            )

        # redirect when the computed kwargs and the kwargs from the URL are different
        param_list = set(kwargs)

        def check_redirect():
            # when parameters were added, redirect
            if param_list == set(kwargs):
                return None
            # for domains, make chars as safe
            encoded_kwargs = urlencode(kwargs, safe="()[], '\"")
            return request.redirect(
                f"/json/1/{subpath}?{encoded_kwargs}",
                HTTPStatus.TEMPORARY_REDIRECT,
            )

        # Get the action
        env = request.env
        action, context, eval_context, record_id = self._get_action(subpath)
        model = env[action.res_model].with_context(context)

        # Get the view
        view_type = kwargs.get("view_type")
        if not view_type and record_id:
            view_type = "form"
        view_id, view_type = get_view_id_and_type(action, view_type)
        view = model.get_view(view_id, view_type)
        spec = model._get_fields_spec(view)

        # Simple case: form view with record
        if view_type == "form" or record_id:
            if redirect := check_redirect():
                return redirect
            if not record_id:
                raise BadRequest(env._("Missing record id"))
            res = model.browse(int(record_id)).web_read(spec)[0]
            return request.make_json_response(res)

        # Find domain and limits
        domains = [safe_eval(action.domain or "[]", eval_context)]
        if "domain" in kwargs:
            # for the user-given domain, use only literal-eval instead of safe_eval
            user_domain = ast.literal_eval(kwargs.get("domain") or "[]")
            domains.append(user_domain)
        else:
            default_domain = get_default_domain(model, action, context, eval_context)
            if default_domain and not Domain(default_domain).is_true():
                kwargs["domain"] = repr(list(default_domain))
            domains.append(default_domain)
        try:
            limit = int(kwargs.get("limit", 0)) or action.limit
            offset = int(kwargs.get("offset", 0))
        except ValueError as exc:
            raise BadRequest(exc.args[0]) from exc
        if "offset" not in kwargs:
            kwargs["offset"] = offset
        if "limit" not in kwargs:
            kwargs["limit"] = limit

        # Additional info from the view
        view_tree = etree.fromstring(view["arch"])

        # Add date domain for some view types
        if view_type in ("calendar", "gantt", "cohort"):
            try:
                start_date = date.fromisoformat(kwargs["start_date"])
                end_date = date.fromisoformat(kwargs["end_date"])
            except ValueError as exc:
                raise BadRequest(exc.args[0]) from exc
            except KeyError:
                start_date = end_date = None
            date_domain = get_date_domain(start_date, end_date, view_tree)
            domains.append(date_domain)
            if "start_date" not in kwargs or "end_date" not in kwargs:
                kwargs.update(
                    {
                        "start_date": date_domain[0][2].isoformat(),
                        "end_date": date_domain[1][2].isoformat(),
                    }
                )

        # Add explicitly activity fields for an activity view
        if view_type == "activity":
            domains.append([("activity_ids", "!=", False)])
            # add activity fields
            for field_name, field in model._fields.items():
                if (
                    field_name.startswith("activity_")
                    and field_name not in spec
                    and model._has_field_access(field, "read")
                ):
                    spec[field_name] = {}

        # Group by
        groupby, fields = get_groupby(
            view_tree, kwargs.get("groupby"), kwargs.get("fields")
        )
        if fields:
            aggregates = [
                (
                    f"{fname}:{model._fields[fname].aggregator}"
                    if ":" not in fname
                    else fname
                )
                for fname in fields
            ]
        else:
            aggregates = ["__count"]

        if groupby is not None and not kwargs.get("groupby"):
            # add arguments to kwargs
            kwargs["groupby"] = ",".join(groupby)
            if "fields" not in kwargs and fields:
                kwargs["fields"] = ",".join(fields)
        if groupby is None and fields:
            # add fields to the spec
            for field in fields:
                spec.setdefault(field, {})

        # Last checks before the query
        if redirect := check_redirect():
            return redirect
        domain = Domain.AND(domains)
        # Reading a group or a list
        if groupby:
            res = model.web_read_group(
                domain,
                aggregates=aggregates,
                groupby=groupby,
                limit=limit,
            )
            # pop '__domain' key
            for value in res["groups"]:
                del value["__extra_domain"]
        else:
            res = model.web_search_read(
                domain,
                spec,
                limit=limit,
                offset=offset,
            )
        return request.make_json_response(res)

    def _check_json_route_active(self):
        """Verify the /json route is enabled (demo mode or config param)."""
        # experimental route, only enabled in demo mode or when explicitly set
        # Use sudo() since user may not have access to ir.module.module
        sudo_env = request.env(su=True)
        if not (
            sudo_env.ref("base.module_base").demo
            or sudo_env["ir.config_parameter"].get_param("web.json.enabled")
        ):
            raise NotFound

    def _get_action(self, subpath):
        """Resolve the action from the URL *subpath*."""

        def get_action_triples_():
            try:
                yield from get_action_triples(request.env, subpath, start_pos=1)
            except ValueError as exc:
                raise BadRequest(exc.args[0]) from exc

        context = dict(request.env.context)
        active_id, action, record_id = list(get_action_triples_())[-1]
        action = action.sudo()
        if action.usage == "ir_actions_server" and action.path:
            # force read-only evaluation of action_data
            try:
                with action.pool.cursor(readonly=True) as ro_cr:
                    if not ro_cr.readonly:
                        ro_cr.connection.read_only = True
                    if not ro_cr.readonly:
                        msg = "Failed to obtain a read-only cursor for server action evaluation"
                        raise RuntimeError(msg)
                    action_data = action.with_env(action.env(cr=ro_cr, su=False)).run()
            except psycopg.errors.ReadOnlySqlTransaction as e:
                # never retry on RO connection, just leave
                raise AccessError(action.env._("Unsupported server action")) from e
            except ValueError as e:
                # safe_eval wraps the error into a ValueError (as str)
                if "ReadOnlySqlTransaction" not in e.args[0]:
                    raise
                raise AccessError(action.env._("Unsupported server action")) from e
            # transform data into a new record
            action = action.env[action_data["type"]]
            action = action.new(
                action_data, origin=action.browse(action_data.pop("id"))
            )
        if action._name != "ir.actions.act_window":
            e = f"{action._name} are not supported server-side"
            raise BadRequest(e)
        eval_context = dict(
            action._get_eval_context(action),
            active_id=active_id,
            context=context,
            allowed_company_ids=request.env.user.company_ids.ids,
        )
        # update the context and return
        context.update(safe_eval(action.context, eval_context))
        return action, context, eval_context, record_id
