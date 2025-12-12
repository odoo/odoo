import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("portal_message_highlight_tour", {
    steps: () => [
        {
            trigger: "#chatterRoot:shadow .o-mail-Message.o-highlighted:has(:text(Test Message))"
        },
    ],
});
