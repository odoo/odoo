odoo.define('survey.session_tour_tools', function (require) {
'use strict';

var tour = require('web_tour.tour');

/**
 * Tool that gathers common steps to every 'survey session' tours.
 */
return {
    accessSurveySteps: [tour.stepUtils.showAppsMenuItem(), {
        trigger: '.o_app[data-menu-xmlid="survey.menu_surveys"]',
        edition: 'community'
    }, {
        trigger: '.o_app[data-menu-xmlid="survey.menu_surveys"]',
        edition: 'enterprise'
    }, {
        trigger: '.oe_kanban_card:contains("User Session Survey")',
    }]
};

});
