import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { loadBundle } from "@web/core/assets";

const actionRegistry = registry.category("actions");

/**
 * Add a new function client action which loads the spreadsheet bundle, then
 * launch the actual action.
 * The action should be redefine in the bundle with `{ force: true }`
 * and the actual action component or function
 * @param {string} actionName
 * @param {string} [path]
 * @param {string} [displayName]
 */
export function addSpreadsheetActionLazyLoader(actionName, path, displayName) {
    const actionLazyLoader = async (env, action) => {
        // load the bundle which should redefine the action in the registry
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
                    const msg = _t("%s couldn't be loaded", actionName);
                    env.services.notification.add(msg, { type: "danger" });
                },
                { force: true }
            );
        }
        // then do the action again, with the actual definition registered
        return action;
    };
    if (path) {
        actionLazyLoader.path = path;
    }
    if (displayName) {
        actionLazyLoader.displayName = displayName;
    }
    actionRegistry.add(actionName, actionLazyLoader);
}

addSpreadsheetActionLazyLoader("action_download_spreadsheet");
