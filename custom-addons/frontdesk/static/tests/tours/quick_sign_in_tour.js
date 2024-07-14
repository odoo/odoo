/** @odoo-module **/

import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("quick_check_in_tour", {
    test: true,
    steps: () => [
        {
            content: "Click on Check in",
            trigger: ".btn:contains('Check in')",
        },
        {
            content: "Click on the planned user",
            trigger: ".visitor-card-body:contains('Tony Stark')",
        },
        {
            content: "Check the button",
            trigger: ".btn-primary:contains('Yes, please')",
        },
        {
            content: "Checking the message",
            trigger: "h1:contains('How can we delight you?')",
            isCheck: true,
        },
        {
            content: "Going to the end page",
            trigger: "button:contains('Nothing, thanks.')",
        },
        {
            content: "Check that we reached on the next page",
            trigger: "h1:contains('Thank you for registering!')",
            isCheck: true,
        },
    ],
});
