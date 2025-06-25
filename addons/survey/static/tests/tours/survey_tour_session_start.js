/** @odoo-module **/

import { registry } from "@web/core/registry";
import { accessSurveysteps } from "./survey_tour_session_tools";

/**
 * Small tour that will open the session manager and check
 * that the attendees are accounted for, then start the session
 * by going to the first question.
 */
registry.category("web_tour.tours").add('test_survey_session_start_tour', {
    url: "/odoo",
    steps: () => [].concat(accessSurveysteps, [{
    trigger: 'button[name="action_open_session_manager"]',
    run: "click",
}, {
    trigger: '.o_survey_session_attendees_count:contains("3")',
    run: function () {
        /* We want to test 2 things: (1) that the attendees count is right
           on the rendered xml template and (2) that the attendees count
           gets correctly updated every 2 seconds via JS.

           This step did verify the one on the xml template, we now change
           the value back to 0 to test that in 2 seconds it'll be updated
           by JS.

           The "waitrpc" class just serves to rule out concurrency issues
           between this step's run and the next step's trigger. */
        const elem = document.querySelector('.o_survey_session_attendees_count');
        elem.classList.add("waitrpc");
        elem.textContent = '0';
    }
}, {
    trigger: '.o_survey_session_attendees_count.waitrpc:contains("3")',
}, {
    trigger: 'h1',
    run: "press ArrowRight",
}, {
    trigger: 'h1:contains("Nickname")',
}])});
