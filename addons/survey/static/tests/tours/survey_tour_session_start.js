odoo.define('survey.test_survey_session_start_tour', function (require) {
"use strict";

var tour = require('web_tour.tour');
var surveySessionTools = require('survey.session_tour_tools');

/**
 * Small tour that will open the session manager and check
 * that the attendees are accounted for, then start the session
 * by going to the first question.
 */
tour.register('test_survey_session_start_tour', {
    url: "/web",
    test: true,
}, [].concat(surveySessionTools.accessSurveySteps, [{
    trigger: 'button[name="action_open_session_manager"]',
}, {
    trigger: '.o_survey_session_attendees_count:contains("3")',
    run: function () {} // check attendees count
}, {
    trigger: 'h1',
    run: function () {
        var e = $.Event('keydown');
        e.keyCode = 39; // arrow-right
        $(document).trigger(e); // start session
    }
}, {
    trigger: 'h1:contains("Nickname")',
    run: function () {} // check first question is displayed
}]));

});
