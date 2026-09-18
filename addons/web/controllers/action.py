from typing import Any

from odoo import _
from odoo.exceptions import AccessError, MissingError, UserError
from odoo.http import BadRequest, Controller, request, route

from ..tools import debug_log as dbg
from .utils import clean_action


class MissingActionError(UserError):
    pass


class Action(Controller):
    @route("/web/action/load", type="jsonrpc", auth="user", readonly=True)
    def load(
        self, action_id: int | str, context: dict[str, Any] | None = None
    ) -> dict[str, Any] | bool:
        dbg.lifecycle.debug(
            "[action:%s] load: %s context_keys=%s",
            action_id,
            dbg.req(),
            dbg.keys(context or {}),
        )
        if context:
            request.update_context(**context)
        Actions = request.env["ir.actions.actions"]
        try:
            action_id = int(action_id)
        except TypeError, ValueError:
            try:
                if "." in action_id:
                    dbg.logic.debug("[action:%s] load: resolve by xmlid", action_id)
                    action = request.env.ref(action_id)
                    if not action._name.startswith("ir.actions."):
                        msg = "Not an action"
                        raise ValueError(msg)
                else:
                    dbg.logic.debug("[action:%s] load: resolve by path", action_id)
                    action = Actions._get_action_by_path(action_id)
                    if not action:
                        msg = "Action not found"
                        raise ValueError(msg)
                dbg.pipeline.debug(
                    "[action:%s] load: resolved -> %s", action_id, dbg.rec(action)
                )
                action_id = action.id
            except (
                TypeError,
                ValueError,
                KeyError,
                AttributeError,
                MissingError,
            ) as exc:
                dbg.logic.debug(
                    "[action:%s] load: unresolved (%s)", action_id, type(exc).__name__
                )
                raise MissingActionError(
                    _("The action '%s' does not exist.", action_id)
                ) from exc

        action = Actions.sudo().browse(action_id)._get_concrete()
        if action._name == Actions._name or not action.exists():
            dbg.logic.debug("[action:%s] load: no concrete action row", action_id)
            raise MissingActionError(_("The action '%s' does not exist", action_id))
        action_type = action._name
        if action_type == "ir.actions.report":
            dbg.logic.debug("[action:%s] load: report -> bin_size", action_id)
            request.update_context(bin_size=True)
        try:
            request.env[action_type].browse(action_id)._check_access_to_load()
        except AccessError as exc:
            dbg.logic.debug(
                "[action:%s] load: refused to uid %s", action_id, request.env.uid
            )
            raise MissingActionError(
                _("The action '%s' does not exist", action_id)
            ) from exc
        action = request.env[action_type].sudo().browse([action_id])
        with dbg.timer(
            request.env, "[action:%s] load: %s dict", action_id, action_type
        ):
            result = clean_action(action._get_action_dict(), env=request.env)
        dbg.pipeline.debug(
            "[action:%s] load: %s -> keys=%s", action_id, action_type, dbg.keys(result)
        )
        return result

    @route("/web/action/run", type="jsonrpc", auth="user")
    def run(
        self, action_id: int, context: dict[str, Any] | None = None
    ) -> dict[str, Any] | bool:
        dbg.lifecycle.debug(
            "[action:%s] run: %s context_keys=%s",
            action_id,
            dbg.req(),
            dbg.keys(context or {}),
        )
        if context:
            request.update_context(**context)
        action = request.env["ir.actions.server"].browse([action_id])
        with dbg.timer(request.env, "[action:%s] run", action_id):
            result = action.run()
        dbg.logic.debug(
            "[action:%s] run: result=%s",
            action_id,
            result.get("type") if isinstance(result, dict) else bool(result),
        )
        return clean_action(result, env=action.env) if result else False

    @route(
        "/web/action/load_breadcrumbs",
        type="jsonrpc",
        auth="user",
        readonly=True,
    )
    def load_breadcrumbs(self, actions: list[dict[str, Any]]) -> list[dict[str, Any]]:
        dbg.lifecycle.debug(
            "[breadcrumbs] load: %s actions=%d", dbg.req(), len(actions)
        )
        results = []
        with dbg.timer(request.env, "[breadcrumbs] load %d actions", len(actions)):
            for idx, action in enumerate(actions):
                next_action = actions[idx + 1] if idx + 1 < len(actions) else None
                try:
                    results.append(self._get_breadcrumb(action, idx, next_action))
                except (MissingActionError, MissingError, AccessError) as exc:
                    dbg.logic.debug(
                        "[breadcrumbs] #%d: error %s", idx, type(exc).__name__
                    )
                    results.append({"error": str(exc)})
        dbg.performance.debug(
            "[breadcrumbs] load: %d results, %d errors",
            len(results),
            sum(1 for r in results if "error" in r),
        )
        return results

    def _get_breadcrumb(
        self, action: dict[str, Any], idx: int, next_action: dict[str, Any] | None
    ) -> dict[str, Any]:
        record_id = action.get("resId")
        if action.get("action"):
            dbg.logic.debug(
                "[breadcrumbs] #%d: by action %s res_id=%s",
                idx,
                action.get("action"),
                record_id,
            )
            return self._get_action_breadcrumb(action, record_id, idx, next_action)
        if action.get("model"):
            dbg.logic.debug(
                "[breadcrumbs] #%d: by model %s res_id=%s",
                idx,
                action.get("model"),
                record_id,
            )
            Model = request.env[action.get("model")]
            if not record_id:
                msg = "Actions with a model should also have a resId"
                raise BadRequest(msg)
            if record_id == "new":
                return {"display_name": _("New")}
            return {"display_name": Model.browse(record_id).display_name}
        dbg.logic.debug("[breadcrumbs] #%d: neither action nor model", idx)
        msg = "Actions should have either an action (id or path) or a model"
        raise BadRequest(msg)

    def _get_action_breadcrumb(
        self,
        action: dict[str, Any],
        record_id: Any,
        idx: int,
        next_action: dict[str, Any] | None,
    ) -> dict[str, Any]:
        act = self.load(action.get("action"))
        if not act:
            dbg.logic.debug("[breadcrumbs] #%d: action not loadable", idx)
            return {"error": f"Action {action.get('action')!r} could not be loaded"}

        if act["type"] == "ir.actions.server":
            if not act["path"]:
                dbg.logic.debug("[breadcrumbs] #%d: server action without path", idx)
                return {"error": "A server action must have a path to be restored"}
            dbg.pipeline.debug(
                "[breadcrumbs] #%d: run server action %s", idx, act["id"]
            )
            act = request.env["ir.actions.server"].browse(act["id"]).run()
            if not isinstance(act, dict):
                dbg.logic.debug("[breadcrumbs] #%d: server action not restorable", idx)
                return {"error": "Server action did not return a restorable action"}

        if not act.get("display_name"):
            act["display_name"] = act["name"]

        if (
            act["type"] == "ir.actions.client"
            and next_action is not None
            and action.get("action") == next_action.get("action")
        ):
            dbg.logic.debug("[breadcrumbs] #%d: repeated client action", idx)
            return {"error": "Client actions don't have multi-record views"}

        if record_id:
            if record_id == "new":
                return {"display_name": _("New")}
            if act.get("res_model"):
                dbg.logic.debug(
                    "[breadcrumbs] #%d: record name %s/%s",
                    idx,
                    act["res_model"],
                    record_id,
                )
                return {
                    "display_name": request.env[act["res_model"]]
                    .browse(record_id)
                    .display_name
                }
            return {"display_name": act["display_name"]}

        if act.get("res_model") and act["type"] != "ir.actions.client":
            request.env[act["res_model"]].check_access("read")
            name = (
                act["display_name"]
                if any(
                    view[1] != "form" and view[1] != "search" for view in act["views"]
                )
                else None
            )
            dbg.logic.debug(
                "[breadcrumbs] #%d: multi-record views=%s -> name=%r",
                idx,
                name is not None,
                name,
            )
        else:
            name = act["display_name"]
        return {"display_name": name}
