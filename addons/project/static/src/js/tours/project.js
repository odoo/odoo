odoo.define('project.tour', function(require) {
"use strict";

var core = require('web.core');
var tour = require('web_tour.tour');

var _t = core._t;

tour.register('project_tour', {
    sequence: 110,
    url: "/web",
    rainbowManMessage: "Congratulations, you are now a master of project management.",
}, [tour.stepUtils.showAppsMenuItem(), {
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
    content: _t('Let\'s create your first <b>project</b>.'),
    position: 'bottom',
    width: 200,
}, {
    trigger: 'input.o_project_name',
    content: _t('Choose a <b>name</b> for your project. <i>It can be anything you want: the name of a customer,\
     of a product, of a team, of a construction site...</i>'),
    position: 'right',
}, {
    trigger: '.o_open_tasks',
    content: _t('Let\'s create your first <b>project</b>.'),
    position: 'top',
    run: function (actions) {
        actions.auto('.modal:visible .btn.btn-primary');
    },
}, {
    trigger: ".o_kanban_project_tasks .o_column_quick_create input",
    content: _t("Add columns to organize your tasks into <b>stages</b> <i>e.g. New - In Progress - Done</i>."),
    position: 'bottom',
}, {
    trigger: ".o_kanban_project_tasks .o_column_quick_create .o_kanban_add",
    auto: true,
}, {
    trigger: ".o_kanban_project_tasks .o_column_quick_create input",
    extra_trigger: '.o_kanban_group',
    content: _t("Add columns to organize your tasks into <b>stages</b> <i>e.g. New - In Progress - Done</i>."),
    position: 'bottom',
}, {
    trigger: ".o_kanban_project_tasks .o_column_quick_create .o_kanban_add",
    auto: true,
}, {
    trigger: '.o-kanban-button-new',
    extra_trigger: '.o_kanban_group:eq(1)',
    content: _t("Let's create your first <b>task</b>."),
    position: 'bottom',
    width: 200,
}, {
    trigger: '.o_kanban_quick_create input.o_field_char[name=name]',
    extra_trigger: '.o_kanban_project_tasks',
    content: _t('Choose a task <b>name</b> <i>(e.g. Website Design, Purchase Goods...)</i>'),
    position: 'right',
}, {
    trigger: '.o_kanban_quick_create .o_kanban_add',
    extra_trigger: '.o_kanban_project_tasks',
    content: _t("Add your task once it is ready."),
    position: "bottom",
}, {
    trigger: ".o_kanban_record .oe_kanban_content",
    extra_trigger: '.o_kanban_project_tasks',
    content: _t("<b>Drag &amp; drop</b> the card to change your task from stage."),
    position: "bottom",
    run: "drag_and_drop .o_kanban_group:eq(1) ",
}, {
    trigger: ".o_kanban_record:first",
    extra_trigger: '.o_kanban_project_tasks',
    content: _t("Let's start working on your task."),
    position: "bottom",
}, {
    trigger: ".o_ChatterTopbar_buttonSendMessage",
    content: _t("Use this chatter to <b>send emails</b> and communicate efficently with your customers. \
    Add new people in the followers list to make them aware about the main changes about this task."),
    width: 350,
    position: "bottom",
}, {
    trigger: ".o_ChatterTopbar_buttonLogNote",
    content: _t("<b>Log notes</b> for internal communications <i>(the people following this task won't be notified \
    of the note you are logging unless you specifically tag them)</i>. Use @ <b>mentions</b> to ping a colleague \
    or # <b>mentions</b> to reach an entire team."),
    width: 350,
    position: "bottom"
}, {
    trigger: ".o_ChatterTopbar_buttonScheduleActivity",
    content: _t("Use <b>activities</b> to organize your daily work."),
}, {
    trigger: ".modal-dialog .btn-primary",
    content: "Schedule your activity once it is ready",
    position: "bottom",
    run: "click",
}, {
    trigger: ".breadcrumb-item:not(.active):last",
    extra_trigger: '.o_form_project_tasks.o_form_readonly',
    content: _t("Let's go back to your <b>kanban view</b> to have an overview of your next tasks."),
    position: "right",
    run: 'click',
}]);

});
