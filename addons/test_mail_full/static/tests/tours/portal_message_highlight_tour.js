import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("portal_message_highlight_tour", {
    steps: () => [
        {
            trigger: "#chatterRoot:shadow .o-mail-Message:contains(Test Message)",
        },
        {
            trigger: "#chatterRoot:shadow .o-highlighted:contains(Test Message)"
        },
    ],
});
