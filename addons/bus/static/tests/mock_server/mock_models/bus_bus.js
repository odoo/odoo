import { getWebSocketWorker } from "@bus/../tests/mock_websocket";
import { models } from "@web/../tests/web_test_helpers";

export class BusBus extends models.Model {
    _name = "bus.bus";

    /** @type {Record<number, string[]>} */
    channelsByUser = {};
    lastBusNotificationId = 0;

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
            "res.users" in this.env
                ? this.env.cookie.get("authenticated_user_sid") ?? this.env.uid
                : null;
        const channels = [
            ...IrWebSocket._build_bus_channel_list(this.channelsByUser[authenticatedUserId] || []),
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
            values.push({
                id: ++this.lastBusNotificationId,
                message: { payload: JSON.parse(JSON.stringify(payload)), type },
            });
        }
        getWebSocketWorker().broadcast("BUS:NOTIFICATION", values);
    }

    /**
     * Close the current websocket with the given reason and code.
     *
     * @param {number} closeCode the code to close the connection with.
     * @param {string} [reason] the reason to close the connection with.
     */
    _simulateDisconnection(closeCode, reason) {
        getWebSocketWorker().websocket.close(closeCode, reason);
    }
}
