/** @odoo-module **/

import { Markup } from 'web.utils';
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";

export const iapNotificationService = {
    dependencies: ["bus_service", "notification"],

    start(env, { bus_service, notification }) {
        bus_service.subscribe("iap_notification", (payload) => {
            if (payload.error_type == "success") {
                displaySuccessIapNotification(payload);
            } else if (payload.error_type == "danger") {
                displayFailureIapNotification(payload);
            }
        });
        bus_service.start();

        /**
         * Displays the IAP success notification on user's screen
         */
        function displaySuccessIapNotification(notif) {
            notification.add(notif.title, {
                type: notif.error_type,
            });
        }

        /**
         * Displays the IAP failure notification on user's screen
         */
        function displayFailureIapNotification(notif) {
            // ℹ️ `_t` can only be inlined directly inside JS template literals
            // after Babel has been updated to version 2.12.
            const translatedText = _t("Buy more credits");
            const message = Markup`<a class='btn btn-link' href='${notif.url}' target='_blank' ><i class='oi oi-arrow-right'></i> ${translatedText}</a>`;
            notification.add(message, {
                type: notif.error_type,
                title: notif.title
            });
        }
    }
};

registry.category("services").add("iapNotification", iapNotificationService);
