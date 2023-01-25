/** @odoo-module */

import { Activity } from "./activity_model";
import { _t } from "@web/core/l10n/translation";
import { assignDefined } from "../utils/misc";
import { registry } from "@web/core/registry";

export class ActivityService {
    constructor(env, services) {
        this.env = env;
        /** @type {import("@mail/new/core/store_service").Store} */
        this.store = services["mail.store"];
        this.orm = services.orm;
    }

    /**
     * @param {import("./activity_model").Activity} activity
     * @param {number[]} attachmentIds
     */
    async markAsDone(activity, attachmentIds = []) {
        await this.orm.call("mail.activity", "action_feedback", [[activity.id]], {
            attachment_ids: attachmentIds,
            feedback: activity.feedback,
        });
    }

    async schedule(resModel, resId, activityId = false, defaultActivityTypeId = undefined) {
        const context = {
            default_res_model: resModel,
            default_res_id: resId,
        };
        if (defaultActivityTypeId !== undefined) {
            context.default_activity_type_id = defaultActivityTypeId;
        }
        return new Promise((resolve) => {
            this.env.services.action.doAction(
                {
                    type: "ir.actions.act_window",
                    name: _t("Schedule Activity"),
                    res_model: "mail.activity",
                    view_mode: "form",
                    views: [[false, "form"]],
                    target: "new",
                    context,
                    res_id: activityId,
                },
                { onClose: resolve }
            );
        });
    }

    /**
     * @param {import("./activity_model").Data} data
     * @returns {import("./activity_model").Activity}
     */
    insert(data) {
        const activity = this.store.activities[data.id] ?? new Activity(this.store, data.id);
        if (data.request_partner_id) {
            data.request_partner_id = data.request_partner_id[0];
        }
        assignDefined(activity, data);
        return activity;
    }

    delete(activity) {
        delete this.store.activities[activity.id];
    }
}

export const activityService = {
    dependencies: ["mail.store", "orm"],
    start(env, services) {
        return new ActivityService(env, services);
    },
};

registry.category("services").add("mail.activity", activityService);
