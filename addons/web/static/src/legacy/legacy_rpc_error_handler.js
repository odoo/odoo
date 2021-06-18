/** @odoo-module **/

import { registry } from "@web/core/registry";
import { RPCErrorDialog } from "../core/errors/error_dialogs";
import { RPCError } from "../core/network/rpc_service";

const errorDialogRegistry = registry.category("error_dialogs");
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
 * @param {Error} error
 * @param {Error} originalError
 * @returns {boolean}
 */
function legacyRPCErrorHandler(env, error, originalError) {
    if (
        originalError &&
        originalError.legacy &&
        originalError.message &&
        originalError.message instanceof RPCError
    ) {
        const event = originalError.event;
        originalError = originalError.message;
        error.unhandledRejectionEvent.preventDefault();
        if (event.isDefaultPrevented()) {
            // in theory, here, event was already handled
            return true;
        }
        event.preventDefault();
        const exceptionName = originalError.exceptionName;
        let ErrorComponent = originalError.Component;
        if (!ErrorComponent && exceptionName && errorDialogRegistry.contains(exceptionName)) {
            ErrorComponent = errorDialogRegistry.get(exceptionName);
        }

        env.services.dialog.add(ErrorComponent || RPCErrorDialog, {
            traceback: originalError.traceback || originalError.stack,
            message: originalError.message,
            name: originalError.name,
            exceptionName: originalError.exceptionName,
            data: originalError.data,
            subType: originalError.subType,
            code: originalError.code,
            type: originalError.type,
        });
        return true;
    }
    return false;
}
errorHandlerRegistry.add("legacyRPCErrorHandler", legacyRPCErrorHandler, { sequence: 2 });
