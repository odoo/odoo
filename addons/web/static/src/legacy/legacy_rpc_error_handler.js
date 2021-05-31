/** @odoo-module **/

import { registry } from "@web/core/registry";
import { RPCErrorDialog } from "../core/errors/error_dialogs";

const errorDialogRegistry = registry.category("error_dialogs");
const errorHandlerRegistry = registry.category("error_handlers");

/**
 * @typedef {import("../env").OdooEnv} OdooEnv
 * @typedef {import("../core/errors/error_service").UncaughtError} UncaughError
 * @typedef {(error: UncaughError) => boolean | void} ErrorHandler
 */

// -----------------------------------------------------------------------------
// Legacy RPC error handling
// -----------------------------------------------------------------------------

/**
 * @param {OdooEnv} env
 * @returns {ErrorHandler}
 */
function legacyRPCErrorHandler(env) {
    return (uncaughtError) => {
        let error = uncaughtError.originalError;
        if (error && error.legacy && error.message && error.message.name === "RPC_ERROR") {
            const event = error.event;
            error = error.message;
            uncaughtError.unhandledRejectionEvent.preventDefault();
            if (event.isDefaultPrevented()) {
                // in theory, here, event was already handled
                return true;
            }
            event.preventDefault();
            const exceptionName = error.exceptionName;
            let ErrorComponent = error.Component;
            if (!ErrorComponent && exceptionName && errorDialogRegistry.contains(exceptionName)) {
                ErrorComponent = errorDialogRegistry.get(exceptionName);
            }

            env.services.dialog.open(ErrorComponent || RPCErrorDialog, {
                traceback: error.traceback || error.stack,
                message: error.message,
                name: error.name,
                exceptionName: error.exceptionName,
                data: error.data,
                subType: error.subType,
                code: error.code,
                type: error.type,
            });
            return true;
        }
    };
}
errorHandlerRegistry.add("legacyRPCErrorHandler", legacyRPCErrorHandler, { sequence: 2 });
