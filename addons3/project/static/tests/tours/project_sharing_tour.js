/** @odoo-module **/

import { registry } from "@web/core/registry";
import { stepUtils } from "@web_tour/tour_service/tour_utils";

const projectSharingSteps = [...stepUtils.goToAppSteps("project.menu_main_pm", 'Go to the Project App.'), {
    trigger: '.o_kanban_record:contains("Project Sharing") .o_dropdown_kanban .dropdown-toggle',
    content: 'Open the project dropdown.'
}, {
    trigger: '.o_kanban_record:contains("Project Sharing") .dropdown-menu a:contains("Share")',
    content: 'Start editing the project.',
}, {
    trigger: 'div.o_field_radio[name="access_mode"] div.o_radio_item > input[data-value="edit"]',
    content: 'Select "Edit" as Access mode in the "Share Project" wizard.',
}, {
    trigger: '.o_field_many2many_tags_email[name=partner_ids] input',
    extra_trigger: 'label[for=partner_ids_0]:contains("Invite People")',
    content: 'Select the user portal as collaborator to the "Project Sharing" project.',
    run: 'text Georges',
}, {
    trigger: '.ui-autocomplete a.dropdown-item:contains("Georges")',
    in_modal: false,
}, {
    trigger: 'footer > button[name="action_share_record"]',
    content: 'Confirm the project sharing with this portal user.',
}, {
    trigger: '.o_web_client',
    content: 'Go to project portal view to select the "Project Sharing" project',
    run: function () {
        window.location.href = window.location.origin + '/my/projects';
    },
}, {
    id: 'project_sharing_feature',
    trigger: 'table > tbody > tr a:has(span:contains(Project Sharing))',
    content: 'Select "Project Sharing" project to go to project sharing feature for this project.',
}, {
    trigger: 'iframe .o_project_sharing',
    content: 'Wait the project sharing feature be loaded',
    run: function () {},
}, {
    trigger: 'iframe button.o-kanban-button-new',
    content: 'Click "Create" button',
    run: 'click',
}, {
    trigger: 'iframe .o_kanban_quick_create .o_field_widget[name="name"] input',
    content: 'Create Task',
    run: 'text Test Create Task',
}, {
    trigger: 'iframe .o_kanban_quick_create .o_kanban_edit',
    content: 'Go to the form view of this new task',
}, {
    trigger: 'iframe div[name="stage_id"] div.o_statusbar_status button[aria-checked="false"]:contains(Done)',
    content: 'Change the stage of the task.',
}, {
    trigger: 'iframe .o_portal_chatter_composer_input .o_portal_chatter_composer_body textarea',
    content: 'Write a message in the chatter of the task',
    run: 'text I create a new task for testing purpose.',
}, {
    trigger: 'iframe .o_portal_chatter_composer_input .o_portal_chatter_composer_body button[name="send_message"]',
    content: 'Send the message',
}, {
    trigger: 'iframe ol.breadcrumb > li.o_back_button > a:contains(Project Sharing)',
    content: 'Go back to the kanban view',
}, {
    trigger: 'iframe .o_searchview_dropdown_toggler',
    content: 'open the search panel menu',
}, {
    trigger: 'iframe .o_filter_menu .dropdown-item:first-child',
    content: 'click on the first item in the filter menu',
}, {
    trigger: 'iframe .o_group_by_menu .dropdown-item:first-child',
    content: 'click on the first item in the group by menu',
}, {
    trigger: 'iframe .o_favorite_menu .o_add_favorite',
    content: 'open accordion "save current search" in favorite menu',
}, {
    trigger: 'iframe .o_favorite_menu .o_accordion_values .o_save_favorite',
    content: 'click to "save" button in favorite menu',
}, {
    trigger: 'iframe .o_filter_menu .dropdown-item:first-child',
    content: 'click on the first item in the filter menu',
}, {
    trigger: 'iframe .o_group_by_menu .dropdown-item:first-child',
    content: 'click on the first item in the group by menu',
}, {
    trigger: 'iframe .o_favorite_menu .o_accordion_values .o_save_favorite',
    content: 'click to "save" button in favorite menu',
}, {
    trigger: 'iframe button.o_switch_view.o_list',
    content: 'Go to the list view',
}, {
    trigger: 'iframe .o_list_view',
    content: 'Check the list view',
    isCheck: true,
}];

registry.category("web_tour.tours").add('project_sharing_tour', {
    test: true,
    url: '/web',
    steps: () => {
        return projectSharingSteps;
    } 
});

registry.category("web_tour.tours").add("portal_project_sharing_tour", {
    test: true,
    url: "/my/projects",
    steps: () => {
        // The begining of the project sharing feature
        const projectSharingStepIndex = projectSharingSteps.findIndex(s => s?.id === 'project_sharing_feature');
        return projectSharingSteps.slice(projectSharingStepIndex, projectSharingSteps.length);
    }
});
