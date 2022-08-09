/** @odoo-module **/

import { TEST_USER_IDS } from "@bus/../tests/helpers/test_constants";
import { getPyEnv } from "@bus/../tests/helpers/mock_python_environment";

import { patch } from "@web/core/utils/patch";
import { MockServer } from "@web/../tests/helpers/mock_server";
import { makeDeferred } from "@web/../tests/helpers/utils";

patch(MockServer.prototype, 'bus', {
    init() {
        this._super(...arguments);
        Object.assign(this, TEST_USER_IDS);
        this.pendingLongpollingPromise = null;
        this.notificationsToBeResolved = [];
    },

    /**
     * @override
     */
    async setup() {
        this.pyEnv = await getPyEnv();
        // link the pyEnv to the actual mockServer after execution of
        // createWebClient.
        this.pyEnv.mockServer = this;
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
