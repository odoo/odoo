/** @odoo-module **/

import { browser } from "../browser/browser";
import { registry } from "../registry";
import { NotificationContainer } from "./notification_container";

const { EventBus } = owl.core;

const AUTOCLOSE_DELAY = 4000;

export const notificationService = {
    start() {
        let notifId = 0;
        const bus = new EventBus();

        registry.category("main_components").add("NotificationContainer", {
            Component: NotificationContainer,
            props: { bus },
        });

        return {
            bus,
            /**
             * @param {string} message
             * @param {Object} [options]
             * @param {{
             *      name: string;
             *      icon?: string;
             *      primary?: boolean;
             *      onClick: () => void
             * }[]} [options.buttons]
             * @param {string} [options.className]
             * @param {boolean} [options.messageIsHtml]
             * @param {() => void} [options.onClose]
             * @param {boolean} [options.sticky]
             * @param {string} [options.title]
             * @param {"warning" | "danger" | "success" | "info"} [options.type]
             */
            add(message, options = {}) {
                const notif = Object.assign({}, options, {
                    id: ++notifId,
                    message,
                });
                const sticky = notif.sticky;
                delete notif.sticky;
                bus.trigger("ADD", notif);
                if (!sticky) {
                    browser.setTimeout(() => bus.trigger("REMOVE", notif.id), AUTOCLOSE_DELAY);
                }
                return () => {
                    bus.trigger("REMOVE", notif.id);
                };
            },
        };
    },
};

registry.category("services").add("notification", notificationService);
