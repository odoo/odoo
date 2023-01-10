/** @odoo-module **/

import tour from 'web_tour.tour';

tour.register('project_sharing_tour', {
    test: true,
    url: '/web',
}, [...tour.stepUtils.goToAppSteps("project.menu_main_pm", 'Go to the Project App.'), {
    // an invisible element cannot be used as a trigger so this small hack is mandatory for the next step
    trigger: '.o_kanban_record:contains("Project Sharing")',
    run: function () {
        this.$anchor.find('.o_dropdown_kanban').css('visibility', 'visible');
    },
}, {
    trigger: '.oe_kanban_global_click :contains("Project Sharing") .o_dropdown_kanban',
    content: 'Open the project dropdown.'
}, {
    trigger: '.o_kanban_record:contains("Project Sharing") .dropdown-menu a:contains("Share")',
    content: 'Start editing the project.',
}, {
    trigger: 'div.o_field_radio[name="access_mode"] > div.o_radio_item > input[data-value="edit"]',
    content: 'Select "Edit" as Access mode in the "Share Project" wizard.',
}, {
    trigger: '.o_field_many2one[name="partner_ids"]',
    content: 'Select the user portal as collaborator to the "Project Sharing" project.',
    run: function (actions) {
        actions.text('Georges', this.$anchor.find('input'));
    },
}, {
    trigger: '.ui-autocomplete a:contains("Georges")',
    in_modal: false,
}, {
    trigger: 'footer > button[name="action_send_mail"]',
    content: 'Confirm the project sharing with this portal user.',
}, {
    trigger: '.o_web_client',
    content: 'Go to project portal view to select the "Project Sharing" project',
    run: function () {
        window.location.href = window.location.origin + '/my/projects';
    },
}, {
    trigger: 'table > tbody > tr a:has(span:contains(Project Sharing))',
    content: 'Select "Project Sharing" project to go to project sharing feature for this project.',
}, {
    trigger: '.o_project_sharing',
    content: 'Wait the project sharing feature be loaded',
    run: function () {},
}, {
    trigger: 'button.o-kanban-button-new',
    content: 'Click "Create" button',
    run: 'click',
}, {
    trigger: '.o_kanban_quick_create .o_field_widget[name="name"]',
    content: 'Create Task',
    run: 'text Test Create Task',
}, {
    trigger: '.o_kanban_quick_create .o_kanban_edit',
    content: 'Go to the form view of this new task',
}, {
    trigger: 'div.o_statusbar_status[name="stage_id"] button[aria-checked="false"]:contains(Done)',
    content: 'Change the stage of the task.',
}, {
    trigger: '.o_portal_chatter_composer_input .o_portal_chatter_composer_body textarea[name="message"]',
    content: 'Write a message in the chatter of the task',
    run: 'text I create a new task for testing purpose.',
}, {
    trigger: '.o_portal_chatter_composer_input .o_portal_chatter_composer_body button[data-action="/mail/chatter_post"]',
    content: 'Send the message',
}, {
    trigger: 'ol.breadcrumb > li.o_back_button > a:contains(Project Sharing)',
    content: 'Go back to the kanban view',
}, {
    trigger: '.o_filter_menu > button',
    content: 'click on filter menu in the search view',
}, {
    trigger: '.o_filter_menu > .dropdown-menu > .dropdown-item:first-child',
    content: 'click on the first item in the filter menu',
}, {
    trigger: '.o_group_by_menu > button',
    content: 'click on group by menu in the search view',
}, {
    trigger: '.o_group_by_menu > .dropdown-menu > .dropdown-item:first-child',
    content: 'click on the first item in the group by menu',
}, {
    trigger: '.o_favorite_menu > button',
    content: 'click on the favorite menu in the search view',
}, {
    trigger: '.o_favorite_menu .o_add_favorite > button',
    content: 'click to "save current search" button in favorite menu',
}, {
    trigger: 'button.o_switch_view.o_list',
    content: 'Go to the list view',
    run: 'click',
}]);

tour.register('portal_project_sharing_tour', {
    test: true,
    url: '/my/projects',
}, [{
    trigger: 'table > tbody > tr a:has(span:contains(Project Sharing))',
    content: 'Select "Project Sharing" project to go to project sharing feature for this project.',
}, {
    trigger: '.o_project_sharing',
    content: 'Wait the project sharing feature be loaded',
    run: function () {},
}, {
    trigger: 'button.o-kanban-button-new',
    content: 'Click "Create" button',
    run: 'click',
}, {
    trigger: '.o_kanban_quick_create .o_field_widget[name="name"]',
    content: 'Create Task',
    run: 'text Test Create Task',
}, {
    trigger: '.o_kanban_quick_create .o_kanban_edit',
    content: 'Go to the form view of this new task',
}, {
    trigger: 'div.o_statusbar_status[name="stage_id"] button[aria-checked="false"]:contains(Done)',
    content: 'Change the stage of the task.',
}, {
    trigger: '.o_portal_chatter_composer_input .o_portal_chatter_composer_body textarea[name="message"]',
    content: 'Write a message in the chatter of the task',
    run: 'text I create a new task for testing purpose.',
}, {
    trigger: '.o_portal_chatter_composer_input .o_portal_chatter_composer_body button[data-action="/mail/chatter_post"]',
    content: 'Send the message',
}, {
    trigger: 'ol.breadcrumb > li.o_back_button > a:contains(Project Sharing)',
    content: 'Go back to the kanban view',
}, {
    trigger: '.o_filter_menu > button',
    content: 'click on filter menu in the search view',
}, {
    trigger: '.o_filter_menu > .dropdown-menu > .dropdown-item:first-child',
    content: 'click on the first item in the filter menu',
}, {
    trigger: '.o_group_by_menu > button',
    content: 'click on group by menu in the search view',
}, {
    trigger: '.o_group_by_menu > .dropdown-menu > .dropdown-item:first-child',
    content: 'click on the first item in the group by menu',
}, {
    trigger: '.o_favorite_menu > button',
    content: 'click on the favorite menu in the search view',
}, {
    trigger: '.o_favorite_menu .o_add_favorite > button',
    content: 'click to "save current search" button in favorite menu',
}, {
    trigger: 'button.o_switch_view.o_list',
    content: 'Go to the list view',
    run: 'click',
}]);
