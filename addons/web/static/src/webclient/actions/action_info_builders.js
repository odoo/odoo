// @ts-check

/** @module @web/webclient/actions/action_info_builders - Builds props, config, and state for client action and view controllers */

/**
 * Builders for action and view controller info objects.
 *
 * Extracted from action_service.js to reduce file size and isolate the logic
 * that builds props/config/state for controllers in the action manager.
 */

import { shallowEqual } from "@web/core/utils/collections/objects";
import { session } from "@web/session";

/**
 * Build the props, config, currentState, and displayName for a client action controller.
 *
 * @param {Object} action the client action descriptor
 * @param {Object} props initial props to merge
 * @param {Object} callbacks
 * @param {Function} callbacks.pushState push current state to the router
 * @returns {{ props: Object, currentState: Object, config: Object, displayName: string }}
 */
export function buildActionInfo(action, props, { pushState }) {
    const actionProps = { ...props, action, actionId: action.id };
    const currentState = {
        resId: actionProps.resId ?? false,
        // Do not default to false: action_state.js serializes non-null values,
        // and false would leak "active_id":false into the URL state.
        active_id: action.context.active_id,
    };
    actionProps.updateActionState = (controller, patchState) => {
        const oldState = { ...currentState };
        Object.assign(currentState, patchState);
        const changed = !shallowEqual(currentState, oldState);
        if (changed && action.target !== "new" && controller.isMounted) {
            pushState();
        }
    };
    return {
        props: actionProps,
        currentState,
        config: {
            actionId: action.id,
            actionType: "ir.actions.client",
        },
        displayName: action.display_name || action.name || "",
    };
}

/**
 * Build the props, config, currentState, and displayName for a view (act_window) controller.
 *
 * @param {Object} view the view descriptor (type, icon, display_name, multiRecord)
 * @param {Object} action the act_window action descriptor
 * @param {Object[]} views all available views for this action
 * @param {Object} props initial props to merge
 * @param {Object} callbacks
 * @param {Function} callbacks.getView get a view by type from the current action
 * @param {Function} callbacks.switchView switch to a different view type
 * @param {Function} callbacks.doAction execute an action
 * @param {Function} callbacks.pushState push current state to the router
 * @returns {{ props: Object, currentState: Object, config: Object, displayName: string }}
 */
export function buildViewInfo(view, action, views, props = {}, callbacks) {
    const { getView, switchView, doAction, pushState } = callbacks;
    const target = action.target;
    const viewSwitcherEntries = views
        .filter((v) => v.multiRecord === view.multiRecord)
        .map((v) => {
            const viewSwitcherEntry = {
                icon: v.icon,
                name: v.display_name,
                type: v.type,
                multiRecord: v.multiRecord,
            };
            if (view.type === v.type) {
                viewSwitcherEntry.active = true;
            }
            return viewSwitcherEntry;
        });
    const context = action.context || {};
    let groupBy = context.group_by || [];
    if (typeof groupBy === "string") {
        groupBy = [groupBy];
    }
    const openFormView = (
        resId,
        { activeIds, readonly, force, newWindow } = /** @type {any} */ ({}),
    ) => {
        if (target !== "new") {
            if (getView("form")) {
                return switchView(
                    "form",
                    { readonly, resId, resIds: activeIds },
                    { newWindow },
                );
            } else if (force || !resId) {
                return doAction(
                    {
                        type: "ir.actions.act_window",
                        res_model: action.res_model,
                        views: [[false, "form"]],
                    },
                    {
                        newWindow,
                        props: { readonly, resId, resIds: activeIds },
                    },
                );
            }
        }
    };
    const viewProps = {
        ...props,
        context,
        display: { mode: target === "new" ? "inDialog" : target },
        domain: action.domain || [],
        groupBy,
        loadActionMenus: target !== "new" && action.res_model !== "res.config.settings",
        loadIrFilters: action.views.some((v) => v[1] === "search"),
        resModel: action.res_model,
        type: view.type,
        selectRecord: openFormView,
        createRecord: () => openFormView(false),
    };
    if (view.type === "form") {
        if (target === "new") {
            viewProps.readonly = false;
            if (!viewProps.onSave) {
                viewProps.onSave = (record, params) => {
                    if (params && params.closable) {
                        doAction({ type: "ir.actions.act_window_close" });
                    }
                };
            }
        }
    }

    const specialKeys = ["help", "useSampleModel", "limit", "count"];
    for (const key of specialKeys) {
        if (key in action) {
            if (key === "help") {
                viewProps.noContentHelp = action.help;
            } else {
                viewProps[key] = action[key];
            }
        }
    }

    if (context.search_disable_custom_filters) {
        viewProps.activateFavorite = false;
    }

    // view specific
    if (!viewProps.resId) {
        viewProps.resId = action.res_id ?? false;
    }

    const currentState = {
        resId: viewProps.resId,
        // Do not default to false: action_state.js serializes non-null values,
        // and false would leak "active_id":false into the URL state.
        active_id: action.context.active_id,
    };
    viewProps.updateActionState = (controller, patchState) => {
        const oldState = { ...currentState };
        Object.assign(currentState, patchState);
        const changed = !shallowEqual(currentState, oldState);
        if (changed && target !== "new" && controller.isMounted) {
            pushState();
        }
    };

    viewProps.noBreadcrumbs =
        "_noBreadcrumbs" in action ? action._noBreadcrumbs : target === "new";

    const embeddedActions =
        view.type === "form"
            ? []
            : context.parent_action_embedded_actions || action.embedded_action_ids;
    const parentActionId = (view.type !== "form" && context.parent_action_id) || false;
    const currentEmbeddedActionId = context.current_embedded_action_id || false;
    return {
        props: viewProps,
        currentState,
        config: {
            actionId: action.id,
            actionName: action.name,
            cache: action.cache,
            actionType: "ir.actions.act_window",
            actionXmlId: action.xml_id,
            embeddedActions,
            parentActionId,
            currentEmbeddedActionId,
            views: action.views,
            viewSwitcherEntries,
        },
        displayName: action.display_name || action.name || "",
    };
}

/**
 * Build the views array for an act_window action, validating that all view types are known.
 *
 * @param {Object} action the act_window action descriptor
 * @returns {Object[]} array of view descriptors with { icon, display_name, multiRecord, type }
 * @throws {Error} if unknown view types are found or no views are available
 */
export function buildActionViews(action) {
    const views = [];
    const unknown = [];
    for (const [, type] of action.views) {
        if (type === "search") {
            continue;
        }
        if (session.view_info[type]) {
            const {
                icon,
                display_name,
                multi_record: multiRecord,
            } = session.view_info[type];
            views.push({ icon, display_name, multiRecord, type });
        } else {
            unknown.push(type);
        }
    }
    if (unknown.length) {
        throw new Error(
            `View types not defined ${unknown.join(", ")} found in act_window action ${action.id}`,
        );
    }
    if (!views.length) {
        throw new Error(`No view found for act_window action ${action.id}`);
    }
    return views;
}
