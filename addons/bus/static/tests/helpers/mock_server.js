/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { MockServer } from "@web/../tests/helpers/mock_server";
import { makeDeferred } from "@web/../tests/helpers/utils";

patch(MockServer.prototype, 'bus', {
    init() {
        this._super(...arguments);
        this.pendingLongpollingPromise = null;
        this.notificationsToBeResolved = [];
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    async _performRPC(route, args) {
        if (route === '/longpolling/poll') {
            const longpollingPromise = makeDeferred();
            if (this.notificationsToBeResolved.length) {
                longpollingPromise.resolve(this.notificationsToBeResolved);
                this.notificationsToBeResolved = [];
            } else {
                this.pendingLongpollingPromise = longpollingPromise;
            }
            return longpollingPromise;
        }
        return this._super(route, args);
    },
    /**
     * Simulates `_sendone` on `bus.bus`.
     *
     * @param {string} channel
     * @param {string} notificationType
     * @param {any} message
     */
    _mockBusBus__sendone(channel, notificationType, message) {
       this._mockBusBus__sendmany([[channel, notificationType, message]]);
    },
    /**
     * Simulates `_sendmany` on `bus.bus`.
     *
     * @param {Array} notifications
     */
    _mockBusBus__sendmany(notifications) {
        const values = [];
        for (const notification of notifications) {
            const [type, payload] = notification.slice(1, notification.length);
            values.push({ message: { payload, type } });
        }
        if (this.pendingLongpollingPromise) {
            this.pendingLongpollingPromise.resolve(values);
            this.pendingLongpollingPromise = null;
        } else {
            this.notificationsToBeResolved.push(...values);
        }
    },
});
