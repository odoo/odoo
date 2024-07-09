import { fields, serverState, webModels } from "@web/../tests/web_test_helpers";
import { serializeDate, today } from "@web/core/l10n/dates";
import { DISCUSS_ACTION_ID } from "../mail_mock_server";

export class ResUsers extends webModels.ResUsers {
    im_status = fields.Char({ default: "online" });
    notification_type = fields.Selection({
        selection: [
            ["email", "Handle by Emails"],
            ["inbox", "Handle in Odoo"],
        ],
        default: "email",
    });

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

        store.add(ResPartner.browse(serverState.odoobotId));
        store.add({
            action_discuss_id: DISCUSS_ACTION_ID,
            channel_types_with_seen_infos: DiscussChannel._types_allowing_seen_infos(),
            hasGifPickerFeature: true,
            hasLinkPreviewFeature: true,
            hasMessageTranslationFeature: true,
            odoobot: { id: serverState.odoobotId, type: "partner" },
        });
        if (!this._is_public(this.env.uid)) {
            const userSettings = ResUsersSettings._find_or_create_for_user(this.env.uid);
            store.add("Persona", {
                id: this.env.user?.partner_id,
                isAdmin: true, // mock server simplification
                active: true,
                isInternalUser: !this.env.user?.share,
                name: this.env.user?.name,
                notification_preference: this.env.user?.notification_type,
                type: "partner",
                userId: this.env.user?.id,
                write_date: this.env.user?.write_date,
            });
            store.add({
                self: { id: this.env.user?.partner_id, type: "partner" },
                settings: ResUsersSettings.res_users_settings_format(userSettings.id),
            });
        } else if (this.env.cookie.get("dgid")) {
            const [guest] = MailGuest.read(this.env.cookie.get("dgid"));
            store.add("Persona", {
                id: guest.id,
                name: guest.name,
                type: "guest",
                write_date: guest.write_date,
            });
            store.add({ self: { id: guest.id, type: "guest" } });
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

        const user = ResUsers._filter([["id", "in", ids]])[0];
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
}
