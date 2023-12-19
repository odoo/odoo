/** @odoo-module alias=@mail/../tests/helpers/mock_server/models/res_users default=false */

import { patch } from "@web/core/utils/patch";
import { today, serializeDate } from "@web/core/l10n/dates";
import { MockServer } from "@web/../tests/helpers/mock_server";
import { DISCUSS_ACTION_ID } from "../../test_constants";

patch(MockServer.prototype, {
    /**
     * Simulates `_init_messaging` on `res.users`.
     *
     * @private
     * @param {integer[]} ids
     * @param {Object} context
     * @returns {Object}
     */
    _mockResUsers_InitMessaging(ids, context) {
        const user = this.getRecords("res.users", [["id", "in", ids]])[0];
        const userSettings = this._mockResUsersSettings_FindOrCreateForUser(user.id);
        const channels = this._mockDiscussChannel__get_channels_as_member();
        const members = this.getRecords("discuss.channel.member", [
            ["channel_id", "in", channels.map((channel) => channel.id)],
            ["partner_id", "=", user.partner_id],
        ]);
        return {
            CannedResponse: this.pyEnv["mail.shortcode"].searchRead([], {
                fields: ["source", "substitution"],
            }),
            Store: {
                action_discuss_id: DISCUSS_ACTION_ID,
                current_user_id: this.pyEnv.currentUserId,
                discuss: {
                    inbox: {
                        counter: this._mockResPartner_GetNeedactionCount(user.partner_id),
                        id: "inbox",
                        model: "mail.box",
                    },
                    starred: {
                        counter: this.getRecords("mail.message", [
                            ["starred_partner_ids", "in", user.partner_id],
                        ]).length,
                        id: "starred",
                        model: "mail.box",
                    },
                },
                hasGifPickerFeature: true,
                hasLinkPreviewFeature: true,
                hasMessageTranslationFeature: true,
                initBusId: this.lastBusNotificationId,
                initChannelsUnreadCounter: members.filter((member) => member.message_unread_counter)
                    .length,
                odoobot: this._mockResPartnerMailPartnerFormat(this.odoobotId).get(this.odoobotId),
                settings: this._mockResUsersSettings_ResUsersSettingsFormat(userSettings.id),
            },
            Thread: this._mockDiscussChannelChannelInfo(
                this._mockDiscussChannel__get_init_channels(user, context).map(
                    (channel) => channel.id
                )
            ),
        };
    },
    /**
     * Simulates `_get_activity_groups` on `res.users`.
     *
     * @private
     */
    _mockResUsers_getActivityGroups() {
        const activities = this.pyEnv["mail.activity"].searchRead([]);
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
    },
});
