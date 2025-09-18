// @ts-check

/** @module @web/webclient/actions/action_state - URL state serialization/deserialization for the action service (router integration) */

/**
 * URL state serialization and deserialization for the action service.
 */

import { markup } from "@odoo/owl";
import { browser } from "@web/core/browser/browser";
import { PATH_KEYS } from "@web/core/browser/router";
import { registry } from "@web/core/registry";
import { omit, pick, shallowEqual } from "@web/core/utils/collections/objects";
import { user } from "@web/services/user";

import { parseActiveIds } from "./action_constants";

/**
 * Serialize a controller stack into a URL-pushable state object.
 *
 * Produces an `actionStack` array (one entry per controller) plus
 * top-level keys for the last controller's state so that the router
 * can reconstruct the breadcrumb on page load.
 *
 * @param {Object[]} controllerStack - array of controller objects
 * @returns {Object} state suitable for `router.pushState`
 */
export function makeActionState(controllerStack) {
    const actions = controllerStack.map((controller) => {
        const { action, props, displayName } = controller;
        const actionState = { displayName };
        if (action.path || action.id) {
            actionState.action = action.path || action.id;
        } else if (action.type === "ir.actions.client") {
            actionState.action = action.tag;
        } else if (action.type === "ir.actions.act_window") {
            actionState.model = props.resModel;
        }
        if (action.type === "ir.actions.act_window") {
            actionState.view_type = props.type;
            if (props.type === "form" && action.res_model !== "res.config.settings") {
                // Use || (not ??): buildViewInfo defaults resId to false for
                // new records, and false is not nullish. Any valid record ID
                // is a positive integer, so || is safe here.
                actionState.resId = controller.currentState.resId || "new";
            }
        }
        if (action.type === "ir.actions.client" && controller.currentState?.resId) {
            actionState.resId = controller.currentState.resId;
        }

        if (controller.currentState?.active_id != null) {
            actionState.active_id = controller.currentState.active_id;
        }
        Object.assign(actionState, omit(controller.currentState || {}, ...PATH_KEYS));
        return actionState;
    });
    const newState = {
        actionStack: actions,
    };
    const stateKeys = [...PATH_KEYS];
    const { action, props, currentState } = controllerStack.at(-1);
    if (props.type !== "form" && props.type !== action.views?.[0][1]) {
        // add view_type only when it's not already known implicitly
        stateKeys.push("view_type");
    }
    if (currentState) {
        stateKeys.push(...Object.keys(omit(currentState, ...PATH_KEYS)));
    }
    return Object.assign(
        newState,
        pick(newState.actionStack.at(-1), .../** @type {any} */ (stateKeys)),
    );
}

/**
 * Reconstruct an action request and options from a URL state object.
 *
 * Restores client actions from the registry, window actions from session
 * storage, and handles recursive actionStack unwinding for invalid states.
 * Pure function — all external dependencies are module-level imports.
 *
 * @param {Object} state - the URL state to parse
 * @returns {{ actionRequest: Object, options: Object } | null}
 */
export function getActionParams(state) {
    const actionRegistry = registry.category("actions");
    const options = {};
    let actionRequest = null;
    const storedAction = browser.sessionStorage.getItem("current_action");
    const lastAction = JSON.parse(storedAction || "{}");
    // If this method is called because of a company switch, the
    // stored allowed_company_ids is incorrect.
    delete lastAction.context?.allowed_company_ids;
    if (lastAction.help) {
        lastAction.help = markup(lastAction.help);
    }
    if (state.action) {
        const context = {};
        if (state.active_id) {
            context.active_id = state.active_id;
        }
        if (state.active_ids) {
            context.active_ids = parseActiveIds(state.active_ids);
        } else if (state.active_id) {
            context.active_ids = [state.active_id];
        }
        // ClientAction
        const [actionRequestKey, clientAction] = actionRegistry.contains(state.action)
            ? [state.action, actionRegistry.get(state.action)]
            : (actionRegistry.getEntries().find((a) => a[1].path === state.action) ??
              []);
        if (actionRequestKey && clientAction) {
            actionRequest = /** @type {any} */ ({
                context,
                params: state,
                tag: actionRequestKey,
                type: "ir.actions.client",
            });
            if (/** @type {any} */ (clientAction).path) {
                actionRequest.path = /** @type {any} */ (clientAction).path;
            }
        } else {
            // The action to load isn't the current one => executes it
            Object.assign(options, {
                additionalContext: context,
                viewType: state.resId ? "form" : state.view_type,
            });
            if (
                [lastAction.id, lastAction.path, lastAction.xml_id]
                    .filter(Boolean)
                    .includes(state.action) &&
                (!lastAction.context?.active_id ||
                    lastAction.context?.active_id === context.active_id) &&
                (!lastAction.context?.active_ids ||
                    shallowEqual(lastAction.context?.active_ids, context.active_ids)) &&
                !lastAction.embedded_action_ids?.length
            ) {
                actionRequest = lastAction;
            } else {
                actionRequest = state.action;
            }
        }
        if ((state.resId && state.resId !== "new") || state.globalState) {
            options.props = {};
            if (state.resId && state.resId !== "new") {
                options.props.resId = state.resId;
            }
            if (state.globalState) {
                options.props.globalState = state.globalState;
            }
        }
    } else if (state.model) {
        if (state.resId || state.view_type === "form") {
            actionRequest = {
                res_model: state.model,
                res_id: state.resId === "new" ? undefined : state.resId,
                type: "ir.actions.act_window",
                views: [[state.view_id ? state.view_id : false, "form"]],
            };
        } else {
            // This is a window action on a multi-record view => restores it from
            // the session storage
            if (lastAction.res_model === state.model) {
                actionRequest = lastAction;
                options.viewType = state.view_type;
            }
        }
    }
    if (!actionRequest) {
        // If the last action isn't valid (eg a model with no resId and no view_type) which can
        // happen if the user edits the url and removes the id from the end of the url, we don't want
        // to send him back to the home menu: we unwind the actionStack until we find a valid action
        const { actionStack } = state;
        if (actionStack?.length > 1) {
            const nextState = { actionStack: actionStack.slice(0, -1) };
            Object.assign(nextState, nextState.actionStack.at(-1));
            const params = getActionParams(nextState);
            // Place the controller at the found position in the action stack to remove all the
            // invalid virtual controllers.
            if (params.options && params.options.index === undefined) {
                params.options.index = nextState.actionStack.length - 1;
            }
            return params;
        }
        // Fall back to the home action if no valid action was found
        actionRequest = user.homeActionId;
    }
    return actionRequest ? { actionRequest, options } : null;
}
