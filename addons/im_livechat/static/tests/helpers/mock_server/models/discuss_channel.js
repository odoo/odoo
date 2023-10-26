/* @odoo-module */

import "@mail/../tests/helpers/mock_server/models/discuss_channel"; // ensure mail overrides are applied first
import { Command } from "@mail/../tests/helpers/command";

import { patch } from "@web/core/utils/patch";
import { MockServer } from "@web/../tests/helpers/mock_server";

patch(MockServer.prototype, {
    /**
     * @override
     */
    _mockDiscussChannelChannelInfo(ids) {
        const channelInfos = super._mockDiscussChannelChannelInfo(...arguments);
        for (const channelInfo of channelInfos) {
            const channel = this.getRecords("discuss.channel", [["id", "=", channelInfo.id]])[0];
            channelInfo["anonymous_name"] = channel.anonymous_name;
            // add the last message date
            if (channel.channel_type === "livechat") {
                // add the operator id
                if (channel.livechat_operator_id) {
                    const operator = this.getRecords("res.partner", [
                        ["id", "=", channel.livechat_operator_id],
                    ])[0];
                    // livechat_username ignored for simplicity
                    channelInfo.operator_pid = [
                        operator.id,
                        operator.display_name.replace(",", ""),
                    ];
                }
            }
        }
        return channelInfos;
    },

    /**
     * Simulates `_close_livechat_session` on `discuss.channel`.
     *
     * @param {Object} channel
     */
    _mockDiscussChannel_closeLivechatSession(channel) {
        if (!channel.livechat_active) {
            return;
        }
        this.pyEnv.write("discuss.channel", [[channel.id], { livechat_active: false }]);
        if (channel.message_ids.length === 0) {
            return;
        }
        this._mockDiscussChannelMessagePost(channel.id, {
            body: this._mockDiscussChannel_getVisitorLeaveMessage(),
            message_type: "comment",
            subtype_xmlid: "mail.mt_comment",
        });
    },

    /**
     * Simulates `_channel_fetch_message` on `discuss.channel`.
     */
    _mockDiscussChannel_channel_fetch_message(channelId, lastId, limit) {
        const domain = [
            ["model", "=", "discuss.channel"],
            ["res_id", "=", channelId],
        ];
        if (lastId) {
            domain.push(["id", "<", lastId]);
        }
        const messages = this._mockMailMessage_MessageFetch(domain, limit);
        return this._mockMailMessageMessageFormat(messages.map(({ id }) => id));
    },

    /**
     * Simulates `_get_visitor_leave_message` on `discuss.channel`.
     */
    _mockDiscussChannel_getVisitorLeaveMessage() {
        return "Visitor left the conversation.";
    },

    /**
     * Simulates `_find_or_create_persona_for_channel` on `discuss.channel`.
     */
    _mockDiscussChannel__findOrCreatePersonaForChannel(channelId, guestName) {
        if (this._mockDiscussChannelMember__getAsSudoFromContext(channelId)) {
            return;
        }
        const guestId =
            this._mockMailGuest__getGuestFromContext()?.id ??
            this.pyEnv["mail.guest"].create({ name: guestName });
        this.pyEnv["discuss.channel"].write([channelId], {
            channel_member_ids: [Command.create({ guest_id: guestId })],
        });
        this._mockMailGuest__setAuthCookie(guestId);
    },
});
