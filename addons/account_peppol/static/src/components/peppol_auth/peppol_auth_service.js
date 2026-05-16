import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";


export const peppolAuthService = {
    dependencies: ["bus_service", "action"],

    start(env, { bus_service, action }) {
        bus_service.subscribe("peppol_auth_channel", (payload) => {
            const success = payload["auth_result"] === "success";
            const successNotificationVals = {
                "title": _t("Authentication successful"),
                "type": "success",
            };
            const failureNotificationVals = {
                "title": _t("Authentication failed"),
                "type": "danger",
                "message": payload["error_message"],
            };
            action.doAction({
                type: "ir.actions.client",
                tag: "display_notification",
                params: {
                    ...(success ? successNotificationVals : failureNotificationVals),
                    "next": {type: "ir.actions.act_window_close"},  // close the wizard
                },
            });
        });
    }
};

registry.category("services").add("peppol_auth_service", peppolAuthService);
