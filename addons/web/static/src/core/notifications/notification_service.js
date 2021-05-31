/** @odoo-module **/

import { browser } from "../browser/browser";
import { registry } from "../registry";

const { EventBus } = owl.core;

const AUTOCLOSE_DELAY = 4000;

export const notificationService = {
    start() {
        let notifId = 0;
        let notifications = [];
        const bus = new EventBus();

        function close(id, wait = 0) {
            function _close() {
                const index = notifications.findIndex((n) => n.id === id);
                if (index > -1) {
                    notifications.splice(index, 1);
                    bus.trigger("UPDATE", notifications);
                }
            }
            if (wait > 0) {
                browser.setTimeout(_close, wait);
            } else {
                _close();
            }
        }
        function create(message, options) {
            const notif = Object.assign({}, options, {
                id: ++notifId,
                message,
            });
            const sticky = notif.sticky;
            delete notif.sticky;
            notifications.push(notif);
            bus.trigger("UPDATE", notifications);
            if (!sticky) {
                browser.setTimeout(() => close(notif.id), AUTOCLOSE_DELAY);
            }
            return notif.id;
        }
        return { close, create, bus };
    },
};

registry.category("services").add("notification", notificationService);
