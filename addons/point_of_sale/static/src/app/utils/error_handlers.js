import { registry } from "@web/core/registry";
import { odooExceptionTitleMap, ErrorDialog } from "@web/core/errors/error_dialogs";
import { ConnectionLostError, RPCError } from "@web/core/network/rpc";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";

export function handleRPCError(error, dialog) {
    const { data } = error;
    if (odooExceptionTitleMap.has(error.exceptionName)) {
        const title = odooExceptionTitleMap.get(error.exceptionName).toString();
        dialog.add(AlertDialog, { title, body: data.message });
    } else {
        if (odoo.debug === "assets") {
            dialog.add(ErrorDialog, {
                traceback: data.message + "\n" + data.debug + "\n",
            });
        } else {
            dialog.add(AlertDialog, {
                title: _t("Odoo Server Error"),
                body: data.message,
            });
        }
    }
}

function rpcErrorHandler(env, error, originalError) {
    const dialog = useService("dialog");
    if (originalError instanceof RPCError) {
        handleRPCError(originalError, dialog);
        return true;
    }
}
registry.category("error_handlers").add("pos-rpcErrorHandler", rpcErrorHandler);

export function offlineErrorHandler(env, error, originalError) {
    const pos = useService("pos");
    const dialog = useService("dialog");
    if (originalError instanceof ConnectionLostError) {
        if (!pos.data.network.warningTriggered) {
            dialog.add(AlertDialog, {
                title: _t("Connection Lost"),
                body: _t(
                    "Until the connection is reestablished, Odoo Point of Sale will operate with limited functionality."
                ),
                confirmLabel: _t("Continue with limited functionality"),
            });
            pos.data.network.warningTriggered = true;
        }

        return true;
    }
}
registry.category("error_handlers").add("pos-offlineErrorHandler", offlineErrorHandler);

function defaultErrorHandler(env, error, originalError) {
    const dialog = useService("dialog");
    if (error instanceof Error) {
        dialog.add(ErrorDialog, {
            traceback: error.traceback,
        });
    } else {
        dialog.add(AlertDialog, {
            title: _t("Unknown Error"),
            body: _t("Unable to show information about this error."),
            showReloadButton: true,
        });
    }
    return true;
}
registry
    .category("error_handlers")
    .add("pos-defaultErrorHandler", defaultErrorHandler, { sequence: 99 });
