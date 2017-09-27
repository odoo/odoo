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
    position: 'right',
    width: 200,
}, {
    trigger: 'input.o_project_name',
    content: _t('Choose a <b>project name</b>. (e.g. Website Launch, Product Development, Office Party, etc.)'),
    position: 'right',
    run: function (actions) {
        actions.auto();
        actions.auto(".modal:visible .btn.btn-primary");
    },
}, {
    trigger: '.o_project_kanban .o_kanban_record:first-child',
    content: _t('Click on the card to <b>go to your project</b> and start organizing tasks.'),
    position: 'right',
    run: function (actions) {
        actions.auto(this.$anchor.find(".o_project_kanban_box:first"));
    },
}, {
    trigger: ".o_kanban_project_tasks .o_column_quick_create",
    content: _t("Add columns to configure <b>stages for your tasks</b>.<br/><i>e.g. Specification &gt; Development &gt; Done</i>"),
    position: "right"
}, {
    trigger: ".o-kanban-button-new",
    extra_trigger: '.o_kanban_project_tasks .o_kanban_group:eq(2)',
    content: _t("Now that the project is set up, <b>create a few tasks</b>."),
    position: "right"
}, {
    trigger: ".o_kanban_group:first-child .o_kanban_record:last-child",
    extra_trigger: '.o_kanban_project_tasks',
    content: _t("<b>Drag &amp; drop tasks</b> between columns as you work on them."),
    position: "right",
    run: "drag_and_drop .o_kanban_group:eq(2) ",
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
}, tour.STEPS.TOGGLE_APPSWITCHER,
tour.STEPS.MENU_MORE, {
    trigger: '.o_app[data-menu-xmlid="base.menu_administration"], .oe_menu_toggler[data-menu-xmlid="base.menu_administration"]',
    content: _t("Configuration options are available in the Settings app."),
    position: "bottom"
}, {
    trigger: ".o_web_settings_dashboard textarea#user_emails",
    content: _t("<b>Invite coworkers</b> via email.<br/><i>Enter one email per line.</i>"),
    position: "right"
}, tour.STEPS.TOGGLE_APPSWITCHER,
tour.STEPS.MENU_MORE, {
    trigger: '.o_app[data-menu-xmlid="project.menu_main_pm"], .oe_menu_toggler[data-menu-xmlid="project.menu_main_pm"]',
    content: _t("Good job! Your completed the Project Management tour. You can continue with the <b>implementation guide</b> to help you setup Project Management in your company."),
    position: 'bottom',
}, {
    trigger: '.o_planner_systray div.progress',
    content: _t("Use the <b>implementation guide</b> to setup Project Management in your company."),
    position: 'bottom',
}]);

});
