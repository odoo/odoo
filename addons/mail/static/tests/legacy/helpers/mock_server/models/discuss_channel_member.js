/** @odoo-module alias=@mail/../tests/helpers/mock_server/models/discuss_channel_member default=false */

import { patch } from "@web/core/utils/patch";
import { MockServer } from "@web/../tests/helpers/mock_server";

patch(MockServer.prototype, {
    _mockDiscussChannelMember__getAsSudoFromContext(channelId) {
        const [partner, guest] = this._mockResPartner__getCurrentPersona();
        if (!partner && !guest) {
            return;
        }
        return this.pyEnv["discuss.channel.member"].search_read([
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
            notifications.push([
                channel,
                "mail.record/insert",
                { "discuss.channel.member": [data] },
            ]);
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
            }
            const data = {
                create_date: member.create_date,
                thread: { id: member.channel_id, model: "discuss.channel" },
                id: member.id,
                persona,
                seen_message_id: member.seen_message_id ? { id: member.seen_message_id } : false,
                fetched_message_id: member.fetched_message_id
                    ? { id: member.fetched_message_id }
                    : false,
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
    /**
     * Simulates the '_channel_fold' method on `discuss.channel.member`.
     *
     * @private
     * @param {number} id
     * @param {state} [state]
     * @param {number} [state_count]
     */
    _mockDiscussChannelMember__channelFold(id, state, state_count) {
        const [member] = this.pyEnv["discuss.channel.member"].search_read([["id", "=", id]]);
        if (member.fold_state === state) {
            return;
        }
        this.pyEnv["discuss.channel.member"].write([id], { fold_state: state });
        let target;
        if (member.partner_id) {
            [target] = this.pyEnv["res.partner"].search_read([["id", "=", member.partner_id[0]]]);
        } else {
            [target] = this.pyEnv["mail.guest"].search_read([["id", "=", member.guest_id[0]]]);
        }
        this.pyEnv["bus.bus"]._sendone(target, "discuss.Thread/fold_state", {
            foldStateCount: state_count,
            id: member.channel_id[0],
            model: "discuss.channel",
            fold_state: state,
        });
    },
});
