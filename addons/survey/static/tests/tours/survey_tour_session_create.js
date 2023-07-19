/** @odoo-module **/

import { registry } from "@web/core/registry";
import { accessSurveysteps } from "./survey_tour_session_tools";

/**
 * Small tour that will simply start the session and wait for attendees.
 */
registry.category("web_tour.tours").add("test_survey_session_create_tour", {
    url: "/web",
    test: true,
    steps: () => {
        return [
            ...accessSurveysteps,
            {
                trigger: 'button[name="action_start_session"]',
            },
            {
                trigger: '.o_survey_session_attendees_count:contains("0")',
                run: function () {}, // check session is correctly started
            },
        ];
    },
});
