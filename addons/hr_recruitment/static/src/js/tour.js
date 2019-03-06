odoo.define('hr_recruitment.tour', function(require) {
"use strict";

var core = require('web.core');
var tour = require('web_tour.tour');

var _t = core._t;

tour.register('hr_recruitment_tour', [tour.STEPS.SHOW_APPS_MENU_ITEM, {
    trigger: '.o_app[data-menu-xmlid="hr_recruitment.menu_hr_recruitment_root"]',
    content: _t('Want to <b>start recruiting</b> like a pro? <i>Start here.</i>'),
    position: 'right',
    edition: 'community'
}, {
    trigger: '.o_app[data-menu-xmlid="hr_recruitment.menu_hr_recruitment_root"]',
    content: _t('Want to <b>start recruiting</b> like a pro? <i>Start here.</i>'),
    position: 'bottom',
    edition: 'enterprise'
}, {
    trigger: ".o-kanban-button-new",
    extra_trigger: '.o_hr_recruitment_kanban',
    content: _t("Click here to create a new job position."),
    position: "bottom"
}, {
    trigger: ".oe_kanban_action_button",
    extra_trigger: '.o_hr_recruitment_kanban',
    content: _t("Let\'s have a look at the <b>applications pipeline</b> for this job position."),
    position: "bottom"
}, {
    trigger: ".breadcrumb-item:not(.active):last",
    extra_trigger: '.o_kanban_applicant',
    content: _t("Use the breadcrumbs to <b>go back to the dashboard</b>."),
    position: "bottom"
}, {
    trigger: ".o_job_alias",
    extra_trigger: '.o_hr_recruitment_kanban',
    content: _t("Try to send an email to this address, it will create an application automatically."),
    position: "bottom"
}]);

});
