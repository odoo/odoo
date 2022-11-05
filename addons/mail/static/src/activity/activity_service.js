/** @odoo-module */

import { reactive } from "@odoo/owl";
import { registry } from "@web/core/registry";

export const activityService = {
    dependencies: ["orm"],
    start(env, { orm }) {
        const state = reactive({
            counter: 0,
            activities: [],
        });

        // not waiting for this on purpose: we do not want to delay the web client
        orm.call("res.users", "systray_get_activities").then((activities) => {
            let total = 0;
            for (let activity of activities) {
                total += activity.total_count;
            }
            state.counter = total;
            state.activities = activities;
        });

        return state;
    },
};

registry.category("services").add("mail.activity", activityService);
