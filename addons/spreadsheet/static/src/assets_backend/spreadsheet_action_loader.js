/** @odoo-module native */
import { loadBundle } from "@web/core/assets";
import { makeLogger } from "@web/core/debug/debug_logger";
import { registry } from "@web/core/registry";
import { _t } from "@web/core/translation";
import { startMissingServices } from "@web/env";

const actionRegistry = registry.category("actions");

const log = makeLogger("spreadsheet.action_loader");

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
        log.lifecycle("lazyLoad:start", { actionName });
        const endBundle = log.perf("loadBundle spreadsheet.o_spreadsheet");
        // load the bundle which should redefine the action in the registry
        await loadBundle("spreadsheet.o_spreadsheet");
        endBundle({ actionName });

        // loadBundle only guarantees the bundle's modules were evaluated, which
        // merely *registers* the services they declare (e.g.
        // spreadsheet_dashboard_loader). Starting them runs asynchronously
        // afterwards, so without this await the action component below can mount
        // and call useService(...) before the service exists — which throws and
        // renders a blank action (notably: no dashboard ever shows). Force a
        // full startup pass so the bundle's services are available first.
        const endServices = log.perf("startMissingServices");
        await startMissingServices(env);
        endServices({ actionName });

        if (actionRegistry.get(actionName) === actionLazyLoader) {
            log.logic("lazyLoad:actionNotRedefined", { actionName });
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
                { force: true },
            );
        }
        log.lifecycle("lazyLoad:done", { actionName });
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
