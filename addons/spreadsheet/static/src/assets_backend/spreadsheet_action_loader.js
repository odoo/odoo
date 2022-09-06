/** @odoo-module **/

import { registry } from "@web/core/registry";
import { loadBundle } from "@web/core/assets";
import { sprintf } from "@web/core/utils/strings";

const actionRegistry = registry.category("actions");

/**
 *
 * @param {object} env
 * @param {string} actionName
 * @param {function} actionLazyLoader
 */
export async function loadSpreadsheetAction(env, actionName, actionLazyLoader) {
    await loadBundle("spreadsheet.o_spreadsheet");

    if (actionRegistry.get(actionName) === actionLazyLoader) {
        // At this point, the real spreadsheet client action should be loaded and have
        // replaced this function in the action registry. If it's not the case,
        // it probably means that there was a crash in the bundle (e.g. syntax
        // error). In this case, this action will remain in the registry, which
        // will lead to an infinite loop. To prevent that, we push another action
        // in the registry.
        actionRegistry.add(
            actionName,
            () => {
                const msg = sprintf(env._t("%s couldn't be loaded"), actionName);
                env.services.notification.add(msg, { type: "danger" });
            },
            { force: true }
        );
    }
}

const loadSpreadsheetDownloadAction = async (env, context) => {
    await loadSpreadsheetAction(env, "action_download_spreadsheet", loadSpreadsheetDownloadAction);

    return {
        ...context,
        target: "current",
        tag: "action_download_spreadsheet",
        type: "ir.actions.client",
    };
};

actionRegistry.add("action_download_spreadsheet", loadSpreadsheetDownloadAction);
