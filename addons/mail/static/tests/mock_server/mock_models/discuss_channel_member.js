import { mailDataHelpers } from "@mail/../tests/mock_server/mail_mock_server";

import { fields, getKwArgs, makeKwArgs, models } from "@web/../tests/web_test_helpers";
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
        /** @type {import("mock_models").DiscussChannelMember} */
        const DiscussChannelMember = this.env["discuss.channel.member"];

        const members = this.browse(ids);
        const notifications = [];
        for (const member of members) {
            const [channel] = DiscussChannel.browse(member.channel_id);
            notifications.push([
                channel,
                "mail.record/insert",
                new mailDataHelpers.Store(DiscussChannelMember.browse(member.id))
                    .add("discuss.channel.member", { id: member.id, isTyping: is_typing })
                    .get_result(),
            ]);
        }
        BusBus._sendmany(notifications);
    }

    _compute_is_pinned() {
        for (const member of this) {
            const [channel] = this.env["discuss.channel"].browse(member.channel_id);
            member.is_pinned =
                !member.unpin_dt ||
                member?.last_interest_dt >= member.unpin_dt ||
                channel?.last_interest_dt >= member.unpin_dt;
        }
    }

    _compute_message_unread_counter([memberId]) {
        const [member] = this.browse(memberId);
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
    _to_store(ids, store, fields, extra_fields) {
        const kwargs = getKwArgs(arguments, "ids", "store", "fields", "extra_fields");
        ids = kwargs.ids;
        fields = kwargs.fields;
        extra_fields = kwargs.extra_fields;

        if (!fields) {
            fields = {
                channel: [],
                create_date: true,
                fetched_message_id: true,
                persona: null,
                seen_message_id: true,
                last_interest_dt: true,
                last_seen_dt: true,
                new_message_separator: true,
            };
        }
        if (extra_fields) {
            fields = { ...fields, ...extra_fields };
        }

        /** @type {import("mock_models").MailGuest} */
        const MailGuest = this.env["mail.guest"];
        /** @type {import("mock_models").ResPartner} */
        const ResPartner = this.env["res.partner"];

        for (const member of this.browse(ids)) {
            const [data] = this._read_format(
                member.id,
                Object.keys(fields).filter(
                    (field) =>
                        ![
                            "channel",
                            "fetched_message_id",
                            "message_unread_counter",
                            "seen_message_id",
                            "persona",
                        ].includes(field)
                ),
                false
            );
            if ("channel" in fields) {
                data.thread = mailDataHelpers.Store.one(
                    this.env["discuss.channel"].browse(member.channel_id),
                    makeKwArgs({ as_thread: true, only_id: true })
                );
            }
            if ("persona" in fields) {
                if (member.partner_id) {
                    data.persona = mailDataHelpers.Store.one(
                        ResPartner.browse(member.partner_id),
                        makeKwArgs({
                            fields: this._get_store_partner_fields([member.id], fields["persona"]),
                        })
                    );
                }
                if (member.guest_id) {
                    data.persona = mailDataHelpers.Store.one(
                        MailGuest.browse(member.guest_id),
                        makeKwArgs({ fields: fields["persona"] })
                    );
                }
            }
            if ("fetched_message_id" in fields) {
                data.fetched_message_id = mailDataHelpers.Store.one(
                    this.env["mail.message"].browse(member.fetched_message_id),
                    makeKwArgs({ only_id: true })
                );
            }
            if ("seen_message_id" in fields) {
                data.seen_message_id = mailDataHelpers.Store.one(
                    this.env["mail.message"].browse(member.seen_message_id),
                    makeKwArgs({ only_id: true })
                );
            }
            if ("message_unread_counter" in fields) {
                data.message_unread_counter = this._compute_message_unread_counter([member.id]);
                data.message_unread_counter_bus_id = this.env["bus.bus"].lastBusNotificationId;
            }
            store.add(this.browse(member.id), data);
        }
    }

    _get_store_partner_fields(ids, fields) {
        return fields;
    }

    /**
     * @param {number[]} ids
     * @param {number} last_message_id
     * @param {boolean} [sync]
     */
    _mark_as_read(ids, last_message_id, sync) {
        const kwargs = getKwArgs(arguments, "ids", "last_message_id", "sync");
        ids = kwargs.ids;
        delete kwargs.ids;
        last_message_id = kwargs.last_message_id;
        sync = kwargs.sync ?? false;
        const [member] = this.browse(ids);
        if (!member) {
            return;
        }
        const messages = this.env["mail.message"]._filter([
            ["model", "=", "discuss.channel"],
            ["res_id", "=", member.channel_id],
        ]);
        if (!messages || messages.length === 0) {
            return;
        }
        this._set_last_seen_message([member.id], last_message_id);
        this.env["discuss.channel.member"]._set_new_message_separator(
            [member.id],
            last_message_id + 1,
            sync
        );
    }

    /**
     * @param {number[]} ids
     * @param {number} message_id
     * @param {boolean} [notify=true]
     */
    _set_last_seen_message(ids, message_id, notify) {
        const kwargs = getKwArgs(arguments, "ids", "message_id", "notify");
        ids = kwargs.ids;
        delete kwargs.ids;
        message_id = kwargs.message_id;
        notify = kwargs.notify ?? true;
        /** @type {import("mock_models").BusBus} */
        const BusBus = this.env["bus.bus"];
        /** @type {import("mock_models").DiscussChannel} */
        const DiscussChannel = this.env["discuss.channel"];
        /** @type {import("mock_models").DiscussChannelMember} */
        const DiscussChannelMember = this.env["discuss.channel.member"];
        /** @type {import("mock_models").ResPartner} */
        const ResPartner = this.env["res.partner"];

        const [member] = this.browse(ids);
        if (!member) {
            return;
        }
        DiscussChannelMember._set_new_message_separator([member.id], message_id + 1);
        DiscussChannelMember.write([member.id], {
            fetched_message_id: message_id,
            seen_message_id: message_id,
            message_unread_counter: DiscussChannelMember._compute_message_unread_counter([
                member.id,
            ]),
        });
        if (notify) {
            const [channel] = this.search_read([["id", "in", ids]]);
            const [partner, guest] = ResPartner._get_current_persona();
            let target = guest ?? partner;
            if (DiscussChannel._types_allowing_seen_infos().includes(channel.channel_type)) {
                target = channel;
            }
            BusBus._sendone(
                target,
                "mail.record/insert",
                new mailDataHelpers.Store(
                    DiscussChannelMember.browse(member.id),
                    makeKwArgs({
                        fields: { channel: [], persona: ["name"], seen_message_id: true },
                    })
                ).get_result()
            );
        }
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

        /** @type {import("mock_models").DiscussChannelMember} */
        const DiscussChannelMember = this.env["discuss.channel.member"];

        const [member] = DiscussChannelMember.browse(ids);
        if (!member) {
            return;
        }
        this.env["discuss.channel.member"].write([member.id], {
            new_message_separator: message_id,
        });
        const message_unread_counter = this._compute_message_unread_counter([member.id]);
        this.env["discuss.channel.member"].write([member.id], { message_unread_counter });
        const [partner, guest] = this.env["res.partner"]._get_current_persona();
        this.env["bus.bus"]._sendone(
            guest ?? partner,
            "mail.record/insert",
            new mailDataHelpers.Store(
                DiscussChannelMember.browse(member.id),
                makeKwArgs({
                    fields: {
                        channel: [],
                        persona: ["name"],
                        message_unread_counter: true,
                        new_message_separator: true,
                    },
                })
            )
                .add("discuss.channel.member", { id: member.id, syncUnread: sync })
                .get_result()
        );
    }
}
