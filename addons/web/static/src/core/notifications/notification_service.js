/** @odoo-module **/

import { browser } from "../browser/browser";
import { registry } from "../registry";
import { NotificationContainer } from "./notification_container";

const { EventBus } = owl.core;

const AUTOCLOSE_DELAY = 4000;

/**
 * @typedef {Object} NotificationButton
 * @property {string} name
 * @property {string} [icon]
 * @property {boolean} [primary=false]
 * @property {function(): void} onClick
 *
 * @typedef {Object} NotificationOptions
 * @property {string} [title]
 * @property {"warning" | "danger" | "success" | "info"} [type]
 * @property {boolean} [sticky=false]
 * @property {string} [className]
 * @property {function(): void} [onClose]
 * @property {NotificationButton[]} [buttons]
 */

export const notificationService = {
    start() {
        let notifId = 0;
        let notifications = [];
        const bus = new EventBus();

        registry.category("main_components").add("NotificationContainer", {
            Component: NotificationContainer,
            props: { bus, notifications },
        });

        /**
         * @param {string} message
         * @param {NotificationOptions} [options]
         */
        function add(message, options = {}) {
            const id = ++notifId;
            const props = Object.assign({}, options, { message });
            const sticky = props.sticky;
            delete props.sticky;
            const closeFn = () => close(id);
            const notification = {
                id,
                props,
                close: closeFn,
            };
            notifications.push(notification);
            bus.trigger("UPDATE");
            if (!sticky) {
                browser.setTimeout(closeFn, AUTOCLOSE_DELAY);
            }
            return closeFn;
        }

        function close(id) {
            const index = notifications.findIndex((n) => n.id === id);
            if (index > -1) {
                notifications.splice(index, 1);
                bus.trigger("UPDATE");
            }
        }

        return { add };
    },
};

registry.category("services").add("notification", notificationService);
