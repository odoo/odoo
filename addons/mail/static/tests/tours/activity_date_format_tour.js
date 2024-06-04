/** @odoo-module **/

import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("mail_activity_date_format", {
    test: true,
    steps: () => [
        {
            trigger: "button:contains('Activities')",
        },
        {
            trigger: "input[id*='activity_type_id']",
            run: "click",
        },
        {
            trigger: ".dropdown-item:contains('To-Do')",
        },
        {
            trigger: "div[name='summary'] input",
            run: "text Go Party",
        },
        {
            trigger: "button:contains('Schedule')",
        },
        {
            trigger: ".o-mail-Activity:contains('Go Party')",
        },
        {
            trigger: ".fa-info-circle",
            run: "click",
        },
        // Format expected from the server for 9 AM at the first day of 2024 is date_format = "%d/%b/%y", time_format = "%I:%M:%S %p".
        {
            trigger: ".o-mail-Activity-details tr:contains('Created') td:contains('01/Jan/24 09:00:00 AM')",
            isCheck: true,
        },
        {
            // Default due date is 5 days after creation date.
            trigger: ".o-mail-Activity-details tr:contains('Due on') td:contains('06/Jan/24')",
            isCheck: true,
        }
    ],
});
