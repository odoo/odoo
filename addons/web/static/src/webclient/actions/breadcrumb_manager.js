// @ts-check

/** @module @web/webclient/actions/breadcrumb_manager - Breadcrumb building, display-name loading, and virtual controller reconstruction for the action service */

/**
 * Breadcrumb management functions for the action service.
 *
 * Handles building breadcrumb items from the controller stack, loading
 * display names for breadcrumb entries, and reconstructing virtual
 * controllers from router state.
 */

/**
 * Given a controller stack, return the list of breadcrumb items.
 *
 * @param {Object[]} stack the controller stack
 * @param {Object} callbacks
 * @param {Function} callbacks.stateToUrl convert a state object to a URL string
 * @param {Function} callbacks.restore restore a controller by its jsId
 * @returns {Object[]} breadcrumb items
 */

import { rpc } from "@web/core/network/rpc";
import { zip } from "@web/core/utils/collections/arrays";
import { pick } from "@web/core/utils/collections/objects";
export function buildBreadcrumbs(stack, { stateToUrl, restore }) {
    return stack
        .filter((controller) => controller.action.tag !== "menu")
        .map((controller) => ({
            jsId: controller.jsId,
            get name() {
                return controller.displayName;
            },
            get isFormView() {
                return controller.props?.type === "form";
            },
            get url() {
                return stateToUrl(controller.state);
            },
            onSelected() {
                restore(controller.jsId);
            },
        }));
}

/**
 * Load breadcrumbs for an array of controllers. Adds display names to
 * controllers that the current user has access to and for which the view
 * (and record) exist. Controllers that correspond to a deleted record or
 * a record/view that the user can't access are removed.
 *
 * @param {Object[]} controllers controllers whose breadcrumbs should be loaded
 * @param {Object} breadcrumbCache mutable cache object (shared by reference)
 * @returns {Promise<Object[]>} new array of displayable controllers with display names
 */
async function loadBreadcrumbs(controllers, breadcrumbCache) {
    const toFetch = [];
    const keys = [];
    for (const { action, state, displayName } of controllers) {
        if (
            action.id === "menu" ||
            (action.type === "ir.actions.client" && !displayName)
        ) {
            continue;
        }
        const actionInfo = pick(state, "action", "model", "resId");
        const key = JSON.stringify(actionInfo);
        keys.push(key);
        if (displayName) {
            breadcrumbCache[key] = { display_name: displayName };
        }
        if (key in breadcrumbCache) {
            continue;
        }
        toFetch.push(actionInfo);
    }
    if (toFetch.length) {
        const req = rpc("/web/action/load_breadcrumbs", { actions: toFetch });
        for (const [i, info] of toFetch.entries()) {
            const key = JSON.stringify(info);
            breadcrumbCache[key] = req.then((res) => {
                breadcrumbCache[key] = res[i];
                return res[i];
            });
        }
    }
    const results = await Promise.all(keys.map((k) => breadcrumbCache[k]));
    const controllersToRemove = [];
    for (const [controller, res] of zip(controllers, results)) {
        if ("display_name" in res) {
            controller.displayName = res.display_name;
        } else {
            controllersToRemove.push(controller);
            if ("error" in res) {
                console.warn(
                    "The following element was removed from the breadcrumb and from the url.\n",
                    controller.state,
                    "\nThis could be because the action wasn't found or because the user doesn't have the right to access to the record, the original error is :\n",
                    res.error,
                );
            }
        }
    }
    return controllers.filter((c) => !controllersToRemove.includes(c));
}

/**
 * Create an array of virtual controllers based on the given router state.
 *
 * @param {Object} state the router state
 * @param {Object} ctx
 * @param {Storage} ctx.sessionStorage browser session storage
 * @param {Function} ctx.stateToUrl convert state to URL string
 * @param {Function} ctx.makeController factory to create a controller object
 * @param {Object} ctx.actionRegistry the client action registry
 * @param {Object} ctx.breadcrumbCache mutable breadcrumb cache
 * @returns {Promise<Object[]>} array of virtual controllers
 */
export async function controllersFromState(state, ctx) {
    const {
        sessionStorage,
        stateToUrl,
        makeController,
        actionRegistry,
        breadcrumbCache,
    } = ctx;
    const currentState = JSON.parse(sessionStorage.getItem("current_state") || "{}");
    if (stateToUrl(currentState) === stateToUrl(state)) {
        state = currentState;
    }
    if (!state?.actionStack?.length) {
        return [];
    }
    // The last controller will be created by doAction and won't be virtual
    const controllers = state.actionStack
        .slice(0, -1)
        .map((actionState, index) => {
            const controller = makeController({
                displayName: actionState.displayName,
                virtual: true,
                action: {},
                props: {},
                state: {
                    ...actionState,
                    actionStack: state.actionStack.slice(0, index + 1),
                },
                currentState: {},
            });
            if (actionState.action) {
                controller.action.id = actionState.action;

                const [actionRequestKey, clientAction] = actionRegistry.contains(
                    actionState.action,
                )
                    ? [actionState.action, actionRegistry.get(actionState.action)]
                    : (actionRegistry
                          .getEntries()
                          .find((a) => a[1].path === actionState.action) ?? []);
                if (actionRequestKey && clientAction) {
                    if (state.actionStack[index + 1]?.action === actionState.action) {
                        // client actions don't have multi-record views, so we can't go further to the next controller
                        return;
                    }
                    controller.action.tag = actionRequestKey;
                    controller.action.type = "ir.actions.client";
                    controller.displayName = clientAction.displayName?.toString();
                }
                if (actionState.active_id) {
                    controller.action.context = {
                        active_id: actionState.active_id,
                    };
                    controller.currentState.active_id = actionState.active_id;
                }
            }
            if (actionState.model) {
                controller.action.type = "ir.actions.act_window";
                controller.props.resModel = actionState.model;
            }
            if (actionState.resId) {
                controller.action.type ||= "ir.actions.act_window";
                controller.props.resId = actionState.resId;
                controller.currentState.resId = actionState.resId;
                controller.props.type = "form";
            }
            return controller;
        })
        .filter(Boolean);

    if (
        state.action &&
        state.resId &&
        controllers.at(-1)?.action?.id === state.action
    ) {
        // When loading the state on a form view, we will need to load the action for it,
        // and this will give us the display name of the corresponding multi-record view in
        // the breadcrumb.
        // By marking the last controller as a lazyController, we can in some cases avoid
        // loadBreadcrumbs from doing any network request as the breadcrumbs may only contain
        // the form view and the multi-record view.
        const bcControllers = await loadBreadcrumbs(
            controllers.slice(0, -1),
            breadcrumbCache,
        );
        controllers.at(-1).lazy = true;
        return [...bcControllers, controllers.at(-1)];
    }
    return loadBreadcrumbs(controllers, breadcrumbCache);
}
