/** @odoo-module */

import { Activity } from "@mail/core/web/activity_model";

import { patch } from "@web/core/utils/patch";

patch(Activity, {
    _insert(data) {
        const activity = super._insert(...arguments);
        if ("approver_id" in data && "approver_status" in data) {
            if (!data.approver_id) {
                delete activity.approval;
            } else {
                activity.approval = { id: data.approver_id, status: data.approver_status };
            }
        }
        return activity;
    },
});
