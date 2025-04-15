/** @odoo-module **/

import { TEST_USER_IDS } from "@bus/../tests/helpers/test_constants";
import { patchWebsocketWorkerWithCleanup } from "@bus/../tests/helpers/mock_websocket";

import { patch } from "@web/core/utils/patch";
import { MockServer } from "@web/../tests/helpers/mock_server";
import { registry } from "@web/core/registry";

QUnit.testDone(() => {
    const callbackRegistry = registry.category("mock_server_websocket_callbacks");
    callbackRegistry.getEntries().map(([key]) => callbackRegistry.remove(key));
});

patch(MockServer.prototype, {
    init() {
        super.init(...arguments);
        Object.assign(this, TEST_USER_IDS);
        const self = this;
        this.notificationQueue = [];
        this.websocketWorker = patchWebsocketWorkerWithCleanup({
            _sendToServer(message) {
                self._performWebsocketRequest(message);
                super._sendToServer(message);
            },
        });
        this.lastBusNotificationId = 0;
        this.channelsByUser = {};
        for (const modelName in this.models) {
            const records = Array.isArray(this.models[modelName].records)
                ? this.models[modelName].records
                : [];
            for (const record of records) {
                Object.defineProperty(record, "__model", { value: modelName });
            }
        }
    },

    mockCreate(modelName, valsList, kwargs = {}) {
        const result = super.mockCreate(modelName, valsList, kwargs);
        const returnArrayOfIds = Array.isArray(result);
        const recordIds = Array.isArray(result) ? result : [result];
        for (const recordId of recordIds) {
            const record = this.models[modelName].records.find((r) => r.id === recordId);
            Object.defineProperty(record, "__model", { value: modelName });
        }
        return returnArrayOfIds ? recordIds : recordIds[0];
    },

    mockSearchRead(modelName, domain, kwargs = {}) {
        const records = super.mockSearchRead(modelName, domain, kwargs);
        for (const record of records) {
            Object.defineProperty(record, "__model", { value: modelName });
        }
        return records;
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
        if (event_name === "update_presence") {
            const { inactivity_period, im_status_ids_by_model } = data;
            this._mockIrWebsocket__updatePresence(inactivity_period, im_status_ids_by_model);
        } else if (event_name === "subscribe") {
            const { channels } = data;
            this.channelsByUser[this.pyEnv?.currentUser] = this.pyEnv
                ? this._mockIrWebsocket__buildBusChannelList(channels)
                : channels;
        }
        const callbackFn = registry
            .category("mock_server_websocket_callbacks")
            .get(event_name, null);
        if (callbackFn) {
            callbackFn(data);
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
        const authenticatedUserId =
            "res.users" in this.models
                ? this.pyEnv.cookie.get("authenticated_user_sid")
                : undefined;
        const authenticatedUser = authenticatedUserId
            ? this.pyEnv["res.users"].searchRead([["id", "=", authenticatedUserId]], {
                  context: { active_test: false },
              })[0]
            : null;
        const channels =
            this.channelsByUser[authenticatedUser] ?? this._mockIrWebsocket__buildBusChannelList();
        notifications = notifications.filter(([target]) =>
            channels.some((channel) => {
                if (typeof target === "string") {
                    return channel === target;
                }
                if (Array.isArray(channel) !== Array.isArray(target)) {
                    return false;
                }
                if (Array.isArray(channel)) {
                    const { __model: cModel, id: cId } = channel[0];
                    const { __model: tModel, id: tId } = target[0];
                    return cModel === tModel && cId === tId && channel[1] === target[1];
                }
                return channel?.__model === target.__model && channel?.id === target?.id;
            })
        );
        if (notifications.length === 0) {
            return;
        }
        for (const notification of notifications) {
            const [type, payload] = notification.slice(1, notification.length);
            values.push({ id: ++this.lastBusNotificationId, message: { payload, type } });
        }
        this.notificationQueue.push(...values);
        if (this.notificationQueue.length === values.length) {
            this._planNotificationSending();
        }
    },

    /**
     * Helper to send the pending notifications to the client. This method is
     * push to the micro task queue to simulate server-side batching of
     * notifications.
     */
    _planNotificationSending() {
        queueMicrotask(() => {
            if (this.debug) {
                console.group("%c[BUS]", "color: #c6e; font-weight: bold;");
                for (const { message } of this.notificationQueue) {
                    console.log(message.type, message.payload);
                }
                console.groupEnd();
            }
            this.websocketWorker.broadcast("notification", this.notificationQueue);
            this.notificationQueue = [];
        });
    },
    /**
     * Simulate the lost of the connection by simulating a closeEvent on
     * the worker websocket.
     *
     * @param {number} closeCode the code to close the connection with.
     */
    _simulateConnectionLost(closeCode) {
        this.websocketWorker.websocket.close(closeCode);
    },
});
