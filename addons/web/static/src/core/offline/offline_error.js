import { plugin } from "@odoo/owl";
import { UncaughtPromiseError } from "../errors/error_service";
import { ConnectionLostError } from "../network/rpc";
import { registry } from "../registry";
import { OfflinePlugin } from "./offline_plugin";

const errorHandlerRegistry = registry.category("error_handlers");

// -----------------------------------------------------------------------------
// Lost connection errors
// -----------------------------------------------------------------------------

/**
 * @param {OdooEnv} env
 * @param {UncaughError} error
 * @param {Error} originalError
 * @returns {boolean}
 */
export function lostConnectionHandler(env, error, originalError) {
    if (!(error instanceof UncaughtPromiseError)) {
        return false;
    }
    if (originalError instanceof ConnectionLostError) {
        const offlinePlugin = plugin(OfflinePlugin);
        offlinePlugin.setOffline(true);
        return true;
    }
}
errorHandlerRegistry.add("lostConnectionHandler", lostConnectionHandler, { sequence: 98 });
