import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("mail_activity_schedule_from_chatter", {
    steps: () => [
        {
            trigger: "button:contains('Activities')",
            run: "click",
        },
        {
            trigger: "input[id*='activity_type_id']",
            run: "click",
        },
        {
            trigger: ".dropdown-item:contains('Call')",
            run: "click",
        },
        {
            trigger: "input[id*='activity_type_id']:value('Call')",
        },
        {
            trigger: "button:contains('Schedule')",
        },
        {
            trigger: "input[id*='activity_type_id']",
            run: "click",
        },
        {
            trigger: ".dropdown-item:contains('To-Do')",
            run: "click",
        },
        {
            trigger: "div[name='summary'] input",
            run: "edit Play Mario Party",
        },
        {
            trigger: "button:contains('Schedule')",
            run: "click",
        },
        {
            trigger: ".o-mail-Activity:contains('Play Mario Party')",
            run: "click",
        },
        {
            trigger: "button:contains('Activities')",
            run: "click",
        },
        {
            trigger: "div[name='summary'] input",
            run: "edit Play Mario Kart",
        },
        {
            trigger: "button:contains('Mark as Done')",
            run: "click",
        },
        {
            trigger: ".o-mail-Message:contains('Play Mario Kart')",
        },
    ],
});
