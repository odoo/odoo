import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("message_link_tour", {
    steps: () => [
        {
            trigger: ".o-mail-Message.o-highlighted:contains('Here is the pizza menu')",
        },
    ],
});
