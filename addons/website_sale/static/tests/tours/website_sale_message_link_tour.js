/** @odoo-module **/

import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("website_sale_message_link_tour", {
    steps: () => [
        {
            trigger: "#chatterRoot:shadow .o-mail-Message.o-highlighted:contains('Here is the pizza menu!')",
        },
    ],
});
