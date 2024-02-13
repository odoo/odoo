/** @odoo-module */

import { webModels } from "@web/../tests/web_test_helpers";
import { serializeDate, today } from "@web/core/l10n/dates";

/**
 * @template T
 * @typedef {import("@web/../tests/web_test_helpers").KwArgs<T>} KwArgs
 */

export class ResUsers extends webModels.ResUsers {
    constructor() {
        super(...arguments);
        // this._records.push({
        //     id: constants.ODOOBOT_ID,
        //     active: false,
        //     login: "odoobot",
        //     partner_id: constants.ODOOBOT_ID,
        //     password: "odoobot",
        // });
    }
    /** @param {KwArgs} [kwargs] */
    systray_get_activities(kwargs = {}) {
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

    /** @param {number[]} ids */
    _init_messaging(ids) {
        /** @type {import("mock_models").DiscussChannel} */
        const DiscussChannel = this.env["discuss.channel"];
        /** @type {import("mock_models").DiscussChannelMember} */
        const DiscussChannelMember = this.env["discuss.channel.member"];
        /** @type {import("mock_models").MailMessage} */
        const MailMessage = this.env["mail.message"];
        /** @type {import("mock_models").MailShortcode} */
        const MailShortcode = this.env["mail.shortcode"];
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
        return {
            CannedResponse: MailShortcode.search_read([], {
                fields: ["source", "substitution"],
            }),
            Store: {
                discuss: {
                    inbox: {
                        counter: ResPartner._get_needaction_count(user.partner_id),
                        id: "inbox",
                        model: "mail.box",
                    },
                    starred: {
                        counter: MailMessage._filter([
                            ["starred_partner_ids", "in", user.partner_id],
                        ]).length,
                        id: "starred",
                        model: "mail.box",
                    },
                },
                initBusId: this.lastBusNotificationId,
                initChannelsUnreadCounter: members.filter((member) => member.message_unread_counter)
                    .length,
            },
        };
        // const Channel = this.env["discuss.channel"];
        // const Partner = this.env["res.partner"];
        // const Settings = this.env["res.users.settings"];

        // const [user] = this._filter([["id", "in", ids]]);
        // const userSettings = Settings.find_or_create_for_user(user.id);
        // const channels = Channel.get_channels_as_member();
        // const members = this.env["discuss.channel.member"]._filter([
        //     ["channel_id", "in", channels.map((channel) => channel.id)],
        //     ["partner_id", "=", user.partner_id],
        // ]);

        // return {
        //     CannedResponse: this.env["mail.shortcode"].search_read([], {
        //         fields: ["source", "substitution"],
        //     }),
        //     Store: {
        //         action_discuss_id: DISCUSS_ACTION_ID,
        //         current_user_id: this.env.uid,
        //         discuss: {
        //             inbox: {
        //                 counter: Partner._get_needaction_count(user.partner_id),
        //                 id: "inbox",
        //                 model: "mail.box",
        //             },
        //             starred: {
        //                 counter: this.env["mail.message"]._filter([
        //                     ["starred_partner_ids", "in", user.partner_id],
        //                 ]).length,
        //                 id: "starred",
        //                 model: "mail.box",
        //             },
        //         },
        //         hasGifPickerFeature: true,
        //         hasLinkPreviewFeature: true,
        //         hasMessageTranslationFeature: true,
        //         initBusId: this.lastBusNotificationId,
        //         initChannelsUnreadCounter: members.filter((member) => member.message_unread_counter)
        //             .length,
        //         menu_id: false, // not useful in QUnit tests
        //         odoobot: Partner.mail_partner_format(constants.ODOOBOT_ID)[constants.ODOOBOT_ID],
        //         self: Partner.mail_partner_format(user.partner_id)[user.partner_id],
        //         settings: Settings.res_users_settings_format(userSettings.id),
        //     },
        //     Thread: Channel.channel_info(
        //         Channel._getInitChannels(user).map((channel) => channel.id)
        //     ),
        // };
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
