import { _t } from "@web/core/l10n/translation";
import { browser } from "../browser/browser";
import { ConnectionLostError, RPCError, rpc } from "../network/rpc";
import { registry } from "../registry";
import { session } from "@web/session";
import { user } from "@web/core/user";
import {
    ClientErrorDialog,
    ErrorDialog,
    NetworkErrorDialog,
    RPCErrorDialog,
} from "./error_dialogs";
import { UncaughtClientError, ThirdPartyScriptError, UncaughtPromiseError } from "./error_service";

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
                env.services.notification.add(notif.message || originalError.data.message, notif);
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

        env.services.dialog.add(ErrorComponent || RPCErrorDialog, {
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
// Lost connection errors
// -----------------------------------------------------------------------------

let connectionLostNotifRemove = null;
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
        if (connectionLostNotifRemove) {
            // notification already displayed (can occur if there were several
            // concurrent rpcs when the connection was lost)
            return true;
        }
        connectionLostNotifRemove = env.services.notification.add(
            _t("Connection lost. Trying to reconnect..."),
            { sticky: true }
        );
        let delay = 2000;
        browser.setTimeout(function checkConnection() {
            rpc("/web/webclient/version_info", {})
                .then(function () {
                    if (connectionLostNotifRemove) {
                        connectionLostNotifRemove();
                        connectionLostNotifRemove = null;
                    }
                    env.services.notification.add(_t("Connection restored. You are back online."), {
                        type: "info",
                    });
                })
                .catch(() => {
                    // exponential backoff, with some jitter
                    delay = delay * 1.5 + 500 * Math.random();
                    browser.setTimeout(checkConnection, delay);
                });
        }, delay);
        return true;
    }
}
errorHandlerRegistry.add("lostConnectionHandler", lostConnectionHandler, { sequence: 98 });

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
    const DialogComponent = defaultDialogs.get(error.constructor) || ErrorDialog;
    env.services.dialog.add(DialogComponent, {
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
    if (!user.isInternalUser && !odoo.debug && !session.test_mode) {
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
    registry.category("error_handlers").add("swallowAllVisitorErrors", swallowAllVisitorErrors, { sequence: 0 });
}
