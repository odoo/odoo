// @ts-check

/** @module @web/webclient/actions/action_button_executor - Executes action buttons (type=object/action/special) with RPC, context filtering, and UI blocking */

/**
 * Extracted action-button execution logic.
 *
 * Receives a context object from action_service.js with the closure
 * dependencies it needs, following the same context-passing pattern
 * as report_executor.js and breadcrumb_manager.js.
 */

import { markup } from "@odoo/owl";
import { browser } from "@web/core/browser/browser";
import { makeContext } from "@web/core/context";
import { rpc } from "@web/core/network/rpc";
import { evaluateExpr } from "@web/core/py_js/py";
import { exprToBoolean } from "@web/core/utils/format/strings";
import { user } from "@web/services/user";

import { CTX_KEY_REGEX, EMBEDDED_ACTIONS_CTX_KEYS } from "./action_constants";

/** @typedef {import("@web/core/utils/concurrency").KeepLast} KeepLast */
/** @typedef {Object} DoActionButtonParams */

export class InvalidButtonParamsError extends Error {}

/**
 * Execute an action button (type="object", type="action", or special).
 *
 * Handles RPC calls, embedded-action recursion, context filtering,
 * UI blocking, and effect triggering.
 *
 * @param {DoActionButtonParams} params
 * @param {Object} [options={}]
 * @param {boolean} [options.isEmbeddedAction] set to true if the action
 *   request is an embedded action (avoids infinite recursion).
 * @param {boolean} [options.newWindow] set to true to open in a new tab.
 * @param {Object} [ctx] - closure dependencies from the action service
 * @param {Object} [ctx.env]
 * @param {KeepLast} [ctx.keepLast]
 * @param {Function} [ctx.loadAction]
 * @param {Function} [ctx.doAction]
 * @param {Function} [ctx.doActionButton] - for recursive embedded-action calls
 * @param {Function} [ctx.executeCloseAction]
 * @returns {Promise<void>}
 */
export async function executeActionButton(
    params,
    { isEmbeddedAction, newWindow } = {},
    ctx,
) {
    if (!params.name) {
        return;
    }
    // determine the action to execute according to the params
    let action;
    if (!isEmbeddedAction) {
        for (const key of EMBEDDED_ACTIONS_CTX_KEYS) {
            delete params.context?.[key];
        }
    }
    const context = makeContext([params.context, params.buttonContext]);
    const blockUi = exprToBoolean(params["block-ui"]);
    if (blockUi) {
        ctx.env.services.ui.block();
    }
    if (params.special) {
        action = {
            type: "ir.actions.act_window_close",
            infos: { special: true },
        };
    } else if (params.type === "object") {
        // call a Python Object method, which may return an action to execute
        let args = params.resId ? [[params.resId]] : [params.resIds];
        if (params.args) {
            let additionalArgs = [];
            try {
                // warning: quotes and double quotes problem due to json and xml clash
                // maybe we should force escaping in xml or do a better parse of the args array
                additionalArgs = JSON.parse(params.args.replaceAll("'", '"'));
            } catch {
                browser.console.error("Could not JSON.parse arguments", params.args);
            }
            args = [...args, ...additionalArgs];
        }
        const callProm = rpc(
            `/web/dataset/call_button/${params.resModel}/${params.name}`,
            {
                args,
                kwargs: { context },
                method: params.name,
                model: params.resModel,
            },
        );
        action = await ctx.keepLast.add(callProm);
        action =
            action && typeof action === "object"
                ? action
                : { type: "ir.actions.act_window_close" };
        if (action.help) {
            action.help = markup(action.help);
        }
    } else if (params.type === "action") {
        // execute a given action, so load it first
        context.active_id = params.resId ?? null;
        context.active_ids = params.resIds;
        context.active_model = params.resModel;
        action = await ctx.keepLast.add(ctx.loadAction(params.name, context));
    } else {
        if (blockUi) {
            ctx.env.services.ui.unblock();
        }
        throw new InvalidButtonParamsError("Missing type for doActionButton request");
    }
    if (!isEmbeddedAction && action.embedded_action_ids?.length) {
        const embeddedActionsKey = `${action.id}+${params.resId || ""}`;
        const embeddedActionsOrder =
            user.settings.embedded_actions_config_ids?.[embeddedActionsKey]
                ?.embedded_actions_order;
        const embeddedActionId = embeddedActionsOrder?.[0];
        const embeddedAction = action.embedded_action_ids?.find(
            (embeddedAction) => embeddedAction.id === embeddedActionId,
        );
        if (embeddedAction) {
            const embeddedActions = [
                ...action.embedded_action_ids,
                {
                    id: false,
                    name: action.name,
                    parent_action_id: action.id,
                    parent_res_model: action.res_model,
                    action_id: action.id,
                    user_id: false,
                    context: {},
                },
            ];
            const embeddedContext = {
                ...action.context,
                ...(embeddedAction.context
                    ? makeContext([embeddedAction.context])
                    : {}),
                active_id: params.resId,
                active_model: params.resModel,
                current_embedded_action_id: embeddedActionId,
                parent_action_embedded_actions: embeddedActions,
                parent_action_id: action.id,
            };
            await ctx.doActionButton(
                {
                    name:
                        embeddedAction.python_method ||
                        embeddedAction.action_id[0] ||
                        embeddedAction.action_id,
                    resId: params.resId,
                    context: embeddedContext,
                    type: embeddedAction.python_method ? "object" : "action",
                    resModel: embeddedAction.parent_res_model,
                    viewType: embeddedAction.default_view_mode,
                },
                { isEmbeddedAction: true },
            );
            return;
        }
    }
    // filter out context keys that are specific to the current action, because:
    //  - wrong default_* and search_default_* values won't give the expected result
    //  - wrong group_by values will fail and forbid rendering of the destination view
    const currentCtx = {};
    for (const key in params.context) {
        if (key.match(CTX_KEY_REGEX) === null) {
            currentCtx[key] = params.context[key];
        }
    }
    const activeCtx = { active_model: params.resModel };
    if (params.resId) {
        activeCtx.active_id = params.resId;
        activeCtx.active_ids = [params.resId];
    }
    action.context = makeContext([
        currentCtx,
        params.buttonContext,
        activeCtx,
        action.context,
    ]);
    // in case an effect is returned from python and there is already an effect
    // attribute on the button, the priority is given to the button attribute
    const effect = params.effect ? evaluateExpr(params.effect) : action.effect;
    const { onClose, stackPosition, viewType } = params;
    await ctx.doAction(action, {
        newWindow,
        onClose,
        stackPosition,
        viewType,
    });
    if (params.close) {
        await ctx.executeCloseAction();
    }
    if (blockUi) {
        ctx.env.services.ui.unblock();
    }
    if (effect) {
        ctx.env.services.effect.add(effect);
    }
}
