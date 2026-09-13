// @ts-check
/** @odoo-module native */

import { reactive } from "@odoo/owl";
import { makeLogger } from "@web/core/debug/debug_logger";
import { reportUncaught } from "@web/core/errors/error_utils";
import { registry } from "@web/core/registry";
import { mainComponentEntry } from "@web/ui/main_components_container";

import { NotificationContainer } from "./notification_container.js";
/**
 * @typedef {Object} NotificationButton
 * @property {string} name
 * @property {string} [icon]
 * @property {boolean} [primary=false]
 * @property {function(): void} onClick
 * @typedef {Object} NotificationOptions
 * @property {string} [title]
 * @property {number} [autocloseDelay=4000]
 * @property {"warning" | "danger" | "success" | "info"} [type]
 * @property {boolean} [sticky=false]
 * @property {string} [className]
 * @property {function(): void} [onClose]
 * @property {NotificationButton[]} [buttons]
 */

const SERVICE_OPTIONS = new Set(["onClose"]);

const SERVICE_OWNED_PROPS = new Set(["close", "message"]);

const log = makeLogger("web.ui.notification");

class NotificationService {
    /**
     * @param {any} notificationContainer
     * @param {string} notificationContainerKey
     */
    constructor(notificationContainer, notificationContainerKey) {
        this.notifId = 0;
        const notificationProps = notificationContainer.notificationComponent?.props;
        if (!notificationProps) {
            throw new Error(
                `${notificationContainer.name}.notificationComponent must declare the component ` +
                    `rendering each notification, so that the options this service accepts are the ` +
                    `props that component validates.`,
            );
        }
        /** @type {Set<string>} */
        this.declaredProps = new Set(Object.keys(notificationProps));
        this.notifications = reactive(
            /** @type {Record<number, { id: number, props: Record<string, any>, onClose?: () => void }>} */ ({}),
        );

        registry
            .category("main_components")
            .add(notificationContainerKey, mainComponentEntry(notificationContainer), {
                sequence: 100,
            });
    }

    /**
     * @param {string | { toString(): string }} message
     * @param {NotificationOptions} [options]
     * @returns {() => void}
     */
    add(message, options = {}) {
        const id = ++this.notifId;
        log.lifecycle("add", () => ({
            id,
            type: options.type,
            sticky: Boolean(options.sticky),
            title: options.title,
            message,
        }));
        const closeFn = () => this._close(id);
        const props = /** @type {Record<string, any>} */ ({
            message,
            close: closeFn,
        });
        for (const [key, value] of Object.entries(options)) {
            if (SERVICE_OPTIONS.has(key)) {
                continue;
            }
            if (SERVICE_OWNED_PROPS.has(key)) {
                if (odoo.debug) {
                    console.warn(
                        `[notification] option "${key}" is set by the service; it will be ignored.`,
                    );
                }
                continue;
            }
            if (this.declaredProps.has(key)) {
                props[key] = value;
            } else if (odoo.debug) {
                console.warn(
                    `[notification] unknown option "${key}"; it will be ignored.`,
                );
            }
        }
        const notification = {
            id,
            props,
            onClose: options.onClose,
        };
        this.notifications[id] = notification;
        return closeFn;
    }

    /** @param {number} id */
    _close(id) {
        log.lifecycle("close", () => ({ id, known: Boolean(this.notifications[id]) }));
        if (this.notifications[id]) {
            const notification = this.notifications[id];
            // Release ownership before calling user code, which may close again.
            delete this.notifications[id];
            try {
                if (notification.onClose) {
                    notification.onClose();
                }
            } catch (error) {
                reportUncaught(error);
            }
        }
    }

    destroy() {
        for (const id of Object.keys(this.notifications)) {
            this._close(Number(id));
        }
    }
}

export const notificationService = {
    notificationContainer: NotificationContainer,
    notificationContainerKey: "NotificationContainer",

    /** @returns {NotificationService} */
    start() {
        return new NotificationService(
            this.notificationContainer,
            this.notificationContainerKey,
        );
    },
};

registry.category("services").add("notification", notificationService);
