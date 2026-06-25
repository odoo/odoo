import { DISCUSS_ACTION_ID } from "@mail/../tests/mock_server/mail_mock_server";

import { fields, serverState, webModels } from "@web/../tests/web_test_helpers";
import { serializeDate, today } from "@web/core/l10n/dates";

export class ResUsers extends webModels.ResUsers {
    im_status = fields.Selection({
        selection: [
            ["online", "Online"],
            ["away", "Away"],
            ["busy", "Do Not Disturb"],
            ["offline", "Offline"],
        ],
        default: "online",
    });
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
        /** @type {import("mock_models").ResUsers} */
        const ResUsers = this.env["res.users"];
        /** @type {import("mock_models").ResUsersSettings} */
        const ResUsersSettings = this.env["res.users.settings"];
        /** @type {import("mock_models").MailMessageSubtype} */
        const MailMessageSubtype = this.env["mail.message.subtype"];
        store.add_global_values((res) => {
            res.attr("action_discuss_id", DISCUSS_ACTION_ID);
            res.attr("channel_types_with_seen_infos", DiscussChannel._types_allowing_seen_infos());
            res.attr("hasGifPickerFeature", true);
            res.attr("hasLinkPreviewFeature", true);
            res.attr("hasMessageTranslationFeature", true);
            res.attr(
                "mt_comment",
                MailMessageSubtype._filter([["subtype_xmlid", "=", "mail.mt_comment"]])[0].id
            );
            res.attr(
                "mt_note",
                MailMessageSubtype._filter([["subtype_xmlid", "=", "mail.mt_note"]])[0].id
            );
            res.one("odoobot", "_store_partner_fields", {
                value: ResPartner.browse(serverState.odoobotId),
            });
            if (!this._is_public(this.env.uid)) {
                const userSettings = ResUsersSettings._find_or_create_for_user(this.env.uid);
                res.one("self_user", "_store_init_fields", {
                    value: ResUsers.browse(this.env.user.id),
                });
                res.attr("settings", ResUsersSettings.res_users_settings_format(userSettings.id));
            } else if (this.env.cookie.get("dgid")) {
                res.one(
                    "self_guest",
                    (r) => {
                        r.from_method("_store_avatar_fields");
                        r.from_method("_store_im_status_fields");
                    },
                    { value: MailGuest.browse(this.env.cookie.get("dgid")) }
                );
            }
        });
    }

    /** mock simplification: admin is the user matching the authenticated admin session */
    _is_admin() {
        const users = this.env["res.users"].search([["login", "=", "admin"]]);
        const adminId = Number.isInteger(users?.[0]) ? users?.[0] : users?.[0]?.id;
        return this.env.cookie.get("authenticated_user_sid") === adminId;
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
     * @param {import("@mail/../tests/mock_server/store").Store} store
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
        store.add_global_values({
            inbox: {
                counter: ResPartner._get_needaction_count(user.partner_id),
                counter_bus_id: bus_last_id,
                id: "inbox",
                model: "mail.box",
            },
            bookmarkBox: {
                counter: MailMessage._filter([["bookmarked_partner_ids", "in", [user.partner_id]]])
                    .length,
                counter_bus_id: bus_last_id,
                id: "bookmark",
                model: "mail.box",
            },
            init_unread_channel_ids: members
                .filter((member) => member.message_unread_counter)
                .map((member) => member.channel_id),
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

    _store_avatar_card_fields(res) {
        res.attr("share");
        res.one("partner_id", "_store_avatar_card_fields");
        res.attr("is_public", (u) => this._is_public(u.id));
        res.from_method("_store_im_status_fields", { internal: true });
    }

    _store_im_status_fields(res) {
        res.attr("im_status");
        res.attr("im_status_access_token", (p) => p.id); // mock: token is the record id
        res.one("partner_id", "_store_im_status_fields");
    }

    _store_manual_im_status_fields(res) {
        res.attr("im_status");
    }

    _store_main_user_fields(res) {
        res.extend(["active", "partner_id", "share"]);
    }

    _store_init_fields(res) {
        res.one("partner_id", (r) => {
            r.records._compute_main_user_id(); // compute not automatically triggering
            r.extend(["active", "name", "tz"]);
            r.one("main_user_id", ["partner_id"]);
            r.many("user_ids", ["active", "company_ids", "share"], { internal: true, sudo: true });
            r.from_method("_store_avatar_fields");
        });
        res.attr("is_admin", () => this._is_admin());
        res.extend(["notification_type", "share", "signature"]);
        res.from_method("_store_im_status_fields");
    }

    _store_user_fields(res) {
        res.one("partner_id", "_store_partner_fields");
    }
}
