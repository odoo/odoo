/* @odoo-module */

import {registry} from "@web/core/registry";
import {browser} from "@web/core/browser/browser";

export const simpleTaggedNotificationService = {
    dependencies: ["bus_service", "notification"],
    start(env, {bus_service, notification: notificationService}) {
        bus_service.subscribe("simple_tagged_notification", ({tag, ttl, message, sticky, title, type}) => {
            const notificationKey = `simple_tagged_notification.${tag}`;

            function addNotification() {
                const hour = 60 * 60 * 1000;
                ttl = ttl || hour;
                let expiry = Date.now() + ttl;
                browser.localStorage.setItem(notificationKey, JSON.stringify({expiry}));
                function onClose() {
                    browser.localStorage.removeItem(notificationKey);
                }
                notificationService.add(message, {sticky, title, type, onClose});
            }

            const item = browser.localStorage.getItem(notificationKey);
            if (item === null || Date.now() > JSON.parse(item).expiry) {
                addNotification();
            }
        });
        bus_service.start();
    },
};

registry.category("services").add("simple_tagged_notification", simpleTaggedNotificationService);
