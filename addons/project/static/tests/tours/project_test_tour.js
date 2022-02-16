odoo.define('project.tour_test_project', function (require) {
'use strict';

var tour = require('web_tour.tour');

tour.register('project_test_tour', {
    url: '/web',
    test: true,
}, [tour.stepUtils.showAppsMenuItem(), {
    trigger: '.o_app[data-menu-xmlid="project.menu_main_pm"]',
    content: "Go to Project App",
}, {
    trigger: '.o-kanban-button-new',
    content: "Create a project",
    run: 'click',
}, {
    trigger: 'input.o_project_name',
    content: "Choose a name for the project",
}, {
    trigger: '.o_open_tasks',
    content: "Create the first project",
    run: function (actions) {
        actions.auto('.modal:visible .btn.btn-primary');
    },
}, {
    trigger: '.o_kanban_project_tasks .o_column_quick_create .input-group input',
    content: "Choose a name for Column to organize your tasks into stages (e.g. New - In Progress - Done)",
    run: 'text Test',
}, {
    trigger: '.o_kanban_project_tasks .o_column_quick_create .o_kanban_add',
    content: "Add Column",
    run: 'click',
}, {
    trigger: '.o_kanban_project_tasks .o_column_quick_create .input-group input',
    extra_trigger: '.o_kanban_group',
    content: "Choose a name for Column to to organize your tasks into stages (e.g. New - In Progress - Done)",
    run: 'text Test',
}, {
    trigger: ".o_kanban_project_tasks .o_column_quick_create .o_kanban_add",
    content: "Create Column",
    run: 'click',
}, {
    trigger: '.o-kanban-button-new',
    content: "Create the first task",
}, {
    trigger: '.o_kanban_quick_create input.o_field_char[name=name]',
    content: "Choose a task name (e.g. Website Design, Purchase Goods...)",
    run: 'text Test',
}, {
    trigger: '.o_kanban_quick_create .o_kanban_add',
    content: "Add the task once it is ready.",
    run: 'click',
}, {
    trigger: '.o_kanban_record .oe_kanban_content',
    content: "Drag and drop the card to change the task from stage.",
    extra_trigger: '.o_kanban_project_tasks',
    run: "drag_and_drop .o_kanban_group:eq(1) ",
}]);

});
