import { DISCUSS_ACTION_ID, mailDataHelpers } from "@mail/../tests/mock_server/mail_mock_server";

import { fields, makeKwArgs, serverState, webModels } from "@web/../tests/web_test_helpers";
import { serializeDate, today } from "@web/core/l10n/dates";

export class ResUsers extends webModels.ResUsers {
    im_status = fields.Char({ default: "online" });
    notification_type = fields.Selection({
        selection: [
            ["email", "Handle by Emails"],
            ["inbox", "Handle in Odoo"],
        ],
        default: "email",
    });
    role_ids = fields.Many2many({ relation: "res.role", string: "Roles" });

    /** Simulates `_init_store_data` on `res.users`. */
    _init_store_data(store) {
        /** @type {import("mock_models").DiscussChannel} */
        const DiscussChannel = this.env["discuss.channel"];
        /** @type {import("mock_models").MailGuest} */
        const MailGuest = this.env["mail.guest"];
        /** @type {import("mock_models").ResPartner} */
        const ResPartner = this.env["res.partner"];
        /** @type {import("mock_models").ResUsersSettings} */
        const ResUsersSettings = this.env["res.users.settings"];
        /** @type {import("mock_models").MailMessageSubtype} */
        const MailMessageSubtype = this.env["mail.message.subtype"];
        store.add({
            action_discuss_id: DISCUSS_ACTION_ID,
            channel_types_with_seen_infos: DiscussChannel._types_allowing_seen_infos(),
            hasGifPickerFeature: true,
            hasLinkPreviewFeature: true,
            hasMessageTranslationFeature: true,
            mt_comment: MailMessageSubtype._filter([["subtype_xmlid", "=", "mail.mt_comment"]])[0]
                .id,
            mt_note: MailMessageSubtype._filter([["subtype_xmlid", "=", "mail.mt_note"]])[0].id,
            odoobot: mailDataHelpers.Store.one(ResPartner.browse(serverState.odoobotId)),
        });
        if (!this._is_public(this.env.uid)) {
            const userSettings = ResUsersSettings._find_or_create_for_user(this.env.uid);
            store.add({
                self_partner: mailDataHelpers.Store.one(
                    ResPartner.browse(this.env.user.partner_id),
                    makeKwArgs({
                        fields: [
                            "active",
                            "avatar_128",
                            "im_status",
                            "is_admin",
                            mailDataHelpers.Store.one("main_user_id", ["notification_type"]),
                            "name",
                            "notification_type",
                            "user",
                        ],
                    })
                ),
                settings: ResUsersSettings.res_users_settings_format(userSettings.id),
            });
        } else if (this.env.cookie.get("dgid")) {
            store.add({
                self_guest: mailDataHelpers.Store.one(
                    MailGuest.browse(this.env.cookie.get("dgid")),
                    makeKwArgs({ fields: ["avatar_128", "name"] })
                ),
            });
        }
    }
    systray_get_activities() {
        /** @type {import("mock_models").MailActivity} */
        const MailActivity = this.env["mail.activity"];

        const activities = MailActivity.search_read([]);
        const userActivitiesByModelName = {};
        for (const activity of activities) {
            const day = serializeDate(today());
            if (day === activity["date_deadline"]) {
                activity["states"] = "today";
            } else if (day > activity["date_deadline"]) {
                activity["states"] = "overdue";
            } else {
                activity["states"] = "planned";
            }
        }
        for (const activity of activities) {
            const modelName = activity["res_model"];
            if (!userActivitiesByModelName[modelName]) {
                userActivitiesByModelName[modelName] = {
                    id: modelName, // for simplicity
                    model: modelName,
                    name: modelName,
                    overdue_count: 0,
                    planned_count: 0,
                    today_count: 0,
                    total_count: 0,
                    type: "activity",
                };
            }
            userActivitiesByModelName[modelName][`${activity["states"]}_count`] += 1;
            userActivitiesByModelName[modelName]["total_count"] += 1;
            userActivitiesByModelName[modelName].actions = [
                {
                    icon: "fa-clock-o",
                    name: "Summary",
                },
            ];
        }
        return Object.values(userActivitiesByModelName);
    }

    /**
     * @param {number[]} ids
     * @param {import("@mail/../tests/mock_server/mail_mock_server").mailDataHelpers.Store} store
     **/
    _init_messaging(ids, store) {
        /** @type {import("mock_models").DiscussChannel} */
        const DiscussChannel = this.env["discuss.channel"];
        /** @type {import("mock_models").DiscussChannelMember} */
        const DiscussChannelMember = this.env["discuss.channel.member"];
        /** @type {import("mock_models").MailMessage} */
        const MailMessage = this.env["mail.message"];
        /** @type {import("mock_models").ResPartner} */
        const ResPartner = this.env["res.partner"];
        /** @type {import("mock_models").ResUsers} */
        const ResUsers = this.env["res.users"];

        const [user] = ResUsers.browse(ids);
        const channels = DiscussChannel._get_channels_as_member();
        const members = DiscussChannelMember._filter([
            ["channel_id", "in", channels.map((channel) => channel.id)],
            ["partner_id", "=", user.partner_id],
        ]);
        const bus_last_id = this.env["bus.bus"].lastBusNotificationId;
        store.add({
            inbox: {
                counter: ResPartner._get_needaction_count(user.partner_id),
                counter_bus_id: bus_last_id,
                id: "inbox",
                model: "mail.box",
            },
            starred: {
                counter: MailMessage._filter([["starred_partner_ids", "in", user.partner_id]])
                    .length,
                counter_bus_id: bus_last_id,
                id: "starred",
                model: "mail.box",
            },
            initChannelsUnreadCounter: members.filter((member) => member.message_unread_counter)
                .length,
        });
    }

    _get_activity_groups() {
        /** @type {import("mock_models").MailActivity} */
        const MailActivity = this.env["mail.activity"];

        const activities = MailActivity.search_read([]);
        const userActivitiesByModelName = {};
        for (const activity of activities) {
            const day = serializeDate(today());
            if (day === activity["date_deadline"]) {
                activity["states"] = "today";
            } else if (day > activity["date_deadline"]) {
                activity["states"] = "overdue";
            } else {
                activity["states"] = "planned";
            }
        }
        for (const activity of activities) {
            const modelName = activity["res_model"];
            if (!userActivitiesByModelName[modelName]) {
                userActivitiesByModelName[modelName] = {
                    id: modelName, // for simplicity
                    model: modelName,
                    name: modelName,
                    domain:
                        modelName && "active" in this.env[modelName]._fields
                            ? [["active", "in", [true, false]]]
                            : [],
                    overdue_count: 0,
                    planned_count: 0,
                    today_count: 0,
                    total_count: 0,
                    type: "activity",
                };
            }
            userActivitiesByModelName[modelName][`${activity["states"]}_count`] += 1;
            userActivitiesByModelName[modelName]["total_count"] += 1;
            userActivitiesByModelName[modelName].actions = [
                {
                    icon: "fa-clock-o",
                    name: "Summary",
                },
            ];
        }
        return Object.values(userActivitiesByModelName);
    }

    _get_store_avatar_card_fields() {
        return [
            "share",
            mailDataHelpers.Store.one(
                "partner_id",
                this.env["res.partner"]._get_store_avatar_card_fields()
            ),
        ];
    }
}
