/** @odoo-module **/

import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("frontdesk_basic_tour", {
    steps: () => [
        {
            content: "Check that the QR is there",
            trigger: "img",
        },
        {
            content: "Click on Check in",
            trigger: ".btn:contains('Check in')",
            run: "click",
        },
        {
            content: "Click on the back button",
            trigger: ".oi-arrow-left",
            run: "click",
        },
        {
            content: "Click on Check in",
            trigger: ".btn:contains('Check in')",
            run: "click",
        },
        {
            content: "Filling the details",
            trigger: "input#company",
            run: "edit Office",
        },
        {
            content: "Filling the details",
            trigger: "input#phone",
            run: "edit 1234567890",
        },
        {
            content: "Filling the details",
            trigger: "input#name",
            run: "edit Test_Tour_1",
        },
        {
            content: "Click on the check in button",
            trigger: ".btn-primary:contains('Check In')",
            run: "click",
        },
        {
            content: "Check that we reached on the last page",
            trigger: "h1:contains('You have been registered!')",
        },
    ],
});
