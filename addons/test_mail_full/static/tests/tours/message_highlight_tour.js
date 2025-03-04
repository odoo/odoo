import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("highlight_portal_message", {
    steps: () => [
        {
            trigger: "#chatterRoot:shadow .o-mail-Message:contains(Test Message)",
        },
        {
            trigger: "#chatterRoot:shadow .o-highlighted:contains(Test Message)"
        },
    ],
});
