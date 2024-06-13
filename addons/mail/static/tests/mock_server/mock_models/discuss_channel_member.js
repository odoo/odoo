import { fields, getKwArgs, models } from "@web/../tests/web_test_helpers";
import { serializeDateTime, today } from "@web/core/l10n/dates";

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
        const kwargs = getKwArgs(arguments, "ids", "is_typing");
        ids = kwargs.ids;
        delete kwargs.ids;
        is_typing = kwargs.is_typing;

        /** @type {import("mock_models").BusBus} */
        const BusBus = this.env["bus.bus"];
        /** @type {import("mock_models").DiscussChannel} */
        const DiscussChannel = this.env["discuss.channel"];

        const members = this._filter([["id", "in", ids]]);
        const notifications = [];
        for (const member of members) {
            const [channel] = DiscussChannel._filter([["id", "=", member.channel_id]]);
            const [data] = this._discuss_channel_member_format([member.id]);
            Object.assign(data, { isTyping: is_typing });
            notifications.push([channel, "discuss.channel.member/typing_status", data]);
            notifications.push([channel.uuid, "discuss.channel.member/typing_status", data]);
        }
        BusBus._sendmany(notifications);
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

    _compute_message_unread_counter([memberId]) {
        const [member] = this._filter([["id", "=", memberId]]);
        return this.env["mail.message"].search_count([
            ["res_id", "=", member.channel_id],
            ["model", "=", "discuss.channel"],
            ["id", ">=", member.new_message_separator],
        ]);
    }

    /**
     * @param {number} id
     * @param {string} [state]
     * @param {number} [state_count]
     */
    _channel_fold(id, state, state_count) {
        const kwargs = getKwArgs(arguments, "id", "state", "state_count");
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
        BusBus._sendone(target, "discuss.Thread/fold_state", {
            foldStateCount: state_count,
            id: member.channel_id[0],
            model: "discuss.channel",
            fold_state: state,
        });
    }

    /** @param {number[]} ids */
    _discuss_channel_member_format(ids, fields) {
        const kwargs = getKwArgs(arguments, "ids", "fields");
        ids = kwargs.ids;
        fields = kwargs.fields;
        delete kwargs.ids;
        delete kwargs.fields;

        if (!fields) {
            fields = {
                channel: {},
                create_date: true,
                fetched_message_id: true,
                id: true,
                persona: {},
                seen_message_id: true,
                last_interest_dt: true,
                new_message_separator: true,
            };
        }
        if (fields.message_unread_counter && !fields.channel) {
            throw new Error(
                "'message_unread_counter' cannot be used without 'channel' in 'fields'"
            );
        }

        /** @type {import("mock_models").MailGuest} */
        const MailGuest = this.env["mail.guest"];

        const members = this._filter([["id", "in", ids]]);
        /** @type {Record<string, { thread: any; id: number; persona: any }>[]} */
        const dataList = [];
        for (const member of members) {
            let persona;
            const data = {};
            if (member.partner_id) {
                persona = this._get_partner_data([member.id]);
            }
            if (member.guest_id) {
                const [guest] = MailGuest._filter([["id", "=", member.guest_id]]);
                persona = MailGuest._guest_format([guest.id])[guest.id];
            }
            if ("id" in fields) {
                data.id = member.id;
            }
            if ("channel" in fields) {
                data.thread = { id: member.channel_id, model: "discuss.channel" };
            }
            if ("create_date" in fields) {
                data.create_date = member.create_date;
            }
            if ("persona" in fields) {
                data.persona = persona;
            }
            if ("fetched_message_id" in fields) {
                data.fetched_message_id = member.fetched_message_id
                    ? { id: member.fetched_message_id }
                    : false;
            }
            if ("seen_message_id" in fields) {
                data.seen_message_id = member.seen_message_id
                    ? { id: member.seen_message_id }
                    : false;
            }
            if ("message_unread_counter" in fields) {
                data.thread.message_unread_counter = this._compute_message_unread_counter([
                    member.id,
                ]);
                data.thread.message_unread_counter_bus_id =
                    this.env["bus.bus"].lastBusNotificationId;
            }
            if ("last_interest_dt" in fields) {
                data.last_interest_dt = member.last_interest_dt;
            }
            if ("new_message_separator" in fields) {
                data.new_message_separator = member.new_message_separator;
            }
            dataList.push(data);
        }
        return dataList;
    }

    /** @param {number[]} ids */
    _get_partner_data(ids) {
        const kwargs = getKwArgs(arguments, "ids");
        ids = kwargs.ids;
        delete kwargs.ids;

        /** @type {import("mock_models").ResPartner} */
        const ResPartner = this.env["res.partner"];

        const [member] = this._filter([["id", "in", ids]]);
        return ResPartner.mail_partner_format([member.partner_id])[member.partner_id];
    }

    /**
     * @param {number[]} ids
     * @param {number} message_id
     * @param {boolean} sync
     */
    _set_new_message_separator(ids, message_id, sync) {
        const kwargs = getKwArgs(arguments, "ids", "message_id", "sync");
        ids = kwargs.ids;
        delete kwargs.ids;
        message_id = kwargs.message_id;
        sync = kwargs.sync ?? false;
        const [member] = this._filter([["id", "in", ids]]);
        if (!member) {
            return;
        }
        this.env["discuss.channel.member"].write([member.id], {
            new_message_separator: message_id,
        });
        const message_unread_counter = this._compute_message_unread_counter([member.id]);
        this.env["discuss.channel.member"].write([member.id], { message_unread_counter });
        const personaFields = {
            partner: { id: true, name: true },
            guest: { id: true, name: true },
        };
        const memberData = this._discuss_channel_member_format([member.id], {
            id: true,
            channel: {},
            persona: personaFields,
            message_unread_counter: true,
            new_message_separator: true,
        })[0];
        memberData["syncUnread"] = sync;
        const [partner, guest] = this.env["res.partner"]._get_current_persona();
        const target = guest ?? partner;
        this.env["bus.bus"]._sendone(target, "mail.record/insert", { ChannelMember: memberData });
    }
}
