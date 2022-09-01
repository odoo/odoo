/** @odoo-module **/

import { TEST_USER_IDS } from "@bus/../tests/helpers/test_constants";
import { patchWebsocketWorkerWithCleanup } from '@bus/../tests/helpers/mock_websocket';

import { patch } from "@web/core/utils/patch";
import { ConnectionLostError } from "@web/core/network/rpc_service";
import { MockServer } from "@web/../tests/helpers/mock_server";
import { makeDeferred } from "@web/../tests/helpers/utils";

patch(MockServer.prototype, 'bus', {
    init() {
        this._super(...arguments);
        Object.assign(this, TEST_USER_IDS);
        this.websocketWorker = patchWebsocketWorkerWithCleanup();
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
            if (this.hasLostConnection) {
                longpollingPromise.reject(new ConnectionLostError());
                this.hasLostConnection = false;
            } else if (this.notificationsToBeResolved.length) {
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
            values.push({ payload, type });
            if (this.debug) {
                console.log("%c[bus]", "color: #c6e; font-weight: bold;", type, payload);
            }
        }
        this.websocketWorker.broadcast('notification', values);

    },

    /**
     * Simulate the lost of the connection by simulating a closeEvent on
     * the worker websocket.
     *
     * @param {number} clodeCode the code to close the connection with.
     */
    _simulateConnectionLost(closeCode) {
        this.websocketWorker.websocket.dispatchEvent(new CloseEvent('close', {
            code: closeCode,
        }));
    },
});
