import { mailModels } from "@mail/../tests/mail_test_helpers";
import { mailDataHelpers } from "@mail/../tests/mock_server/mail_mock_server";

import { serializeDate, today } from "@web/core/l10n/dates";

export class MailActivity extends mailModels.MailActivity {
    get_today_call_activities() {
        /** @type {import("mock_models").MailActivityType} */
        const MailActivityType = this.env["mail.activity.type"];
        const activityTypeIds = MailActivityType.search([["category", "=", "phonecall"]])[0];
        const store = new mailDataHelpers.Store();
        this._format_call_activities(
            this.search([
                ["activity_type_id", "in", activityTypeIds],
                ["user_id", "=", this.env.uid],
                ["date_deadline", "<=", serializeDate(today())],
            ]),
            store
        );
        return store.get_result();
    }

    /** @param {number[]} ids */
    _format_call_activities(ids, store) {
        /** @type {import("mock_models").ResUsers} */
        const ResUsers = this.env["res.users"];
        /** @type {import("mock_models").ResPartner} */
        const ResPartner = this.env["res.partner"];

        const activities = this.browse(ids);
        const now = serializeDate(today());
        for (const activity of activities) {
            const [user] = ResUsers.search_read([["id", "=", activity.user_id]]);
            const state =
                activity.date_deadline === now
                    ? "today"
                    : activity.date_deadline < now
                    ? "overdue"
                    : "planned";
            const [record] = this.env[activity.res_model].search_read([
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
                [relatedPartner] = ResPartner.search_read([["id", "=", activity.res_id]]);
            } else {
                if (record.partner_id) {
                    [relatedPartner] = ResPartner.search_read([["id", "=", record.partner_id]]);
                }
            }
            if (relatedPartner) {
                activityData.partner = mailDataHelpers.Store.one(
                    ResPartner.browse(relatedPartner.id)
                );
            }
            activityData.mobile = record.mobile || relatedPartner?.mobile;
            activityData.phone = record.phone || relatedPartner?.phone;
            store.add(this.browse(activity.id), activityData);
        }
    }
}
