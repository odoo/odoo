/** @odoo-module */

import { MockServer, getServerWebSockets, models } from "@web/../tests/web_test_helpers";

export class BusBus extends models.Model {
    _name = "bus.bus";

    channelsByUser = {};
    lastBusNotificationId = 1;

    /**
     * Simulates `_sendone` on `bus.bus`.
     *
     * @param {models.Model | string} channel
     * @param {string} notificationType
     * @param {any} message
     */
    _sendone(channel, notificationType, message) {
        this._sendmany([[channel, notificationType, message]]);
    }

    /**
     * Simulates `_sendmany` on `bus.bus`.
     *
     * @param {[models.Model | string, string, any][]} notifications
     */
    _sendmany(notifications) {
        if (!notifications.length) {
            return;
        }
        const values = [];

        const authenticatedUserId =
            "res.users" in MockServer.models && this.env.cookie.get("authenticated_user_sid");
        const authenticatedUser = authenticatedUserId
            ? this.env["res.users"].search_read([["id", "=", authenticatedUserId]], {
                  context: { active_test: false },
              })[0]
            : null;
        const channels = [
            ...this.env["ir.websocket"]._buildBusChannelList(),
            ...(this.channelsByUser[authenticatedUser] || []),
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
            values.push({ id: this.lastBusNotificationId++, message: { payload, type } });
        }

        for (const ws of getServerWebSockets()) {
            ws.send(JSON.stringify(values));
        }
    }
}
