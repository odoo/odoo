odoo.define('project.tour', function(require) {
"use strict";

const {_t} = require('web.core');
const {Markup} = require('web.utils');
var tour = require('web_tour.tour');

tour.register('project_tour', {
    sequence: 110,
    url: "/web",
    rainbowManMessage: _t("Congratulations, you are now a master of project management."),
}, [tour.stepUtils.showAppsMenuItem(), {
    trigger: '.o_app[data-menu-xmlid="project.menu_main_pm"]',
    content: Markup(_t('Want a better way to <b>manage your projects</b>? <i>It starts here.</i>')),
    position: 'right',
    edition: 'community',
}, {
    trigger: '.o_app[data-menu-xmlid="project.menu_main_pm"]',
    content: Markup(_t('Want a better way to <b>manage your projects</b>? <i>It starts here.</i>')),
    position: 'bottom',
    edition: 'enterprise',
}, {
    trigger: '.o-kanban-button-new',
    extra_trigger: '.o_project_kanban',
    content: Markup(_t('Let\'s create your first <b>project</b>.')),
    position: 'bottom',
    width: 200,
}, {
    trigger: '.o_project_name input',
    content: Markup(_t('Choose a <b>name</b> for your project. <i>It can be anything you want: the name of a customer,\
     of a product, of a team, of a construction site, etc.</i>')),
    position: 'right',
}, {
    trigger: '.o_open_tasks',
    content: Markup(_t('Let\'s create your first <b>project</b>.')),
    position: 'top',
    run: function (actions) {
        actions.auto('.modal:visible .btn.btn-primary');
    },
}, {
    trigger: ".o_kanban_project_tasks .o_column_quick_create .input-group",
    content: Markup(_t("Add columns to organize your tasks into <b>stages</b> <i>e.g. New - In Progress - Done</i>.")),
    position: 'right',
    run: function (actions) {
        actions.text("Test", this.$anchor.find("input"));
    },
}, {
    trigger: ".o_kanban_project_tasks .o_column_quick_create .o_kanban_add",
    auto: true,
}, {
    trigger: ".o_kanban_project_tasks .o_column_quick_create .input-group",
    extra_trigger: '.o_kanban_group',
    content: Markup(_t("Add columns to organize your tasks into <b>stages</b> <i>e.g. New - In Progress - Done</i>.")),
    position: 'right',
    run: function (actions) {
        actions.text("Test", this.$anchor.find("input"));
    },
}, {
    trigger: ".o_kanban_project_tasks .o_column_quick_create .o_kanban_add",
    auto: true,
}, {
    trigger: '.o-kanban-button-new',
    extra_trigger: '.o_kanban_group:eq(1)',
    content: Markup(_t("Let's create your first <b>task</b>.")),
    position: 'bottom',
    width: 200,
}, {
    trigger: '.o_kanban_quick_create div.o_field_char[name=name] input',
    extra_trigger: '.o_kanban_project_tasks',
    content: Markup(_t('Choose a task <b>name</b> <i>(e.g. Website Design, Purchase Goods...)</i>')),
    position: 'right',
}, {
    trigger: '.o_kanban_quick_create .o_kanban_add',
    extra_trigger: '.o_kanban_project_tasks',
    content: _t("Add your task once it is ready."),
    position: "bottom",
}, {
    trigger: ".o_kanban_record .oe_kanban_content",
    extra_trigger: '.o_kanban_project_tasks',
    content: Markup(_t("<b>Drag &amp; drop</b> the card to change your task from stage.")),
    position: "bottom",
    run: "drag_and_drop_native .o_kanban_group:eq(1) ",
}, {
    trigger: ".o_kanban_record:first",
    extra_trigger: '.o_kanban_project_tasks',
    content: _t("Let's start working on your task."),
    position: "bottom",
}, {
    trigger: ".o_ChatterTopbar_buttonSendMessage",
    extra_trigger: '.o_form_project_tasks',
    content: Markup(_t("Use the chatter to <b>send emails</b> and communicate efficiently with your customers. \
    Add new people to the followers' list to make them aware of the main changes about this task.")),
    width: 350,
    position: "bottom",
}, {
    trigger: ".o_ChatterTopbar_buttonLogNote",
    extra_trigger: '.o_form_project_tasks',
    content: Markup(_t("<b>Log notes</b> for internal communications <i>(the people following this task won't be notified \
    of the note you are logging unless you specifically tag them)</i>. Use @ <b>mentions</b> to ping a colleague \
    or # <b>mentions</b> to reach an entire team.")),
    width: 350,
    position: "bottom"
}, {
    trigger: ".o_ChatterTopbar_buttonScheduleActivity",
    extra_trigger: '.o_form_project_tasks',
    content: Markup(_t("Create <b>activities</b> to set yourself to-dos or to schedule meetings.")),
}, {
    trigger: ".modal-dialog .btn-primary",
    extra_trigger: '.o_form_project_tasks',
    content: _t("Schedule your activity once it is ready."),
    position: "bottom",
    run: "click",
}, {
    trigger: ".o_field_widget[name='user_ids'] input",
    extra_trigger: '.o_form_project_tasks',
    content: _t("Assign a responsible to your task"),
    position: "right",
    run: "text a"
}, {
    trigger: ".ui-autocomplete > li > a:not(:has(i.fa))",
    auto: true,
}, {
    trigger: ".o_form_button_save",
    extra_trigger: '.o_form_project_tasks.o_form_dirty',
    content: Markup(_t("You have unsaved changes - no worries! Odoo will automatically save it as you navigate.<br/> You can discard these changes from here or manually save your task.<br/>Let's save it manually.")),
    position: "bottom",
}, {
    trigger: ".breadcrumb-item:not(.active):last",
    extra_trigger: '.o_form_project_tasks',
    content: Markup(_t("Let's go back to the <b>kanban view</b> to have an overview of your next tasks.")),
    position: "right",
    run: 'click',
}, {
    trigger: '.o_kanban_renderer',
    // last step to confirm we've come back before considering the tour successful
    auto: true
}]);

});
