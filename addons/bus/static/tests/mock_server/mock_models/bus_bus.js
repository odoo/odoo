/** @odoo-module */

import { models } from "@web/../tests/web_test_helpers";
import { registry } from "@web/core/registry";
import { patchWebsocketWorkerWithCleanup } from "../../mock_websocket";

/**
 * @param {BusBus} BusBus
 * @param {Object} message Message sent through the websocket to the
 * server.
 * @param {string} [message.event_name]
 * @param {any} [message.data]
 */
function performWebsocketRequest(BusBus, { event_name, data }) {
    /** @type {import("mock_models").IrWebSocket} */
    const IrWebSocket = BusBus.env["ir.websocket"];

    if (event_name === "update_presence") {
        const { inactivity_period, im_status_ids_by_model } = data;
        IrWebSocket._update_presence(inactivity_period, im_status_ids_by_model);
    } else if (event_name === "subscribe") {
        const { channels } = data;
        BusBus.channelsByUser[BusBus.env?.uid] = channels;
    }
    const callbackFn = registry.category("mock_server_websocket_callbacks").get(event_name, null);
    if (callbackFn) {
        callbackFn(data);
    }
}

export class BusBus extends models.Model {
    _name = "bus.bus";

    wsWorker;
    channelsByUser = {};
    lastBusNotificationId = 0;

    constructor() {
        super(...arguments);
        const self = this;
        this.wsWorker = patchWebsocketWorkerWithCleanup({
            _sendToServer(message) {
                performWebsocketRequest(self, message);
                super._sendToServer(message);
            },
        });
    }

    /**
     * @param {models.Model | string} channel
     * @param {string} notificationType
     * @param {any} message
     */
    _sendone(channel, notificationType, message) {
        this._sendmany([[channel, notificationType, message]]);
    }

    /** @param {[models.Model | string, string, any][]} notifications */
    _sendmany(notifications) {
        /** @type {import("mock_models").IrWebSocket} */
        const IrWebSocket = this.env["ir.websocket"];

        if (!notifications.length) {
            return;
        }
        const values = [];
        const authenticatedUserId =
            "res.users" in this.env && this.env.cookie.get("authenticated_user_sid");
        const channels = [
            ...IrWebSocket._build_bus_channel_list(),
            ...(this.channelsByUser[authenticatedUserId] || []),
        ];
        notifications = notifications.filter(([target]) =>
            channels.some((channel) => {
                if (typeof target === "string") {
                    return channel === target;
                }
                return channel?._name === target?.model && channel?.id === target?.id;
            })
        );
        if (notifications.length === 0) {
            return;
        }
        for (const notification of notifications) {
            const [type, payload] = notification.slice(1, notification.length);
            values.push({ id: ++this.lastBusNotificationId, message: { payload, type } });
        }
        this.wsWorker.broadcast("notification", values);
    }
}
