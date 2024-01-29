import { browser } from "../browser/browser";
import { registry } from "../registry";
import { NotificationContainer } from "./notification_container";

import { reactive } from "@odoo/owl";

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
    notificationContainer: NotificationContainer,

    start() {
        let notifId = 0;
        const notifications = reactive({});

        registry.category("main_components").add(
            this.notificationContainer.name,
            {
                Component: this.notificationContainer,
                props: { notifications },
            },
            { sequence: 100 }
        );

        /**
         * @param {string} message
         * @param {NotificationOptions} [options]
         */
        function add(message, options = {}) {
            const id = ++notifId;
            const closeFn = () => close(id);
            const props = Object.assign({}, options, { message, close: closeFn });
            const sticky = props.sticky;
            delete props.sticky;
            delete props.onClose;
            let closeTimeout;
            const refresh = sticky
                ? () => {}
                : () => {
                      closeTimeout = browser.setTimeout(closeFn, AUTOCLOSE_DELAY);
                  };
            const freeze = sticky
                ? () => {}
                : () => {
                      browser.clearTimeout(closeTimeout);
                  };
            props.refresh = refreshAll;
            props.freeze = freezeAll;
            const notification = {
                id,
                props,
                onClose: options.onClose,
                refresh,
                freeze,
            };
            notifications[id] = notification;
            if (!sticky) {
                closeTimeout = browser.setTimeout(closeFn, AUTOCLOSE_DELAY);
            }
            return closeFn;
        }

        function refreshAll() {
            for (const id in notifications) {
                notifications[id].refresh();
            }
        }

        function freezeAll() {
            for (const id in notifications) {
                notifications[id].freeze();
            }
        }

        function close(id) {
            if (notifications[id]) {
                const notification = notifications[id];
                if (notification.onClose) {
                    notification.onClose();
                }
                delete notifications[id];
            }
        }

        return { add };
    },
};

registry.category("services").add("notification", notificationService);
