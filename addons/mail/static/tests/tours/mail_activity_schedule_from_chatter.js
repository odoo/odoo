/* @odoo-module */

import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("mail_activity_schedule_from_chatter", {
    test: true,
    steps: () => [
        {
            trigger: "button:contains('Activities')",
        },
        {
            trigger: "input[id*='activity_type_id']",
            run: "click",
        },
        {
            trigger: ".dropdown-item:contains('Call')",
        },
        {
            extra_trigger: "button:contains('Schedule')",
            trigger: "input[id*='activity_type_id']",
            run: function (action_helper) {
                setTimeout(() => action_helper.click(), 100);
            },
        },
        {
            trigger: ".dropdown-item:contains('To-Do')",
        },
        {
            trigger: "div[name='summary'] input",
            run: "text Play Mario Party",
        },
        {
            trigger: "button:contains('Schedule')",
        },
        {
            trigger: ".o-mail-Activity:contains('Play Mario Party')",
        },
        {
            trigger: "button:contains('Activities')",
        },
        {
            trigger: "div[name='summary'] input",
            run: "text Play Mario Kart",
        },
        {
            trigger: "button:contains('Mark as Done')",
        },
        {
            trigger: ".o-mail-Message:contains('Play Mario Kart')",
            isCheck: true,
        },
    ],
});
