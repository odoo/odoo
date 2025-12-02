import { UncaughtPromiseError } from "../errors/error_service";
import { ConnectionLostError } from "../network/rpc";
import { registry } from "../registry";

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
        env.services.offline.offline = true;
        return true;
    }
}
errorHandlerRegistry.add("lostConnectionHandler", lostConnectionHandler, { sequence: 98 });
