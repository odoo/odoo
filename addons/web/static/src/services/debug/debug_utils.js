// @ts-check

/** @module @web/services/debug/debug_utils - Opens a form view action for a given model/record in debug mode */

/**
 * Open a form view for the given model/record in debug mode.
 * @param {import("@web/env").OdooEnv} env
 * @param {string} title - window title for the action
 * @param {string} model - technical model name (e.g. "res.partner")
 * @param {number} id - record ID to edit
 * @returns {Promise<void>}
 */
export function editModelDebug(env, title, model, id) {
    return env.services.action.doAction({
        res_model: model,
        res_id: id,
        name: title,
        type: "ir.actions.act_window",
        views: [[false, "form"]],
        view_mode: "form",
        target: "current",
    });
}
