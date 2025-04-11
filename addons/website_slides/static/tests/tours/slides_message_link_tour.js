/** @odoo-module **/

import { registry } from "@web/core/registry";

/**
 * This tour tests that a public user can not react to messages
 */
registry.category("web_tour.tours").add("slides_message_link_tour", {
    steps: () => [
        {
            trigger: "#chatterRoot:shadow .o-mail-Message.o-highlighted:contains('Here is the pizza menu!')",
        },
    ],
});
