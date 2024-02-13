/** @odoo-module */

import { constants, fields, models } from "@web/../tests/web_test_helpers";

export class DiscussChannelMember extends models.ServerModel {
    _name = "discuss.channel.member";

    fold_state = fields.Generic({ default: "open" });
    is_pinned = fields.Generic({ default: true });
    message_unread_counter = fields.Generic({ default: 0 });

    /**
     * @param {number[]} ids
     * @param {boolean} isTyping
     */
    notify_typing(ids, isTyping) {
        /** @type {import("mock_models").BusBus} */
        const BusBus = this.env["bus.bus"];
        /** @type {import("mock_models").DiscussChannel} */
        const DiscussChannel = this.env["discuss.channel"];

        const members = this._filter([["id", "in", ids]]);
        const notifications = [];
        for (const member of members) {
            const [channel] = DiscussChannel._filter([["id", "=", member.channel_id]]);
            const [data] = this._discuss_channel_member_format([member.id]);
            Object.assign(data, { isTyping });
            notifications.push([channel, "discuss.channel.member/typing_status", data]);
            notifications.push([channel.uuid, "discuss.channel.member/typing_status", data]);
        }
        BusBus._sendmany(notifications);
    }

    /**
     * @param {number} ids
     * @param {string} [state]
     * @param {number} [state_count]
     * @param {KwArgs} [kwargs]
     */
    _channel_fold(ids, state, state_count, kwargs = {}) {
        /** @type {import("mock_models").BusBus} */
        const BusBus = this.env["bus.bus"];
        /** @type {import("mock_models").DiscussChannel} */
        const DiscussChannel = this.env["discuss.channel"];
        /** @type {import("mock_models").ResPartner} */
        const ResPartner = this.env["res.partner"];

        state = kwargs.state || state;
        state_count = kwargs.state_count || state_count;
        const channels = DiscussChannel._filter([["id", "in", ids]]);
        for (const channel of channels) {
            const memberOfCurrentUser = DiscussChannel._find_or_create_member_for_self(channel.id);
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
            const [partner] = ResPartner.read(constants.PARTNER_ID);
            BusBus._sendone(partner, "discuss.Thread/fold_state", {
                foldStateCount: state_count,
                id: channel.id,
                model: "discuss.channel",
                fold_state: foldState,
            });
        }
    }

    /** @param {number[]} ids */
    _discuss_channel_member_format(ids) {
        /** @type {import("mock_models").MailGuest} */
        const MailGuest = this.env["mail.guest"];

        const members = this._filter([["id", "in", ids]]);
        /** @type {Record<string, { thread: any; id: number; persona: any }>[]} */
        const dataList = [];
        for (const member of members) {
            let persona;
            if (member.partner_id) {
                persona = this._get_partner_data([member.id]);
                persona.type = "partner";
            }
            if (member.guest_id) {
                const [guest] = MailGuest._filter([["id", "=", member.guest_id]]);
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

    /** @param {number[]} ids */
    _get_partner_data(ids) {
        /** @type {import("mock_models").ResPartner} */
        const ResPartner = this.env["res.partner"];

        const [member] = this._filter([["id", "in", ids]]);
        return ResPartner.mail_partner_format([member.partner_id])[member.partner_id];
    }
}
