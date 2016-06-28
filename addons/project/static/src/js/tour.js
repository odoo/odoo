odoo.define('project.tour', function(require) {
"use strict";

var core = require('web.core');
var tour = require('web_tour.tour');

var _t = core._t;

tour.register('project_tour', {
    'skip_enabled': true,
}, [{
    trigger: '.o_app[data-menu-xmlid="base.menu_main_pm"], .oe_menu_toggler[data-menu-xmlid="base.menu_main_pm"]',
    content: _t('Want a better way to <b>manage your projects</b>? <i>It starts here.</i>'),
    position: 'bottom',
}, {
    trigger: '.o-kanban-button-new',
    extra_trigger: '.o_project_kanban',
    content: _t('Let\'s create your first project.'),
    position: 'right',
    width: 200,
}, {
    trigger: 'input.o_project_name',
    content: _t('Choose a <b>project name</b>. (e.g. Website Launch, Product Development, Office Party, etc.)'),
    position: 'right',
}, {
    trigger: '.o_project_kanban .o_kanban_record:first-child',
    content: _t('Click on the card to <b>go to your project</b> and start organizing tasks.'),
    position: 'right',
}, {
    trigger: ".o_kanban_project_tasks .o_column_quick_create",
    content: _t("Add columns to configure <b>stages for your tasks</b>.<br/><i>e.g. Specification &gt; Development &gt; Done</i>"),
    position: "right"
}, {
    trigger: ".o-kanban-button-new",
    extra_trigger: '.o_kanban_project_tasks .o_kanban_group:nth-child(2)',
    content: _t("Now that the project is setup, <b>create a few tasks</b>."),
    position: "right"
}, {
    trigger: ".o_kanban_record:nth-child(3)",
    extra_trigger: '.o_kanban_project_tasks',
    content: _t("<b>Drag &amp; drop tasks</b> between columns as you work on them."),
    position: "right"
}, {
    trigger: ".o_kanban_record .o_priority_star",
    extra_trigger: '.o_kanban_project_tasks',
    content: _t("<b>Star tasks</b> to mark team priorities."),
    position: "bottom"
}, {
    trigger: ".breadcrumb li:not(.active):last",
    extra_trigger: '.o_form_project_tasks',
    content: _t("Click on layers in the path to easily <b>return to tasks</b>."),
    position: "bottom"
}, {
    trigger: ".o_main_navbar .o_menu_toggle",
    content: _t('Click the <i>Home icon</i> to navigate across apps.'),
    position: "bottom"
}, {
    trigger: ".o_apps .o_app:last",
    content: _t("Configuration options are available in the Settings app."),
    position: "bottom"
}, {
    trigger: ".o_web_settings_dashboard .o_web_settings_dashboard_invitations",
    content: _t("<b>Invite collegues</b> via email.<br/><i>Enter one email per line.</i>"),
    position: "bottom"
}]);

});
