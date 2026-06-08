import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";

export const iapNotificationService = {
    dependencies: ["bus_service", "notification"],

    start(env, { bus_service, notification }) {
        bus_service.subscribe("iap_notification", (params) => {
            if (params.type == "no_credit") {
                displayCreditErrorNotification(params);
            } else {
                displayNotification(params);
            }
        });
        bus_service.start();

        function displayNotification(params) {
            notification.add(params.message, {
                title: params.title,
                type: params.type,
            });
        }

        function displayCreditErrorNotification(params) {
            notification.add(params.title, {
                type: "danger",
                buttons: [
                    {
                        name: _t("Buy"),
                        onClick: () => {
                            window.open(params.get_credits_url, '_blank');
                        }
                    }
                ]
            });
        }
    },
};

registry.category("services").add("iapNotification", iapNotificationService);
