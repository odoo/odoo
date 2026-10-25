import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";


export const peppolAuthService = {
    dependencies: ["bus_service", "action"],

    start(env, { bus_service, action }) {
        bus_service.subscribe("peppol_auth_channel", (payload) => {
            const notificationValsPerResult = {
                success: {
                    "title": _t("Authentication successful"),
                    "type": "success",
                },
                pending: {
                    "title": _t("Verification pending"),
                    "type": "success",
                    "message": _t("Your details are being verified. There is nothing else to do on your end: your Peppol registration will be finalized automatically."),
                },
                canceled: {
                    "title": _t("Authentication canceled"),
                    "type": "warning",
                },
                failure: {
                    "title": _t("Authentication failed"),
                    "type": "danger",
                    "message": payload["error_message"] || "",
                },
            };
            const notificationVals = notificationValsPerResult[payload["auth_result"]] || notificationValsPerResult.failure;
            action.doAction({
                type: "ir.actions.client",
                tag: "display_notification",
                params: {
                    ...notificationVals,
                    "next": {type: "ir.actions.act_window_close"},  // close the wizard
                },
            });
        });
    }
};

registry.category("services").add("peppol_auth_service", peppolAuthService);
