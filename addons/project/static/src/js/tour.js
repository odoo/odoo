odoo.define('project.tour', function(require) {
"use strict";

var core = require('web.core');
var tour = require('web_tour.tour');

var _t = core._t;

tour.register('project_tour', {
    url: "/web",
}, [tour.STEPS.MENU_MORE, {
    trigger: '.o_app[data-menu-xmlid="project.menu_main_pm"], .oe_menu_toggler[data-menu-xmlid="project.menu_main_pm"]',
    content: _t('Want a better way to <b>manage your projects</b>? <i>It starts here.</i>'),
    position: 'bottom',
}, {
    trigger: '.o-kanban-button-new',
    extra_trigger: '.o_project_kanban',
    content: _t('Let\'s create your first project.'),
    position: 'bottom',
    width: 200,
}, {
    trigger: 'input.o_project_name',
    content: _t('Choose a <b>project name</b>. (e.g. Website Launch, Product Development, Office Party, etc.)'),
    position: 'right',
}, {
    trigger: '.o_open_tasks',
    content: _t('This will create new project and redirect us to its tasks.'),
    position: 'right',
    run: function (actions) {
        actions.auto('[role="dialog"]:visible .btn.btn-primary');
    },
}, {
    trigger: ".o_kanban_project_tasks .o_column_quick_create input",
    content: _t("Add columns to configure <b>stages for your tasks</b>.<br/><i>e.g. Specification &gt; Development &gt; Done</i>"),
    position: "right"
}, {
    trigger: ".o_kanban_project_tasks .o_column_quick_create .o_kanban_add",
    auto: true,
}, {
    trigger: '.o-kanban-button-new',
    extra_trigger: '.o_kanban_project_tasks',
    content: _t('Let\'s create your first task.'),
    position: 'right',
    width: 200,
}, {
    trigger: '.o_kanban_quick_create input.o_field_char[name=name]',
    extra_trigger: '.o_kanban_project_tasks',
    content: _t('Choose a <b>task name</b>. (e.g. Website Design, Purchase Goods etc.)'),
    position: 'right',
}, {
    trigger: '.o_kanban_quick_create .o_kanban_add',
    extra_trigger: '.o_kanban_project_tasks',
    content: _t("<p>Once your task is ready, you can save it.</p>"),
    position: 'bottom',
}, {
    trigger: ".o_kanban_record .o_priority_star",
    extra_trigger: '.o_kanban_project_tasks',
    content: _t("<b>Star tasks</b> to mark team priorities."),
    position: "bottom",
}, {
    trigger: ".o_kanban_record",
    extra_trigger: '.o_kanban_project_tasks',
    content: _t("Click on a card to get the details of the task."),
    position: "bottom",
}, {
    trigger: ".o_form_button_edit",
    extra_trigger: '.o_form_project_tasks',
    content: _t('Click on this button to modify the task.'),
    position: "bottom"
}, {
    trigger: ".o_form_view .o_task_user_field",
    extra_trigger: '.o_form_project_tasks.o_form_editable',
    content: _t('<b>Assign the task</b> to someone. <i>You can create and invite a new user on the fly.</i>'),
    position: "bottom",
    run: function (actions) {
        actions.text("Demo User", this.$anchor.find("input"));
    },
}, {
    trigger: ".ui-autocomplete > li > a",
    auto: true,
}, {
    trigger: ".o_form_button_save",
    extra_trigger: '.o_form_project_tasks.o_form_editable',
    content: _t('<b>Click the save button</b> to apply your changes to the task.'),
    position: "bottom"
}, {
    trigger: ".breadcrumb li:not(.active):last",
    extra_trigger: '.o_form_project_tasks.o_form_readonly',
    content: _t("Use the breadcrumbs to <b>go back to your tasks pipeline</b>."),
    position: "bottom"
}, tour.STEPS.TOGGLE_HOME_MENU,
tour.STEPS.MENU_MORE, {
    trigger: '.o_app[data-menu-xmlid="base.menu_administration"], .oe_menu_toggler[data-menu-xmlid="base.menu_administration"]',
    content: _t("Configuration options are available in the Settings app."),
    position: "bottom"
}, {
    trigger: ".o_web_settings_dashboard .o_user_emails",
    content: _t("<b>Invite coworkers</b> via email.<br/><i>Enter one email per line.</i>"),
    position: "right"
}, tour.STEPS.TOGGLE_HOME_MENU,
tour.STEPS.MENU_MORE, {
    trigger: '.o_app[data-menu-xmlid="project.menu_main_pm"], .oe_menu_toggler[data-menu-xmlid="project.menu_main_pm"]',
    content: _t("Good job! You completed the Project Management tour."),
    position: 'bottom',
}]);

});
