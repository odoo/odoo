import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";

import { markup } from "@odoo/owl";

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
            const message = markup`
                <a class='btn btn-link' href='${params.get_credits_url}' target='_blank'>
                    <i class='oi oi-arrow-right'></i>
                    ${_t("Buy more credits")}
                </a>`;
            notification.add(message, {
                title: params.title,
                type: "danger",
            });
        }
    },
};

registry.category("services").add("iapNotification", iapNotificationService);
