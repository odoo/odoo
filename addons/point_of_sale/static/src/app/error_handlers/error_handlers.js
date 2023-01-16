/** @odoo-module */

import { registry } from "@web/core/registry";
import { odooExceptionTitleMap } from "@web/core/errors/error_dialogs";
import { ConnectionLostError, RPCError } from "@web/core/network/rpc_service";
import { Gui, GuiNotReadyError } from "@point_of_sale/js/Gui";
import { ErrorPopup } from "@point_of_sale/js/Popups/ErrorPopup";
import { ErrorTracebackPopup } from "@point_of_sale/js/Popups/ErrorTracebackPopup";
import { OfflineErrorPopup } from "@point_of_sale/js/Popups/OfflineErrorPopup";

export function identifyError(error) {
    return error && error.legacy ? error.message : error;
}

function rpcErrorHandler(env, error, originalError) {
    error = identifyError(originalError);
    if (error instanceof RPCError) {
        const { message, data } = error;
        if (odooExceptionTitleMap.has(error.exceptionName)) {
            const title = odooExceptionTitleMap.get(error.exceptionName).toString();
            Gui.showPopup(ErrorPopup, { title, body: data.message });
        } else {
            Gui.showPopup(ErrorTracebackPopup, {
                title: message,
                body: data.message + "\n" + data.debug + "\n",
            });
        }
        return true;
    }
}
registry.category("error_handlers").add("rpcErrorHandler", rpcErrorHandler);

function offlineErrorHandler(env, error, originalError) {
    error = identifyError(originalError);
    if (error instanceof ConnectionLostError) {
        Gui.showPopup(OfflineErrorPopup, {
            title: env._t("Couldn't connect to the server"),
            body: env._t(
                "The operation couldn't be completed because you are offline. Check your internet connection and try again."
            ),
        });
        return true;
    }
}
registry.category("error_handlers").add("offlineErrorHandler", offlineErrorHandler);

function defaultErrorHandler(env, error, originalError) {
    error = identifyError(originalError);
    if (error instanceof Error) {
        Gui.showPopup(ErrorTracebackPopup, {
            title: `${error.name}: ${error.message}`,
            body: error.traceback,
        });
    } else {
        Gui.showPopup(ErrorPopup, {
            title: env._t("Unknown Error"),
            body: env._t("Unable to show information about this error."),
        });
    }
    return true;
}
registry
    .category("error_handlers")
    .add("defaultErrorHandler", defaultErrorHandler, { sequence: 99 });

function guiNotReadyHandler(env, error, originalError) {
    error = identifyError(originalError);
    if (error instanceof GuiNotReadyError) {
        console.error(originalError);
        return true;
    }
}
registry.category("error_handlers").add("guiNotReadyHandler", guiNotReadyHandler);
