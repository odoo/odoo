/* @odoo-module */

import { patch } from "@web/core/utils/patch";
import { today, serializeDate } from "@web/core/l10n/dates";
import { MockServer } from "@web/../tests/helpers/mock_server";
import { DISCUSS_ACTION_ID } from "../../test_constants";

patch(MockServer.prototype, {
    async _performRPC(route, args) {
        if (args.model === "res.users" && args.method === "systray_get_activities") {
            return this._mockResUsersSystrayGetActivities();
        }
        return super._performRPC(route, args);
    },
    /**
     * Simulates `_init_messaging` on `res.users`.
     *
     * @private
     * @param {integer[]} ids
     * @returns {Object}
     */
    _mockResUsers_InitMessaging(ids) {
        const user = this.getRecords("res.users", [["id", "in", ids]])[0];
        const userSettings = this._mockResUsersSettings_FindOrCreateForUser(user.id);
        return {
            action_discuss_id: DISCUSS_ACTION_ID,
            channels: this._mockDiscussChannelChannelInfo(
                this._mockResPartner_GetChannelsAsMember(user.partner_id).map(
                    (channel) => channel.id
                )
            ),
            current_partner: this._mockResPartnerMailPartnerFormat(user.partner_id).get(
                user.partner_id
            ),
            current_user_id: this.pyEnv.currentUserId,
            current_user_settings: this._mockResUsersSettings_ResUsersSettingsFormat(
                userSettings.id
            ),
            hasGifPickerFeature: true,
            hasMessageTranslationFeature: true,
            initBusId: this.lastBusNotificationId,
            needaction_inbox_counter: this._mockResPartner_GetNeedactionCount(user.partner_id),
            odoobot: this._mockResPartnerMailPartnerFormat(this.odoobotId).get(this.odoobotId),
            shortcodes: this.pyEnv["mail.shortcode"].searchRead([], {
                fields: ["source", "substitution"],
            }),
            starred_counter: this.getRecords("mail.message", [
                ["starred_partner_ids", "in", user.partner_id],
            ]).length,
            hasLinkPreviewFeature: true,
        };
    },
    /**
     * Simulates `systray_get_activities` on `res.users`.
     *
     * @private
     */
    _mockResUsersSystrayGetActivities() {
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
