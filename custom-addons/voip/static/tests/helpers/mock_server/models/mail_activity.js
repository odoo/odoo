/* @odoo-module */

import "@mail/../tests/helpers/mock_server/models/mail_activity"; // ensure mail overrides are applied first

import { patch } from "@web/core/utils/patch";
import { serializeDate, today } from "@web/core/l10n/dates";
import { MockServer } from "@web/../tests/helpers/mock_server";

patch(MockServer.prototype, {
    /**
     * @override
     */
    async _performRPC(_route, { model, method, args, kwargs }) {
        if (model !== "mail.activity") {
            return super._performRPC(...arguments);
        }
        switch (method) {
            case "get_today_call_activities":
                return this._mockMailActivityGetTodayCallActivities(...args, kwargs);
            default:
                return super._performRPC(...arguments);
        }
    },
    _mockMailActivityGetTodayCallActivities() {
        const activityTypeIds = this.pyEnv["mail.activity.type"].search([
            ["category", "=", "phonecall"],
        ]);
        return this._mockMailActivity_FormatCallActivities(
            this.getRecords("mail.activity", [
                ["activity_type_id", "in", activityTypeIds],
                ["user_id", "=", this.pyEnv.currentUserId],
                ["date_deadline", "<=", serializeDate(today())],
            ])
        );
    },
    _mockMailActivity_FormatCallActivities(activities) {
        const formattedActivities = [];
        for (const activity of activities) {
            const [user] = this.pyEnv["res.users"].searchRead([["id", "=", activity.user_id]]);
            const state = (() => {
                const now = serializeDate(today());
                if (activity.date_deadline === now) {
                    return "today";
                } else if (activity.date_deadline < now) {
                    return "overdue";
                } else {
                    return "planned";
                }
            })();
            const [record] = this.pyEnv[activity.res_model].searchRead([
                ["id", "=", activity.res_id],
            ]);
            const activityData = {
                id: activity.id,
                activity_category: "phonecall",
                res_id: activity.res_id,
                res_model: activity.res_model,
                res_name: activity.res_name || record.display_name,
                state,
                user_id: [activity.user_id, user.name],
            };
            let relatedPartner;
            if (activity.res_model === "res.partner") {
                [relatedPartner] = this.getRecords("res.partner", [["id", "=", activity.res_id]]);
            } else {
                if (record.partner_id) {
                    [relatedPartner] = this.getRecords("res.partner", [
                        ["id", "=", record.partner_id],
                    ]);
                }
            }
            if (relatedPartner) {
                activityData.partner = this._mockResPartnerMailPartnerFormat([
                    relatedPartner.id,
                ]).get(relatedPartner.id);
            }
            activityData.mobile = record.mobile || relatedPartner?.mobile;
            activityData.phone = record.phone || relatedPartner?.phone;
            formattedActivities.push(activityData);
        }
        return formattedActivities;
    },
});
