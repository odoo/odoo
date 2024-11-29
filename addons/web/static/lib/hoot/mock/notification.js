/** @odoo-module */

import { makePublicListeners } from "../hoot_utils";
import { currentPermissions } from "./navigator";

//-----------------------------------------------------------------------------
// Global
//-----------------------------------------------------------------------------

const { Event, EventTarget, Promise, Set } = globalThis;

//-----------------------------------------------------------------------------
// Internal
//-----------------------------------------------------------------------------

/** @type {Set<MockNotification>} */
const notifications = new Set();

//-----------------------------------------------------------------------------
// Exports
//-----------------------------------------------------------------------------

/**
 * Returns the list of notifications that have been created since the last call
 * to this function, consuming it in the process.
 *
 * @returns {MockNotification[]}
 */
export function flushNotifications() {
    const result = [...notifications];
    notifications.clear();
    return result;
}

export class MockNotification extends EventTarget {
    /** @type {NotificationPermission} */
    static get permission() {
        return currentPermissions.notifications.state;
    }

    /** @type {NotificationPermission} */
    get permission() {
        return this.constructor.permission;
    }

    /**
     * @param {string} title
     * @param {NotificationOptions} [options]
     */
    constructor(title, options) {
        super(...arguments);

        makePublicListeners(this, ["click", "close", "error", "show"]);

        this.title = title;
        this.options = options;

        if (this.permission === "granted") {
            notifications.push(this);
        }
    }

    static requestPermission() {
        return Promise.resolve(this.permission);
    }

    click() {
        this.dispatchEvent(new Event("click"));
    }

    close() {
        notifications.delete(this);
        this.dispatchEvent(new Event("close"));
    }

    show() {
        this.dispatchEvent(new Event("show"));
    }
}
