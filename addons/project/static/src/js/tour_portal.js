odoo.define('project.portal_tours', function (require) {
    'use strict';
    
    var tour = require('web_tour.tour');
    
    // ADMIN
    tour.register('portal_project_tour_admin', {
        test: true,
        url: '/my/project/2',
    },
        [
            {
                content: "Check that the breadcrumb shows the name of the project",
                trigger: '.breadcrumb-item:contains("Office Design")',
            }, {
                content: "Once the iframe is loaded, prioritize a task",
                extra_trigger: 'iframe .o_view_controller',
                trigger: 'iframe .o_kanban_record:contains("Meeting Room Furnitures") .o_priority_star',
            }, {
                content: "Change a task's status",
                trigger: 'iframe .o_kanban_record:contains("Meeting Room Furnitures") .o_status',
                run: function (actions) {
                    actions.auto('iframe .o_kanban_record:contains("Meeting Room Furnitures") .dropdown-menu.state:contains("Ready for Next Stage")');
                },
            }, {
                content: "Open a task's form view",
                trigger: 'iframe .o_kanban_record:contains("Meeting Room Furnitures"):first',
            }, {
                content: "Check that the selected task was opened",
                extra_trigger: 'iframe .o_form_view',
                trigger: 'iframe .o_task_name:contains("Meeting Room Furnitures")',
            }, {
                content: "Prioritize that task",
                trigger: 'iframe .o_priority_star',
            }, {
                content: "Change that task's stage",
                trigger: 'iframe button:contains("To Do")',
            }, {
                content: "Open the chatter composer",
                trigger: 'iframe button:contains("Send message")',
            }, {
                content: "Once the composer is open, send a message on the chatter",
                trigger: 'iframe .o_composer_input textarea:first',
                extra_trigger: 'iframe .o_thread_composer',
                run: function (actions) {
                    actions.text("Test message");
                    actions.auto('iframe .o_composer_send button:contains("Send")');
                },
            }, {
                content: "Check that the chatter contains the message",
                trigger: 'iframe .o_thread_message_content:contains("Test message")',
            }, {
                content: "Click on the project's name from within the form",
                trigger: 'iframe .o_group a[href*="/my/project"]:contains("Office Design"):first',
            }, {
                content: "Once the Kanban view is open again, check that the breadcrumb shows the name of the project",
                extra_trigger: 'iframe .o_kanban_view',
                trigger: '.breadcrumb-item:contains("Office Design")',
            },
        ],
    );

    // UNLOGGED, ACCESS TOKEN
    tour.register('portal_project_tour_unlogged_accesstoken', {
        test: true,
        url: '/web',
    },
        [
            {
                content: "Open the Project module",
                trigger: '.o_app[data-menu-xmlid="project.menu_main_pm"], .oe_menu_toggler[data-menu-xmlid="project.menu_main_pm"]',
            }, {
                content: "Open the edit form for the first project ('Office Design')",
                trigger: '.o_kanban_record:first .o_kanban_manage_toggle_button',
                run: function (actions) {
                    actions.auto('.oe_kanban_action.oe_kanban_action_a:contains("Edit"):first');
                },
            }, {
                content: "Copy the Public Link",
                trigger: '.o_btn_char_copy',
            },
            {
                content: "Check that the breadcrumb shows the name of the project",
                trigger: '.breadcrumb-item:contains("Office Design")',
            }, {
                content: "Once the iframe is loaded, open a task's form view",
                extra_trigger: 'iframe .o_view_controller',
                trigger: 'iframe .o_kanban_record:contains("Meeting Room Furnitures"):first',
            }, {
                content: "Check that the selected task was opened",
                extra_trigger: 'iframe .o_form_view',
                trigger: 'iframe .o_task_name:contains("Meeting Room Furnitures")',
            }, {
                content: "Open the chatter composer",
                trigger: 'iframe button:contains("Send message")',
            }, {
                content: "Once the composer is open, send a message on the chatter",
                trigger: 'iframe .o_composer_input textarea:first',
                extra_trigger: 'iframe .o_thread_composer',
                run: function (actions) {
                    actions.text("Test message");
                    actions.auto('iframe .o_composer_send button:contains("Send")');
                },
            }, {
                content: "Check that the chatter contains the message",
                trigger: 'iframe .o_thread_message_content:contains("Test message")',
            }, {
                content: "Click on the project's name from within the form",
                trigger: 'iframe .o_group a[href*="/my/project"]:contains("Office Design"):first',
            }, {
                content: "Once the Kanban view is open again, check that the breadcrumb shows the name of the project",
                extra_trigger: 'iframe .o_kanban_view',
                trigger: '.breadcrumb-item:contains("Office Design")',
            },
        ],
    );
    
});
