/** @odoo-module */

import { markup } from "@odoo/owl";

/**
 * @typedef {import("@web/webclient/actions/action_service").ActionOptions} ActionOptions
 */

/**
 * @param {*} env
 * @param {string} actionXmlId
 * @param {Object} actionDescription
 * @param {ActionOptions} options
 */
export async function navigateTo(env, actionXmlId, actionDescription, options) {
    const actionService = env.services.action;
    let navigateActionDescription;
    const { views, view_mode, domain, context, name, res_model, res_id } = actionDescription;
    try {
        navigateActionDescription = await actionService.loadAction(actionXmlId, context);
        const filteredViews = views.map(
            ([v, viewType]) =>
                navigateActionDescription.views.find(([, type]) => viewType === type) || [
                    v,
                    viewType,
                ]
        );

        navigateActionDescription = {
            ...navigateActionDescription,
            context,
            domain,
            name,
            res_model,
            res_id,
            view_mode,
            target: "current",
            views: filteredViews,
        };
    } catch {
        navigateActionDescription = {
            type: "ir.actions.act_window",
            name,
            res_model,
            res_id,
            views,
            target: "current",
            domain,
            context,
            view_mode,
        };
    } finally {
        // clear empty keys
        const cleanedActionDescription = JSON.parse(JSON.stringify(navigateActionDescription));
        if (cleanedActionDescription.help) {
            // JSON.stringify/parse strips the trusted `markup`, so restore it before rendering.
            cleanedActionDescription.help = markup(cleanedActionDescription.help);
        }
        await actionService.doAction(cleanedActionDescription, options);
    }
}
