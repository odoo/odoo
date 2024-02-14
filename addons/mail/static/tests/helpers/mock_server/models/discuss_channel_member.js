/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { MockServer } from "@web/../tests/helpers/mock_server";

patch(MockServer.prototype, "mail/models/discuss_channel_member", {
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
                persona = { partner: this._mockDiscussChannelMember_GetPartnerData([member.id]) };
            }
            if (member.guest_id) {
                const [guest] = this.getRecords("mail.guest", [["id", "=", member.guest_id]]);
                persona = {
                    guest: {
                        id: guest.id,
                        im_status: guest.im_status,
                        name: guest.name,
                    },
                };
            }
            const data = {
                channel: { id: member.channel_id },
                id: member.id,
                persona: persona,
                create_date: member.create_date,
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
