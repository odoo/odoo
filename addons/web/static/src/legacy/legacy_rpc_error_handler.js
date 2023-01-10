/** @odoo-module **/

import { registry } from "@web/core/registry";
import { ConnectionLostError, RPCError } from "../core/network/rpc_service";
import { lostConnectionHandler, rpcErrorHandler } from "@web/core/errors/error_handlers";

const errorHandlerRegistry = registry.category("error_handlers");

/**
 * @typedef {import("../env").OdooEnv} OdooEnv
 * @typedef {import("../core/errors/error_service").UncaughtError} UncaughError
 */

// -----------------------------------------------------------------------------
// Legacy RPC error handling
// -----------------------------------------------------------------------------

/**
 * @param {OdooEnv} env
 * @param {UncaughError} error
 * @param {Error} originalError
 * @returns {boolean}
 */
function legacyRPCErrorHandler(env, error, originalError) {
    if (
        originalError &&
        originalError.legacy &&
        originalError.message &&
        (originalError.message instanceof RPCError ||
            originalError.message instanceof ConnectionLostError)
    ) {
        const event = originalError.event;
        originalError = originalError.message;
        if (event.isDefaultPrevented()) {
            // in theory, here, event was already handled
            error.unhandledRejectionEvent.preventDefault();
            return true;
        }
        event.preventDefault();
        if (originalError instanceof ConnectionLostError) {
            return lostConnectionHandler(env, error, originalError);
        }
        return rpcErrorHandler(env, error, originalError);
    }
    return false;
}
errorHandlerRegistry.add("legacyRPCErrorHandler", legacyRPCErrorHandler, { sequence: 2 });
