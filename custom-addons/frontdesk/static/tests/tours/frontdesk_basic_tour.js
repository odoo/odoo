/** @odoo-module **/

import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("frontdesk_basic_tour", {
    test: true,
    steps: () => [
        {
            content: "Check that the QR is there",
            trigger: "img",
            isCheck: true,
        },
        {
            content: "Click on Check in",
            trigger: ".btn:contains('Check in')",
        },
        {
            content: "Click on the back button",
            trigger: ".oi-arrow-left",
        },
        {
            content: "Click on Check in",
            trigger: ".btn:contains('Check in')",
        },
        {
            content: "Filling the details",
            trigger: "input#company",
            run: "text Office",
        },
        {
            content: "Filling the details",
            trigger: "input#phone",
            run: "text 1234567890",
        },
        {
            content: "Filling the details",
            trigger: "input#name",
            run: "text Test_Tour_1",
        },
        {
            content: "Click on the check in button",
            trigger: ".btn-primary:contains('Check In')",
        },
        {
            content: "Check that we reached on the last page",
            trigger: "h1:contains('You have been registered!')",
            isCheck: true,
        },
    ],
});
