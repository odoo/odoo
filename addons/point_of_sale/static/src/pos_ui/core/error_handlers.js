/** @odoo-module */

import {
    RPCError,
    ConnectionLostError,
    ConnectionAbortedError,
} from "@web/core/network/rpc_service";
import { odooExceptionTitleMap } from "@web/core/errors/error_dialogs";
import { registry } from "@web/core/registry";

import { ErrorPopup } from "@point_of_sale/js/Popups/ErrorPopup";
import { ErrorTracebackPopup } from "@point_of_sale/js/Popups/ErrorTracebackPopup";
import { OfflineErrorPopup } from "@point_of_sale/js/Popups/OfflineErrorPopup";

/** FIXME Docstring
 * This method is used to handle unexpected errors. It is registered to
 * the `error_handlers` service when this component is properly mounted.
 * See `onMounted` hook of the `ChromeAdapter` component.
 * @param {*} env
 * @param {UncaughtClientError | UncaughtPromiseError} error
 * @param {*} originalError
 * @returns {boolean}
 */

function rpcErrorHandler(env, error, originalError) {
    if (originalError instanceof RPCError) {
        const { message, data } = originalError;
        if (odooExceptionTitleMap.has(originalError.exceptionName)) {
            const title = odooExceptionTitleMap.get(originalError.exceptionName).toString();
            env.services.dialog.add(ErrorPopup, { title, body: data.message });
        } else {
            env.services.dialog.add(ErrorTracebackPopup, {
                title: message,
                body: data.message + "\n" + data.debug + "\n",
            });
        }
        return true;
    }
}
function connectionLostHandler(env, error, originalError) {
    if (originalError instanceof ConnectionLostError) {
        env.services.dialog.add(OfflineErrorPopup, {
            title: this.env._t("Connection is lost"),
            body: this.env._t("Check the internet connection then try again."),
        });
        return true;
    } else if (originalError instanceof ConnectionAbortedError) {
        env.services.dialog.add(OfflineErrorPopup, {
            title: this.env._t("Connection is aborted"),
            body: this.env._t("Check the internet connection then try again."),
        });
        return true;
    }
}
function defaultErrorHandler(env, error, originalError) {
    if (originalError instanceof Error) {
        // If `originalError` is a normal Error (such as TypeError),
        // the annotated traceback can be found from `error`.
        env.services.dialog.add(ErrorTracebackPopup, {
            // Hopefully the message is translated.
            title: `${originalError.name}: ${originalError.message}`,
            body: error.traceback,
        });
    } else {
        // Hey developer. It's your fault that the error reach here.
        // Please, throw an Error object in order to get stack trace of the error.
        // At least we can find the file that throws the error when you look
        // at the console.
        env.services.dialog.add(ErrorPopup, {
            title: this.env._t("Unknown Error"),
            body: this.env._t("Unable to show information about this error."),
        });
        console.error("Unknown error. Unable to show information about this error.", originalError);
    }
    return true;
}

registry
    .category("error_handlers")
    .add("rpc_error_handler", rpcErrorHandler)
    .add("connection_lost_handler", connectionLostHandler)
    .add("default_error_handler", defaultErrorHandler);
