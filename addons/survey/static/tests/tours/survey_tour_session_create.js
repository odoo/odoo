/** @odoo-module **/

import { registry } from "@web/core/registry";
import surveySessionTools from "survey.session_tour_tools";

/**
 * Small tour that will simply start the session and wait for attendees.
 */
registry.category("web_tour.tours").add('test_survey_session_create_tour', {
    url: "/web",
    test: true,
    steps: [].concat(surveySessionTools.accessSurveySteps, [{
    trigger: 'button[name="action_start_session"]',
}, {
    trigger: '.o_survey_session_attendees_count:contains("0")',
    run: function () {} // check session is correctly started
}])});
