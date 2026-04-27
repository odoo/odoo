/** @odoo-module **/

import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("quick_check_in_tour", {
    steps: () => [
        {
            content: "Click on Check in",
            trigger: ".btn:contains('Check in')",
            run: "click",
        },
        {
            content: "Click on the planned user",
            trigger: ".visitor-card-body:contains('Tony Stark')",
            run: "click",
        },
        {
            content: "Check the button",
            trigger: ".btn-primary:contains('Yes, please')",
            run: "click",
        },
        {
            content: "Checking the message",
            trigger: "h1:contains('How can we delight you?')",
        },
        {
            content: "Going to the end page",
            trigger: "button:contains('Nothing, thanks.')",
            run: "click",
        },
        {
            content: "Check that we reached on the next page",
            trigger: "h1:contains('Thank you for registering!')",
        },
    ],
});
