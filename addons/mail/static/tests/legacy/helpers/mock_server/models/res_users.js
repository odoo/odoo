/** @odoo-module alias=@mail/../tests/helpers/mock_server/models/res_users default=false */

import { patch } from "@web/core/utils/patch";
import { today, serializeDate } from "@web/core/l10n/dates";
import { MockServer } from "@web/../tests/helpers/mock_server";
import { DISCUSS_ACTION_ID } from "../../test_constants";

patch(MockServer.prototype, {
    /** Simulates `_init_store_data` on `res.users`. */
    _mockResUsers__init_store_data() {
        const res = {
            Store: {
                action_discuss_id: DISCUSS_ACTION_ID,
                channel_types_with_seen_infos: this._mockDiscussChannel__typesAllowingSeenInfos(),
                hasGifPickerFeature: true,
                hasLinkPreviewFeature: true,
                hasMessageTranslationFeature: true,
                odoobot: this._mockResPartnerMailPartnerFormat(this.odoobotId).get(this.odoobotId),
            },
        };
        if (!this.pyEnv.currentUser._is_public()) {
            const userSettings = this._mockResUsersSettings_FindOrCreateForUser(
                this.pyEnv.currentUser.id
            );
            Object.assign(res.Store, {
                self: {
                    id: this.pyEnv.currentUser.partner_id,
                    isAdmin: true, // mock server simplification
                    isInternalUser: !this.pyEnv.currentUser.share,
                    name: this.pyEnv.currentUser.name,
                    notification_preference: this.pyEnv.currentUser.notification_type,
                    type: "partner",
                    userId: this.pyEnv.currentUser.id,
                    write_date: this.pyEnv.currentUser.write_date,
                },
                settings: this._mockResUsersSettings_ResUsersSettingsFormat(userSettings.id),
            });
        } else if (this.pyEnv.currentGuest) {
            Object.assign(res.Store, {
                self: {
                    id: this.pyEnv.currentGuest.id,
                    name: this.pyEnv.currentGuest.name,
                    type: "guest",
                    write_date: this.pyEnv.currentGuest.write_date,
                },
            });
        }
        return res;
    },
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
        const channels = this._mockDiscussChannel__get_channels_as_member();
        const members = this.getRecords("discuss.channel.member", [
            ["channel_id", "in", channels.map((channel) => channel.id)],
            ["partner_id", "=", user.partner_id],
        ]);
        const bus_last_id = this.lastBusNotificationId;
        return {
            Store: {
                discuss: {
                    inbox: {
                        counter: this._mockResPartner_GetNeedactionCount(user.partner_id),
                        counter_bus_id: bus_last_id,
                        id: "inbox",
                        model: "mail.box",
                    },
                    starred: {
                        counter: this.getRecords("mail.message", [
                            ["starred_partner_ids", "in", user.partner_id],
                        ]).length,
                        counter_bus_id: bus_last_id,
                        id: "starred",
                        model: "mail.box",
                    },
                },
                initChannelsUnreadCounter: members.filter((member) => member.message_unread_counter)
                    .length,
            },
        };
    },
    /**
     * Simulates `_get_activity_groups` on `res.users`.
     *
     * @private
     */
    _mockResUsers_getActivityGroups() {
        const activities = this.pyEnv["mail.activity"].search_read([]);
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
