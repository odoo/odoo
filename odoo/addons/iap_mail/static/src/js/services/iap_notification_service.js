/** @odoo-module **/

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
            // ℹ️ `_t` can only be inlined directly inside JS template literals
            // after Babel has been updated to version 2.12.
            const translatedText = _t("Buy more credits");
            const message = markup(`
            <a class='btn btn-link' href='${params.get_credits_url}' target='_blank'>
                <i class='oi oi-arrow-right'></i>
                ${translatedText}
            </a>`);
            notification.add(message, {
                title: params.title,
                type: 'danger',
            });
        }
    }
};

registry.category("services").add("iapNotification", iapNotificationService);
