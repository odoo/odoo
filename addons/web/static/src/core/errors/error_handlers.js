import { usePlugin } from "@odoo/owl";
import { DebugModePlugin } from "@web/core/debug_mode_plugin";
import {
    ClientErrorDialog,
    ErrorDialog,
    NetworkErrorDialog,
    RequestEntityTooLargeErrorDialog,
    RPCErrorDialog,
} from "@web/core/errors/error_dialogs";
import {
    ThirdPartyScriptError,
    UncaughtClientError,
    UncaughtPromiseError,
} from "@web/core/errors/error_service";
import { RequestEntityTooLargeError, RPCError } from "@web/core/network/rpc";
import { registry } from "@web/core/registry";
import { user } from "@web/core/user";
import { useService } from "@web/core/utils/hooks";
import { session } from "@web/session";

/**
 * @typedef {import("../../env").OdooEnv} OdooEnv
 * @typedef {import("./error_service").UncaughtError} UncaughError
 */

const errorHandlerRegistry = registry.category("error_handlers");
const errorDialogRegistry = registry.category("error_dialogs");
const errorNotificationRegistry = registry.category("error_notifications");

// -----------------------------------------------------------------------------
// RPC errors
// -----------------------------------------------------------------------------

/**
 * @param {OdooEnv} env
 * @param {UncaughError} error
 * @param {Error} originalError
 * @returns {boolean}
 */
export function rpcErrorHandler(env, error, originalError) {
    if (!(error instanceof UncaughtPromiseError)) {
        return false;
    }

    const notification = useService("notification");
    const dialog = useService("dialog");

    if (originalError instanceof RPCError) {
        // When an error comes from the server, it can have an exeption name.
        // (or any string truly). It is used as key in the error dialog from
        // server registry to know which dialog component to use.
        // It's how a backend dev can easily map its error to another component.
        // Note that for a client side exception, we don't use this registry
        // as we can directly assign a value to `component`.
        // error is here a RPCError
        error.unhandledRejectionEvent.preventDefault();
        const exceptionName = originalError.exceptionName;
        let ErrorComponent = originalError.Component;
        if (!ErrorComponent && exceptionName) {
            if (errorNotificationRegistry.contains(exceptionName)) {
                const notif = errorNotificationRegistry.get(exceptionName);
                notification.add(notif.message || originalError.data.message, notif);
                return true;
            }
            if (errorDialogRegistry.contains(exceptionName)) {
                ErrorComponent = errorDialogRegistry.get(exceptionName);
            }
        }
        if (!ErrorComponent && originalError.data.context) {
            const exceptionClass = originalError.data.context.exception_class;
            if (errorDialogRegistry.contains(exceptionClass)) {
                ErrorComponent = errorDialogRegistry.get(exceptionClass);
            }
        }

        dialog.add(ErrorComponent || RPCErrorDialog, {
            traceback: error.traceback,
            message: originalError.message,
            name: originalError.name,
            exceptionName: originalError.exceptionName,
            data: originalError.data,
            subType: originalError.subType,
            code: originalError.code,
            type: originalError.type,
            serverHost: error.event?.target?.location.host,
            model: originalError.model,
        });
        return true;
    }
}

errorHandlerRegistry.add("rpcErrorHandler", rpcErrorHandler, { sequence: 97 });

// -----------------------------------------------------------------------------
// Request entity too large errors
// -----------------------------------------------------------------------------

/**
 * @param {OdooEnv} env
 * @param {UncaughError} error
 * @param {Error} originalError
 * @returns {boolean}
 */
export function requestEntityTooLargeHandler(env, error, originalError) {
    if (!(error instanceof UncaughtPromiseError)) {
        return false;
    }

    const dialog = useService("dialog");

    if (originalError instanceof RequestEntityTooLargeError) {
        dialog.add(RequestEntityTooLargeErrorDialog);
        return true;
    }
}
errorHandlerRegistry.add("requestEntityTooLargeHandler", requestEntityTooLargeHandler, {
    sequence: 99,
});

// -----------------------------------------------------------------------------
// Default handler
// -----------------------------------------------------------------------------

const defaultDialogs = new Map([
    [UncaughtClientError, ClientErrorDialog],
    [UncaughtPromiseError, ClientErrorDialog],
    [ThirdPartyScriptError, NetworkErrorDialog],
]);

/**
 * Handles the errors based on the very general error categories emitted by the
 * error service. Notice how we do not look at the original error at all.
 *
 * @param {OdooEnv} env
 * @param {UncaughError} error
 * @returns {boolean}
 */
export function defaultHandler(env, error) {
    const dialog = useService("dialog");
    const DialogComponent = defaultDialogs.get(error.constructor) || ErrorDialog;
    dialog.add(DialogComponent, {
        traceback: error.traceback,
        message: error.message,
        name: error.name,
        serverHost: error.event?.target?.location.host,
    });
    return true;
}
errorHandlerRegistry.add("defaultHandler", defaultHandler, { sequence: 100 });

// -----------------------------------------------------------------------------
// Frontend visitors errors
// -----------------------------------------------------------------------------

/**
 * We don't want to show tracebacks to non internal users. This handler swallows
 * all errors if we're not an internal user (except in debug or test mode).
 */
export function swallowAllVisitorErrors(env, error, originalError) {
    const debugMode = usePlugin(DebugModePlugin);
    if (!user.isInternalUser && !debugMode.isActive() && !session.test_mode) {
        return true;
    }
}

if (user.isInternalUser === undefined) {
    // Only warn about this while on the "frontend": the session info might
    // apparently not be present in all Odoo screens at the moment... TODO ?
    if (session.is_frontend) {
        console.warn(
            "isInternalUser information is required for this handler to work. It must be available in the page."
        );
    }
} else {
    registry
        .category("error_handlers")
        .add("swallowAllVisitorErrors", swallowAllVisitorErrors, { sequence: 0 });
}
