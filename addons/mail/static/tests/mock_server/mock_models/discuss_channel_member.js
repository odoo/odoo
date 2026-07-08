import { Store } from "@mail/../tests/mock_server/store";

import { fields, getKwArgs, models } from "@web/../tests/web_test_helpers";
import { serializeDateTime, today } from "@web/core/l10n/dates";
import { ensureArray } from "@web/core/utils/arrays";

const { DateTime } = luxon;

export class DiscussChannelMember extends models.ServerModel {
    _name = "discuss.channel.member";

    is_pinned = fields.Generic({ compute: "_compute_is_pinned" });
    is_self = fields.Boolean({ compute: "_compute_is_self" });
    unpin_dt = fields.Datetime({ string: "Unpin date" });
    message_unread_counter = fields.Generic({ default: 0 });
    last_interest_dt = fields.Datetime({
        default: () => serializeDateTime(today().minus({ seconds: 1 })),
    });

    create(values) {
        const idOrIds = super.create(values);
        this.env["discuss.channel"]._compute_channel_name_member_ids();
        const channels_needing_name_update = this.env["discuss.channel"]
            ._filter([
                ["channel_name_member_ids", "in", ensureArray(idOrIds)],
                ["name", "=", false],
                [
                    "channel_type",
                    "in",
                    this.env["discuss.channel"]._member_based_naming_channel_types(),
                ],
            ])
            .filter((channel) => channel.channel_name_member_ids.length <= 3);
        for (const channel of channels_needing_name_update) {
            const store = new Store().add(this.env["discuss.channel"].browse(channel.id), (res) =>
                res.many("channel_name_member_ids", "_store_member_fields", { sort: "id" })
            );
            this.env["bus.bus"]._sendone(channel, "mail.record/insert", store.as_dict());
        }
        return idOrIds;
    }

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
                const store = new Store();
                diff.push("channel", "persona");
                store.add(this.browse(member.id), (res) => this._store_sync_fields(res, diff));
                const [partner, guest] = this.env["res.partner"]._get_current_persona();
                const busChannel = guest ?? partner;
                this.env["bus.bus"]._sendone(busChannel, "mail.record/insert", store.as_dict());
            }
        }
        return result;
    }

    _sync_field_names() {
        return [
            "channel_role",
            "is_favorite",
            "last_interest_dt",
            "message_unread_counter",
            "new_message_separator",
            "unpin_dt",
        ];
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
                new Store()
                    .add(DiscussChannelMember.browse(member.id), (res) => {
                        res.from_method("_store_member_fields");
                        res.attr("isTyping", is_typing);
                        res.attr("is_typing_dt", serializeDateTime(DateTime.now()));
                    })
                    .as_dict(),
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

    _compute_is_self() {
        const [partner, guest] = this.env["res.partner"]._get_current_persona();
        for (const member of this) {
            member.is_self = member.partner_id
                ? member.partner_id === partner?.id
                : member.guest_id === guest?.id;
        }
    }

    _compute_message_unread_counter() {
        for (const member of this) {
            this.write([member.id], {
                message_unread_counter: this.env["mail.message"].search_count([
                    ["res_id", "=", member.channel_id],
                    ["model", "=", "discuss.channel"],
                    ["id", ">=", member.new_message_separator],
                ]),
            });
        }
    }

    _store_avatar_card_fields(res) {
        res.attr("channel_id");
        this._store_persona(res, {
            partner_fields: (res) => {
                res.attr("name");
                res.from_method("_store_avatar_fields");
                res.from_method("_store_im_status_fields", { internal: true });
                res.from_method("_store_mention_fields");
            },
            guest_fields: (res) => {
                res.from_method("_store_avatar_fields");
                res.from_method("_store_im_status_fields", { internal: true });
            },
        });
    }

    _store_guest_dynamic_fields(res) {}

    _store_partner_dynamic_fields(res) {}

    _store_persona_default_fields(res) {
        res.attr("channel_id");
        this._store_persona(res, {
            partner_fields: (res) => {
                res.from_method("_store_partner_fields");
                res.from_method("_store_mention_fields");
            },
            guest_fields: (res) => {
                res.from_method("_store_avatar_fields");
                res.from_method("_store_im_status_fields", { internal: true });
            },
        });
    }

    _store_identifying_fields(res) {
        res.attr("channel_id");
        this._store_persona(res, { partner_fields: [], guest_fields: [] });
    }

    _store_persona(res, { partner_fields, guest_fields } = {}) {
        // sudo: res.partner - reading partner related to a member is considered acceptable
        res.one("partner_id", partner_fields, {
            dynamic_fields: "_store_partner_dynamic_fields",
            predicate: (m) => m.partner_id !== null && m.partner_id !== undefined && m.partner_id,
            sudo: true,
        });
        // sudo: mail.guest - reading guest related to a member is considered acceptable
        res.one("guest_id", guest_fields, {
            dynamic_fields: "_store_guest_dynamic_fields",
            predicate: (m) => m.guest_id !== null && m.guest_id !== undefined && m.guest_id,
            sudo: true,
        });
    }

    _store_seen_fields(res) {
        res.attr("seen_message_id");
        this._store_avatar_card_fields(res);
    }

    _store_member_fields(res) {
        // sudo: discuss.channel.member - reading channel ownership related to a member is considered acceptable
        res.attr("channel_role", undefined, { sudo: true });
        res.extend(["create_date", "last_seen_dt", "seen_message_id"]);
        this._store_persona_default_fields(res);
    }

    /** Mock counterpart of bus.sync.mixin: applies the sync diff computed by `write`. */
    _store_sync_fields(res, fields) {
        res.extend(
            fields.filter(
                (field) => !["channel", "message_unread_counter", "persona"].includes(field)
            )
        );
        if (fields.includes("message_unread_counter")) {
            this._compute_message_unread_counter();
            res.attr("message_unread_counter", (m) => m.message_unread_counter);
            res.attr("message_unread_counter_bus_id", this.env["bus.bus"].lastBusNotificationId);
        }
        if (fields.includes("channel")) {
            res.attr("channel_id");
        }
        if (fields.includes("persona")) {
            this._store_persona(res, {
                partner_fields: (res) => {
                    res.from_method("_store_partner_fields");
                    res.from_method("_store_mention_fields");
                },
                guest_fields: (res) => {
                    res.from_method("_store_avatar_fields");
                    res.from_method("_store_im_status_fields", { internal: true });
                },
            });
        }
    }

    /**
     * @param {number[]} ids
     * @param {boolean} [pinned=false]
     */
    _channel_pin(ids, pinned) {
        const kwargs = getKwArgs(arguments, "ids", "pinned");
        ids = kwargs.ids;
        delete kwargs.ids;
        pinned = kwargs.pinned ?? false;

        /** @type {import("mock_models").BusBus} */
        const BusBus = this.env["bus.bus"];
        /** @type {import("mock_models").DiscussChannel} */
        const DiscussChannel = this.env["discuss.channel"];
        /** @type {import("mock_models").DiscussChannelMember} */
        const DiscussChannelMember = this.env["discuss.channel.member"];
        /** @type {import("mock_models").ResPartner} */
        const ResPartner = this.env["res.partner"];

        const members = this.browse(ids);
        for (const member of members) {
            if (member && member.is_pinned !== pinned) {
                DiscussChannelMember.write([member.id], {
                    unpin_dt: pinned ? false : serializeDateTime(DateTime.now()),
                });
            }
            const [partner] = ResPartner.read(this.env.user.partner_id);
            if (!pinned) {
                BusBus._sendone(
                    partner,
                    "mail.record/insert",
                    new Store().add(DiscussChannel.browse(member.channel_id), []).as_dict()
                );
            } else {
                BusBus._sendone(
                    partner,
                    "mail.record/insert",
                    new Store()
                        .add(DiscussChannel.browse(member.channel_id), "_store_channel_fields")
                        .as_dict()
                );
            }
        }
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
        DiscussChannelMember.write([member.id], { seen_message_id: message_id });
        this._compute_message_unread_counter();
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
                new Store()
                    .add(DiscussChannelMember.browse(member.id), "_store_seen_fields")
                    .as_dict()
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
        this._compute_message_unread_counter();
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
            new Store()
                .add(DiscussChannelMember.browse(channelMememberId), ["custom_notifications"])
                .as_dict()
        );
    }
}
