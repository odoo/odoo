import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("mail_activity_schedule_from_chatter", {
    steps: () => [
        {
            trigger: "button:contains('Activity')",
            run: "click",
        },
        {
            trigger: ".o_selection_badge span:contains('Call')",
            run: "click",
        },
        {
            trigger: ".o_selection_badge.active span:contains('Call')",
        },
        {
            trigger: ".o_selection_badge span:contains('To-Do')",
            run: "click",
        },
        {
            trigger: "div[name='summary'] input",
            run: "edit Play Mario Party",
        },
        {
            trigger: "button:contains('Save')",
            run: "click",
        },
        {
            trigger: ".o-mail-Activity:contains('Play Mario Party')",
            run: "click",
        },
        {
            trigger: "button:contains('Activity')",
            run: "click",
        },
        {
            trigger: "div[name='summary'] input",
            run: "edit Play Mario Kart",
        },
        {
            trigger: "button.btn.btn-secondary:contains('Mark Done')",
            run: "click",
        },
        {
            trigger: ".o-mail-Message:contains('Play Mario Kart')",
        },
    ],
});
