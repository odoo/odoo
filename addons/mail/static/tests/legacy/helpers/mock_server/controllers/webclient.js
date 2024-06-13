/** @odoo-module alias=@mail/../tests/helpers/mock_server/controllers/webclient default=false */

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
        if ("init_messaging" in args) {
            const initMessaging =
                this._mockMailGuest__getGuestFromContext() && this.pyEnv.currentUser?._is_public()
                    ? {}
                    : this._mockResUsers_InitMessaging([this.pyEnv.currentUserId], args.context);
            this._addToRes(res, initMessaging);
            const guest =
                this.pyEnv.currentUser?._is_public() && this._mockMailGuest__getGuestFromContext();
            const members = this.getRecords("discuss.channel.member", [
                guest
                    ? ["guest_id", "=", guest.id]
                    : ["partner_id", "=", this.pyEnv.currentPartnerId],
                "|",
                ["fold_state", "in", ["open", "folded"]],
                ["rtc_inviting_session_id", "!=", false],
            ]);
            const channelsDomain = [["id", "in", members.map((m) => m.channel_id)]];
            const { channelTypes } = args.init_messaging;
            if (channelTypes) {
                channelsDomain.push(["channel_type", "in", channelTypes]);
            }
            this._addToRes(res, {
                Thread: this._mockDiscussChannelChannelInfo(
                    this.pyEnv["discuss.channel"].search(channelsDomain)
                ),
            });
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
        if (args.systray_get_activities && this.pyEnv.currentPartnerId) {
            const bus_last_id = this.lastBusNotificationId;
            const groups = this._mockResUsers_getActivityGroups();
            this._addToRes(res, {
                Store: {
                    activityCounter: groups.reduce(
                        (counter, group) => counter + (group.total_count || 0),
                        0
                    ),
                    activity_counter_bus_id: bus_last_id,
                    activityGroups: groups,
                },
            });
        }
        if (args.canned_responses) {
            this._addToRes(res, {
                CannedResponse: this.pyEnv["mail.canned.response"].search_read([], {
                    fields: ["source", "substitution"],
                }),
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
