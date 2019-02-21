odoo.define('project.tour', function(require) {
"use strict";

var core = require('web.core');
var tour = require('web_tour.tour');

var _t = core._t;

tour.register('project_tour', {
    url: "/web",
}, [tour.STEPS.SHOW_APPS_MENU_ITEM, {
    trigger: '.o_app[data-menu-xmlid="project.menu_main_pm"]',
    content: _t('Want a better way to <b>manage your projects</b>? <i>It starts here.</i>'),
    position: 'right',
    edition: 'community',
}, {
    trigger: '.o_app[data-menu-xmlid="project.menu_main_pm"]',
    content: _t('Want a better way to <b>manage your projects</b>? <i>It starts here.</i>'),
    position: 'bottom',
    edition: 'enterprise',
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
    content: _t('This will create a new project and redirect us to its stages.'),
    position: 'top',
    run: function (actions) {
        actions.auto('.modal:visible .btn.btn-primary');
    },
}, {
    trigger: ".o_kanban_project_tasks .o_column_quick_create input",
    content: _t("Add columns to configure <b>stages for your tasks</b>.<br/><i>e.g. New - In Progress - Done</i>"),
    position: "bottom",
}, {
    trigger: ".o_kanban_project_tasks .o_column_quick_create .o_kanban_add",
    auto: true,
}, {
    trigger: ".o_kanban_project_tasks .o_column_quick_create input",
    content: _t("Add columns to configure <b>stages for your tasks</b>.<br/><i>e.g. New - In Progress - Done</i>"),
    position: "bottom",
}, {
    trigger: ".o_kanban_project_tasks .o_column_quick_create .o_kanban_add",
    auto: true,
}, {
    trigger: '.o-kanban-button-new',
    extra_trigger: '.o_kanban_project_tasks',
    content: _t('Let\'s create your first task.'),
    position: 'bottom',
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
    trigger: ".o_kanban_record .oe_kanban_content",
    extra_trigger: '.o_kanban_project_tasks',
    content: _t("Click on the card to write more information about it and collaborate with your coworkers."),
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
        actions.text("Marc Demo", this.$anchor.find("input"));
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
    trigger: ".breadcrumb-item:not(.active):last",
    extra_trigger: '.o_form_project_tasks.o_form_readonly',
    content: _t("Use the breadcrumbs to <b>go back to your tasks pipeline</b>."),
    position: "right"
}]);

});
