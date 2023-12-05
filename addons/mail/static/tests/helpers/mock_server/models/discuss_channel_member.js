/* @odoo-module */

import { patch } from "@web/core/utils/patch";
import { MockServer } from "@web/../tests/helpers/mock_server";

patch(MockServer.prototype, {
    _mockDiscussChannelMember__getAsSudoFromContext(channelId) {
        const [partner, guest] = this._mockResPartner__getCurrentPersona();
        if (!partner && !guest) {
            return;
        }
        return this.pyEnv["discuss.channel.member"].searchRead([
            ["channel_id", "=", channelId],
            guest ? ["guest_id", "=", guest.id] : ["partner_id", "=", partner.id],
        ])[0];
    },
    /**
     * Simulates `notify_typing` on `discuss.channel.member`.
     *
     * @private
     * @param {integer[]} ids
     * @param {boolean} is_typing
     */
    _mockDiscussChannelMember_NotifyTyping(ids, is_typing) {
        const members = this.getRecords("discuss.channel.member", [["id", "in", ids]]);
        const notifications = [];
        for (const member of members) {
            const [channel] = this.getRecords("discuss.channel", [["id", "=", member.channel_id]]);
            const [data] = this._mockDiscussChannelMember_DiscussChannelMemberFormat([member.id]);
            Object.assign(data, {
                isTyping: is_typing,
            });
            notifications.push([channel, "discuss.channel.member/typing_status", data]);
            notifications.push([channel.uuid, "discuss.channel.member/typing_status", data]);
        }
        this.pyEnv["bus.bus"]._sendmany(notifications);
    },
    /**
     * Simulates `_discuss_channel_member_format` on `discuss.channel.member`.
     *
     * @private
     * @param {integer[]} ids
     * @returns {Object[]}
     */
    _mockDiscussChannelMember_DiscussChannelMemberFormat(ids) {
        const members = this.getRecords("discuss.channel.member", [["id", "in", ids]]);
        const dataList = [];
        for (const member of members) {
            let persona;
            if (member.partner_id) {
                persona = this._mockDiscussChannelMember_GetPartnerData([member.id]);
                persona.type = "partner";
            }
            if (member.guest_id) {
                const [guest] = this.getRecords("mail.guest", [["id", "=", member.guest_id]]);
                persona = {
                    id: guest.id,
                    im_status: guest.im_status,
                    name: guest.name,
                    type: "guest",
                };
            }
            const data = {
                thread: { id: member.channel_id, model: "discuss.channel" },
                id: member.id,
                persona,
            };
            dataList.push(data);
        }
        return dataList;
    },
    /**
     * Simulates `_get_partner_data` on `discuss.channel.member`.
     *
     * @private
     * @param {integer[]} ids
     * @returns {Object}
     */
    _mockDiscussChannelMember_GetPartnerData(ids) {
        const [member] = this.getRecords("discuss.channel.member", [["id", "in", ids]]);
        return this._mockResPartnerMailPartnerFormat([member.partner_id]).get(member.partner_id);
    },
});
