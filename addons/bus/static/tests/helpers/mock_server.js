/** @odoo-module **/

import { TEST_USER_IDS } from "@bus/../tests/helpers/test_constants";
import { patchWebsocketWorkerWithCleanup } from '@bus/../tests/helpers/mock_websocket';

import { patch } from "@web/core/utils/patch";
import { MockServer } from "@web/../tests/helpers/mock_server";

patch(MockServer.prototype, 'bus', {
    init() {
        this._super(...arguments);
        Object.assign(this, TEST_USER_IDS);
        const self = this;
        this.websocketWorker = patchWebsocketWorkerWithCleanup({
            _sendToServer(message) {
                self._performWebsocketRequest(message);
                this._super(message);
            },
        });
        this.pendingLongpollingPromise = null;
        this.notificationsToBeResolved = [];
        this.lastBusNotificationId = 0;
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @param {Object} message Message sent through the websocket to the
     * server.
     * @param {string} [message.event_name]
     * @param {any} [message.data]
     */
    _performWebsocketRequest({ event_name, data }) {
        if (event_name === 'update_presence') {
            const { inactivity_period, im_status_ids_by_model } = data;
            this._mockIrWebsocket__updatePresence(inactivity_period, im_status_ids_by_model);
        }
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
        if (!notifications.length) {
            return;
        }
        const values = [];
        for (const notification of notifications) {
            const [type, payload] = notification.slice(1, notification.length);
            values.push({ id: this.lastBusNotificationId++, message: { payload, type }});
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
