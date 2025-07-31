import { mailDataHelpers } from "@mail/../tests/mock_server/mail_mock_server";

import { fields, getKwArgs, makeKwArgs, models } from "@web/../tests/web_test_helpers";
import { serializeDateTime, today } from "@web/core/l10n/dates";

const { DateTime } = luxon;

export class DiscussChannelMember extends models.ServerModel {
    _name = "discuss.channel.member";

    is_pinned = fields.Generic({ compute: "_compute_is_pinned" });
    unpin_dt = fields.Datetime({ string: "Unpin date" });
    message_unread_counter = fields.Generic({ default: 0 });
    last_interest_dt = fields.Datetime({ default: () => serializeDateTime(today()) });

    write(ids, vals) {
        const membersToUpdate = this.browse(ids);
        const syncFields = this._sync_field_names();
        const oldValsByMember = new Map();
        for (const member of membersToUpdate) {
            const oldVals = {};
            for (const fieldName of syncFields) {
                oldVals[fieldName] = member[fieldName];
            }
            oldValsByMember.set(member.id, oldVals);
        }
        const result = super.write(ids, vals);
        for (const member of membersToUpdate) {
            const oldVals = oldValsByMember.get(member.id);
            const diff = [];
            for (const fieldName of syncFields) {
                if (member[fieldName] !== oldVals[fieldName]) {
                    diff.push(fieldName);
                }
            }
            if (diff.length > 0) {
                const store = new mailDataHelpers.Store();
                diff.push("channel", "persona");
                this.browse(member.id)._to_store(store, diff);
                const [partner, guest] = this.env["res.partner"]._get_current_persona();
                const busChannel = guest ?? partner;
                this.env["bus.bus"]._sendone(busChannel, "mail.record/insert", store.get_result());
            }
        }
        return result;
    }

    _sync_field_names() {
        return ["last_interest_dt", "message_unread_counter", "new_message_separator", "unpin_dt"];
    }

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
                    .add("discuss.channel.member", {
                        id: member.id,
                        isTyping: is_typing,
                        is_typing_dt: serializeDateTime(DateTime.now()),
                    })
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

    /** @param {number[]} ids */
    _to_store(store, fields) {
        const kwargs = getKwArgs(arguments, "store", "fields");
        fields = kwargs.fields;
        store._add_record_fields(
            this,
            fields.filter(
                (field) => !["message_unread_counter", "persona", "channel"].includes(field)
            )
        );
        for (const member of this) {
            const data = {};
            if (fields.includes("message_unread_counter")) {
                data.message_unread_counter = this._compute_message_unread_counter([member.id]);
                data.message_unread_counter_bus_id = this.env["bus.bus"].lastBusNotificationId;
            }
            if (fields.includes("channel")) {
                data.channel_id = mailDataHelpers.Store.one(
                    this.env["discuss.channel"].browse(member.channel_id),
                    makeKwArgs({ as_thread: true, only_id: true })
                );
            }
            if (fields.includes("persona")) {
                store._add_record_fields(this.browse(member.id), this._to_store_persona());
            }

            if (Object.keys(data).length) {
                store._add_record_fields(this.browse(member.id), data);
            }
        }
    }

    _to_store_persona(fields) {
        return [
            mailDataHelpers.Store.attr(
                "partner_id",
                (m) =>
                    mailDataHelpers.Store.one(
                        this.env["res.partner"].browse(m.partner_id),
                        makeKwArgs({
                            fields: this._get_store_partner_fields(fields),
                        })
                    ),
                makeKwArgs({
                    predicate: (m) =>
                        m.partner_id !== null && m.partner_id !== undefined && m.partner_id,
                })
            ),
            mailDataHelpers.Store.attr(
                "guest_id",
                (m) =>
                    mailDataHelpers.Store.one(
                        this.env["mail.guest"].browse(m.guest_id),
                        makeKwArgs({ fields })
                    ),
                makeKwArgs({
                    predicate: (m) => m.guest_id !== null && m.guest_id !== undefined && m.guest_id,
                })
            ),
        ];
    }

    get _to_store_defaults() {
        return [
            mailDataHelpers.Store.one("channel_id", makeKwArgs({ as_thread: true, only_id: true })),
            "create_date",
            "fetched_message_id",
            "seen_message_id",
            "last_interest_dt",
            "last_seen_dt",
            "new_message_separator",
        ].concat(this._to_store_persona());
    }

    _get_store_partner_fields(fields) {
        return fields;
    }

    /**
     * @param {number[]} ids
     * @param {number} last_message_id
     */
    _mark_as_read(ids, last_message_id) {
        const kwargs = getKwArgs(arguments, "ids", "last_message_id", "sync");
        ids = kwargs.ids;
        delete kwargs.ids;
        last_message_id = kwargs.last_message_id;
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
            last_message_id + 1
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
                    [
                        mailDataHelpers.Store.one(
                            "channel_id",
                            makeKwArgs({ as_thread: true, only_id: true })
                        ),

                        "seen_message_id",
                    ].concat(this._to_store_persona())
                ).get_result()
            );
        }
    }

    /**
     * @param {number[]} ids
     * @param {number} message_id
     */
    _set_new_message_separator(ids, message_id) {
        const kwargs = getKwArgs(arguments, "ids", "message_id", "sync");
        ids = kwargs.ids;
        delete kwargs.ids;
        message_id = kwargs.message_id;

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
    }

    set_custom_notifications(ids, custom_notifications) {
        const kwargs = getKwArgs(arguments, "ids", "custom_notifications");
        ids = kwargs.ids;
        delete kwargs.ids;
        custom_notifications = kwargs.custom_notifications;

        /** @type {import("mock_models").DiscussChannelMember} */
        const DiscussChannelMember = this.env["discuss.channel.member"];

        const channelMememberId = ids[0]; // simulate ensure_one.
        DiscussChannelMember.write([channelMememberId], { custom_notifications });

        const [partner, guest] = this.env["res.partner"]._get_current_persona();
        this.env["bus.bus"]._sendone(
            guest ?? partner,
            "mail.record/insert",
            new mailDataHelpers.Store(
                DiscussChannelMember.browse(channelMememberId),
                "custom_notifications"
            ).get_result()
        );
    }
}
