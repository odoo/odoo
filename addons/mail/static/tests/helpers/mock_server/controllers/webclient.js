/* @odoo-module */

import "@mail/../tests/helpers/mock_server/controllers/discuss"; // ensure super is loaded first

import { patch } from "@web/core/utils/patch";
import { MockServer } from "@web/../tests/helpers/mock_server";

patch(MockServer.prototype, {
    async _performRPC(route, args) {
        if (route === "/mail/action") {
            return this._mockRoute_ProcessRequest(args);
        }
        if (route === "/mail/data") {
            return this._mockRoute_ProcessRequest(args);
        }
        return super._performRPC(route, args);
    },
    _mockRoute_ProcessRequest(args) {
        const res = {};
        if (args.init_messaging) {
            const initMessaging =
                this._mockMailGuest__getGuestFromContext() && this.pyEnv.currentUser?._is_public()
                    ? this._mockMailGuest__initMessaging(args.context)
                    : this._mockResUsers_InitMessaging([this.pyEnv.currentUserId], args.context);
            this._addToRes(res, initMessaging);
        }
        if (args.failures && this.pyEnv.currentPartnerId) {
            const partner = this.getRecords(
                "res.partner",
                [["id", "=", this.pyEnv.currentPartnerId]],
                {
                    active_test: false,
                }
            )[0];
            const messages = this.getRecords("mail.message", [
                ["author_id", "=", partner.id],
                ["res_id", "!=", 0],
                ["model", "!=", false],
                ["message_type", "!=", "user_notification"],
            ]).filter((message) => {
                // Purpose is to simulate the following domain on mail.message:
                // ['notification_ids.notification_status', 'in', ['bounce', 'exception']],
                // But it's not supported by getRecords domain to follow a relation.
                const notifications = this.getRecords("mail.notification", [
                    ["mail_message_id", "=", message.id],
                    ["notification_status", "in", ["bounce", "exception"]],
                ]);
                return notifications.length > 0;
            });
            messages.length = Math.min(messages.length, 100);
            this._addToRes(res, {
                Message: this._mockMailMessage_MessageNotificationFormat(
                    messages.map((message) => message.id)
                ),
            });
        }
        return res;
    },
    _addToRes(res, data) {
        for (const [key, val] of Object.entries(data)) {
            if (Array.isArray(val)) {
                if (!res[key]) {
                    res[key] = val;
                } else {
                    res[key].push(...val);
                }
            } else if (typeof val === "object" && val !== null) {
                if (!res[key]) {
                    res[key] = val;
                } else {
                    Object.assign(res[key], val);
                }
            } else {
                throw new Error("Unsupported return type");
            }
        }
    },
});
