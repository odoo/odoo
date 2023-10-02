/* @odoo-module */

import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("mail_activity_schedule_from_chatter", {
    test: true,
    steps: () => [
        {
            trigger: "button:contains('Activities')",
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
