/** @odoo-module */

import { registry } from "@web/core/registry";
import { odooExceptionTitleMap } from "@web/core/errors/error_dialogs";
import { ConnectionLostError, RPCError } from "@web/core/network/rpc_service";
import { Gui } from "@point_of_sale/js/Gui";
import { _t, _lt } from "@web/core/l10n/translation";

export function identifyError(error) {
    return error && error.legacy ? error.message : error;
}

function rpcErrorHandler(env, error, originalError) {
    error = identifyError(originalError);
    if (error instanceof RPCError) {
        const { message, data } = error;
        if (odooExceptionTitleMap.has(error.exceptionName)) {
            const title = odooExceptionTitleMap.get(error.exceptionName).toString();
            Gui.showPopup("ErrorPopup", { title, body: data.message });
        } else {
            Gui.showPopup("ErrorTracebackPopup", {
                title: message,
                body: data.message + "\n" + data.debug + "\n",
            });
        }
        return true;
    }
}
registry.category("error_handlers").add("rpcErrorHandler", rpcErrorHandler);

// TODO: consider only showing a notification instead of an error popup in flows that can work offline
export const urlToMessage = {
    "/web/dataset/call_kw/pos.order/create_from_ui": _lt(
        "The order couldn't be sent to the server because you are offline"
    ),
};
function offlineErrorHandler(env, error, originalError) {
    error = identifyError(originalError);
    if (error instanceof ConnectionLostError) {
        const body =
            urlToMessage[error.url] ||
            _t(
                "The operation couldn't be completed because you are offline. Check your internet connection and try again."
            );
        Gui.showPopup("OfflineErrorPopup", {
            title: _t("Couldn't connect to the server"),
            body,
        });
        return true;
    }
}
registry.category("error_handlers").add("offlineErrorHandler", offlineErrorHandler);

function defaultErrorHandler(env, error, originalError) {
    error = identifyError(originalError);
    if (error instanceof Error) {
        Gui.showPopup("ErrorTracebackPopup", {
            title: `${error.name}: ${error.message}`,
            body: error.traceback,
        });
    } else {
        Gui.showPopup("ErrorPopup", {
            title: _t("Unknown Error"),
            body: _t("Unable to show information about this error."),
        });
    }
    return true;
}
registry
    .category("error_handlers")
    .add("defaultErrorHandler", defaultErrorHandler, { sequence: 99 });
