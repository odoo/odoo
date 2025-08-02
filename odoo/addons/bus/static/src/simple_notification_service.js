/* @odoo-module */

import { registry } from "@web/core/registry";

export const simpleNotificationService = {
    dependencies: ["bus_service", "notification"],
    start(env, { bus_service, notification: notificationService }) {
        bus_service.subscribe("simple_notification", ({ message, sticky, title, type }) => {
            notificationService.add(message, { sticky, title, type });
        });
        bus_service.start();
    },
};

registry.category("services").add("simple_notification", simpleNotificationService);
