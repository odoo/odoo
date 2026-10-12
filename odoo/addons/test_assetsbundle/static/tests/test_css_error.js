import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("css_error_tour", {
    steps: () => [
        {
            content: "Error message",
            trigger: ".o_notification:has(.o_notification_bar.bg-danger)",
        },
        {
            trigger: ".o_notification:contains('Style error')",
        },
    ],
});

registry.category("web_tour.tours").add("css_error_tour_frontend", {
    steps: () => [
        {
            content: "Error message",
            trigger: ".o_notification:has(.o_notification_bar.bg-danger)",
        },
        {
            trigger: ".o_notification:contains('Style error')",
        },
    ],
});
