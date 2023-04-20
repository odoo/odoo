/* @odoo-module */

import { registry } from "@web/core/registry";

export const simpleNotificationService = {
    dependencies: ["bus_service", "notification"],
    start(env, { bus_service, notification: notificationService }) {
        bus_service.addEventListener("notification", ({ detail: notifications }) => {
            for (const { payload, type } of notifications) {
                if (type === "simple_notification") {
                    notificationService.add(payload.message, {
                        sticky: payload.sticky,
                        title: payload.title,
                        type: payload.type,
                    });
                }
            }
        });
        bus_service.start();
    },
};

registry.category("services").add("simple_notification", simpleNotificationService);
