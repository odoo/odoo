odoo.define('survey.test_survey_session_create_tour', function (require) {
"use strict";

var tour = require('web_tour.tour');
var surveySessionTools = require('survey.session_tour_tools');

/**
 * Small tour that will simply start the session and wait for attendees.
 */
tour.register('test_survey_session_create_tour', {
    url: "/web",
    test: true,
}, [].concat(surveySessionTools.accessSurveySteps, [{
    trigger: 'button[name="action_start_session"]',
}, {
    trigger: '.o_survey_session_attendees_count:contains("0")',
    run: function () {} // check session is correctly started
}]));

});
