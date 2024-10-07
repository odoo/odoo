import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("discuss_channel_call_action.js", {
    steps: () => [
        {
            content: "Check that the call has started",
            trigger: ".o-discuss-Call",
        },
        {
            content: "Check that current user is in call ('disconnect' button visible)",
            trigger: "button[title='Disconnect']",
        },
    ],
});
