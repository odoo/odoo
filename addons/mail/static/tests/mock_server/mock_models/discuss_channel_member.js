/** @odoo-module */

import { fields, models } from "@web/../tests/web_test_helpers";

export class DiscussChannelMember extends models.ServerModel {
    _name = "discuss.channel.member";

    fold_state = fields.Generic({ default: "open" });
    is_pinned = fields.Generic({ default: true });
    message_unread_counter = fields.Generic({ default: 0 });

    /**
     * Simulates `notify_typing` on `discuss.channel.member`.
     *
     * @param {number[]} ids
     * @param {boolean} isTyping
     */
    notify_typing(ids, isTyping) {
        const members = this._filter([["id", "in", ids]]);
        const notifications = [];
        for (const member of members) {
            const [channel] = this.env["discuss.channel"]._filter([["id", "=", member.channel_id]]);
            const [data] = this._discussChannelMemberFormat([member.id]);
            Object.assign(data, { isTyping });
            notifications.push([channel, "discuss.channel.member/typing_status", data]);
            notifications.push([channel.uuid, "discuss.channel.member/typing_status", data]);
        }
        this.env["bus.bus"]._sendmany(notifications);
    }

    /**
     * Simulates the '_channelFold' route on `discuss.channel.member`.
     *
     * @param {number} ids
     * @param {string} [state]
     * @param {number} [state_count]
     * @param {KwArgs} [kwargs]
     */
    _channelFold(ids, state, state_count, kwargs = {}) {
        state = kwargs.state || state;
        state_count = kwargs.state_count || state_count;
        const channels = this.env["discuss.channel"]._filter([["id", "in", ids]]);
        for (const channel of channels) {
            const memberOfCurrentUser = this._getAsSudoFromContext(channel.id);
            const foldState = state
                ? state
                : memberOfCurrentUser.fold_state === "open"
                ? "folded"
                : "open";
            const vals = {
                fold_state: foldState,
                is_minimized: foldState !== "closed",
            };
            this.write([memberOfCurrentUser.id], vals);
            this.env["bus.bus"]._sendone(this.env.partner, "discuss.Thread/fold_state", {
                foldStateCount: state_count,
                id: channel.id,
                model: "discuss.channel",
                fold_state: foldState,
            });
        }
    }

    /**
     * Simulates `_discuss_channel_member_format` on `discuss.channel.member`.
     *
     * @param {number[]} ids
     */
    _discussChannelMemberFormat(ids) {
        const members = this._filter([["id", "in", ids]]);
        /** @type {Record<string, { thread: any; id: number; persona: any }>[]} */
        const dataList = [];
        for (const member of members) {
            let persona;
            if (member.partner_id) {
                persona = this._getPartnerData([member.id]);
                persona.type = "partner";
            }
            if (member.guest_id) {
                const [guest] = this.env["mail.guest"]._filter([["id", "=", member.guest_id]]);
                persona = {
                    id: guest.id,
                    im_status: guest.im_status,
                    name: guest.name,
                    type: "guest",
                };
            }
            dataList.push({
                thread: { id: member.channel_id, model: "discuss.channel" },
                id: member.id,
                persona,
            });
        }
        return dataList;
    }

    /**
     * Simulates `_get_partner_data` on `discuss.channel.member`.
     *
     * @param {number[]} ids
     */
    _getPartnerData(ids) {
        const [member] = this._filter([["id", "in", ids]]);
        return this.env["res.partner"].mail_partner_format([member.partner_id])[member.partner_id];
    }

    /**
     * @param {number} channelId
     */
    _getAsSudoFromContext(channelId) {
        const guest = this.env["mail.guest"]._getGuestFromContext();
        return this.search_read([
            ["channel_id", "=", channelId],
            guest ? ["guest_id", "=", guest.id] : ["partner_id", "=", this.env.partner_id],
        ])[0];
    }
}
