import { fields, models } from "@web/../tests/web_test_helpers";
import { serializeDateTime, today } from "@web/core/l10n/dates";
import { parseModelParams } from "../mail_mock_server";

export class DiscussChannelMember extends models.ServerModel {
    _name = "discuss.channel.member";

    fold_state = fields.Generic({ default: "closed" });
    is_pinned = fields.Generic({ compute: "_compute_is_pinned" });
    unpin_dt = fields.Datetime({ string: "Unpin date" });
    message_unread_counter = fields.Generic({ default: 0 });
    last_interest_dt = fields.Datetime({ default: () => serializeDateTime(today()) });

    /**
     * @param {number[]} ids
     * @param {boolean} is_typing
     */
    notify_typing(ids, is_typing) {
        const kwargs = parseModelParams(arguments, "ids", "is_typing");
        ids = kwargs.ids;
        delete kwargs.ids;
        is_typing = kwargs.is_typing;

        /** @type {import("mock_models").BusBus} */
        const BusBus = this.env["bus.bus"];
        /** @type {import("mock_models").DiscussChannel} */
        const DiscussChannel = this.env["discuss.channel"];

        const members = this._filter([["id", "in", ids]]);
        for (const member of members) {
            const [channel] = DiscussChannel._filter([["id", "=", member.channel_id]]);
            const [data] = this._discuss_channel_member_format([member.id]);
            Object.assign(data, { isTyping: is_typing });
            BusBus._add_to_queue(channel, "discuss.channel.member/typing_status", data);
        }
    }

    _compute_is_pinned() {
        for (const member of this) {
            const [channel] = this.env["discuss.channel"]._filter([["id", "=", member.channel_id]]);
            member.is_pinned =
                !member.unpin_dt ||
                member?.last_interest_dt >= member.unpin_dt ||
                channel?.last_interest_dt >= member.unpin_dt;
        }
    }

    /**
     * @param {number} id
     * @param {string} [state]
     * @param {number} [state_count]
     */
    _channel_fold(id, state, state_count) {
        const kwargs = parseModelParams(arguments, "id", "state", "state_count");
        id = kwargs.id;
        delete kwargs.id;
        state = kwargs.state;
        state_count = kwargs.state_count;

        /** @type {import("mock_models").BusBus} */
        const BusBus = this.env["bus.bus"];
        /** @type {import("mock_models").MailGuest} */
        const MailGuest = this.env["mail.guest"];
        /** @type {import("mock_models").ResPartner} */
        const ResPartner = this.env["res.partner"];

        const [member] = this.search_read([["id", "=", id]]);
        if (member.fold_state === state) {
            return;
        }
        this.write([id], { fold_state: state });
        let target;
        if (member.partner_id) {
            [target] = ResPartner.search_read([["id", "=", member.partner_id[0]]]);
        } else {
            [target] = MailGuest.search_read([["id", "=", member.guest_id[0]]]);
        }
        BusBus._add_to_queue(target, "discuss.Thread/fold_state", {
            foldStateCount: state_count,
            id: member.channel_id[0],
            model: "discuss.channel",
            fold_state: state,
        });
    }

    /** @param {number[]} ids */
    _discuss_channel_member_format(ids) {
        const kwargs = parseModelParams(arguments, "ids");
        ids = kwargs.ids;
        delete kwargs.ids;

        /** @type {import("mock_models").MailGuest} */
        const MailGuest = this.env["mail.guest"];

        const members = this._filter([["id", "in", ids]]);
        /** @type {Record<string, { thread: any; id: number; persona: any }>[]} */
        const dataList = [];
        for (const member of members) {
            let persona;
            if (member.partner_id) {
                persona = this._get_partner_data([member.id]);
            }
            if (member.guest_id) {
                const [guest] = MailGuest._filter([["id", "=", member.guest_id]]);
                persona = MailGuest._guest_format([guest.id])[guest.id];
            }
            const data = {
                create_date: member.create_date,
                thread: { id: member.channel_id, model: "discuss.channel" },
                id: member.id,
                last_interest_dt: member.last_interest_dt,
                persona,
                seen_message_id: member.seen_message_id ? { id: member.seen_message_id } : false,
                fetched_message_id: member.fetched_message_id
                    ? { id: member.fetched_message_id }
                    : false,
            };
            dataList.push(data);
        }
        return dataList;
    }

    /** @param {number[]} ids */
    _get_partner_data(ids) {
        const kwargs = parseModelParams(arguments, "ids");
        ids = kwargs.ids;
        delete kwargs.ids;

        /** @type {import("mock_models").ResPartner} */
        const ResPartner = this.env["res.partner"];

        const [member] = this._filter([["id", "in", ids]]);
        return ResPartner.mail_partner_format([member.partner_id])[member.partner_id];
    }
}
