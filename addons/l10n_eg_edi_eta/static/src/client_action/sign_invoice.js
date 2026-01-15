import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { registry } from "@web/core/registry";
import { _t } from "@web/core/l10n/translation";

async function actionGetDrive(env, action, type) {
    const { drive_id, sign_host: host } = action.params;
    const { orm, http, dialog, action: actionService } = env.services;

    let route = host;
    let key, method;
    if (type === "certificate") {
        route += "/hw_l10n_eg_eta/certificate";
        method = "set_certificate";
        key = "certificate";
    } else if (type === "sign") {
        route += "/hw_l10n_eg_eta/sign";
        method = "set_signature_data";
        key = "invoices";
    }

    let result;
    try {
        result = await http.post(route, action.params);
    } catch {
        dialog.add(AlertDialog, {
            body: _t("Error trying to connect to the middleware. Is the middleware running?"),
        });
        return;
    }

    if (result.error) {
        const typeToErrorMessage = {
            no_pykcs11: _t(
                "Missing library - Please make sure that PyKCS11 is correctly installed on the local proxy server"
            ),
            missing_dll: _t(
                "Missing Dependency - If you are using Windows, make sure eps2003csp11.dll is correctly installed. You can download it here: https://www.egypttrust.com/en/downloads/other-drivers. If you are using Linux or macOS, please install OpenSC"
            ),
            no_drive: _t("No drive found - Make sure the thumb drive is correctly inserted"),
            multiple_drive: _t(
                "Multiple drive detected - Only one secure thumb drive can be inserted at the same time"
            ),
            system_unsupported: _t("System not supported"),
            unauthorized: _t("Unauthorized"),
        };
        dialog.add(AlertDialog, {
            body: typeToErrorMessage[result.error] || _t("Unexpected error: “%s”", result.error),
        });
    } else if (result[key]) {
        await orm.call("l10n_eg_edi.thumb.drive", method, [[drive_id], result[key]]).catch(() => {
            dialog.add(AlertDialog, {
                body: _t("Error trying to connect to Odoo. Check your internet connection"),
            });
        });
        actionService.doAction({
            type: "ir.actions.client",
            tag: "reload",
        });
    } else {
        dialog.add(AlertDialog, {
            body: _t("An unexpected error has occurred"),
        });
    }
}

registry
    .category("actions")
    .add("action_get_drive_certificate", (env, action) =>
        actionGetDrive(env, action, "certificate")
    );
registry
    .category("actions")
    .add("action_post_sign_invoice", (env, action) => actionGetDrive(env, action, "sign"));
