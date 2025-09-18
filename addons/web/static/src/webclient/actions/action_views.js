// @ts-check

/** @module @web/webclient/actions/action_views - View lookup and action display mode resolution for the action service */

/**
 * View lookup and action mode resolution for the action service.
 */

/**
 * Find a view descriptor matching the given type and multi-record flag.
 *
 * @param {Object[]} views - available view descriptors
 * @param {boolean} multiRecord - whether to match multi-record views
 * @param {string} viewType - the view type to find
 * @returns {Object|undefined}
 */
export function findView(views, multiRecord, viewType) {
    return views.find((v) => v.type === viewType && v.multiRecord === multiRecord);
}

/**
 * Determine the effective display mode for an action.
 *
 * Client actions may force a target via their registry definition.
 * Falls back to "current" when no explicit target is set.
 *
 * @param {Object} action - preprocessed action descriptor
 * @param {Object} actionRegistry - the "actions" registry category
 * @returns {"current"|"fullscreen"|"new"|"main"}
 */
export function getActionMode(action, actionRegistry) {
    if (action.target === "new") {
        return "new";
    }
    if (action.type === "ir.actions.client") {
        const clientAction = actionRegistry.get(action.tag);
        if (clientAction.target) {
            return clientAction.target;
        }
    }
    if (action.target === "fullscreen") {
        return "fullscreen";
    }
    return "current";
}
