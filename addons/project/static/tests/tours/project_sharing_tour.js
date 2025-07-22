import { delay } from "@odoo/hoot-dom";
import { registry } from "@web/core/registry";
import { stepUtils } from "@web_tour/tour_utils";

const projectSharingSteps = [...stepUtils.goToAppSteps("project.menu_main_pm", 'Go to the Project App.'), {
    trigger: ".o_kanban_record:contains(Project Sharing)",
    content: 'Open the project dropdown.',
    run: "hover && click .o_kanban_record:contains(Project Sharing) .o_dropdown_kanban .dropdown-toggle",
}, {
    trigger: '.dropdown-menu a:contains("Share")',
    content: 'Start editing the project.',
    run: "click",
}, {
    trigger: '.modal div[name="collaborator_ids"] .o_field_x2many_list_row_add > button',
    content: 'Add a collaborator to the project.',
    run: "click",
}, {
    trigger: '.modal div[name="collaborator_ids"] div[name="partner_id"] input',
    content: 'Select the user portal as collaborator to the "Project Sharing" project.',
    run: "edit Georges",
}, {
    trigger: '.ui-autocomplete a.dropdown-item:contains("Georges")',
    run: "click",
}, {
    trigger: '.modal div[name="collaborator_ids"] div[name="access_mode"] input',
    content: 'Open Access mode selection dropdown.',
    run: 'click',
},{
    trigger: '.o_select_menu_item:contains(Edit)',
    run: 'click',
}, {
    trigger: '.modal footer > button[name="action_share_record"]',
    content: 'Confirm the project sharing with this portal user.',
    run: "click",
},
{
    trigger: "body:not(:has(.modal))",
},
{
    trigger: '.o_web_client',
    content: 'Go to project portal view to select the "Project Sharing" project',
    run: function () {
        window.location.href = window.location.origin + '/my/projects';
    },
    expectUnloadPage: true,
}, {
    id: 'project_sharing_feature',
    trigger: 'table > tbody > tr a:has(span:contains(Project Sharing))',
    content: 'Select "Project Sharing" project to go to project sharing feature for this project.',
    run: "click",
    expectUnloadPage: true,
}, {
    trigger: '.o_project_sharing .o_kanban_renderer',
    content: 'Wait the project sharing feature be loaded',
}, {
    trigger: 'button.o-kanban-button-new',
    content: 'Click "Create" button',
    run: 'click',
}, {
    trigger: '.o_kanban_quick_create .o_field_widget[name=name] input',
    content: 'Create Task',
    run: "edit Test Create Task",
}, {
    content: "Check that task stages cannot be drag and dropped",
    trigger: '.o_kanban_group:not(.o_group_draggable)',
}, {
    trigger: '.o_kanban_quick_create .o_kanban_edit',
    content: 'Go to the form view of this new task',
    run: "click",
}, {
    trigger: 'div[name="stage_id"] div.o_statusbar_status button[aria-checked="false"]:contains(Done)',
    content: 'Change the stage of the task.',
    run: "click",
}, {
    trigger: '.o-mail-Composer-input',
    content: 'Write a message in the chatter of the task',
    run: "edit I create a new task for testing purpose.",
}, {
    trigger: '.o-mail-Composer-send:enabled',
    content: 'Send the message',
    run: "click",
}, {
    trigger: 'ol.breadcrumb > li.o_back_button > a:contains(Project Sharing)',
    content: 'Go back to the kanban view',
    run: "click",
}, {
    trigger: '.o_searchview_dropdown_toggler',
    content: 'open the search panel menu',
    run: "click",
}, {
    trigger: '.o_filter_menu .dropdown-item:first-child',
    content: 'click on the first item in the filter menu',
    run: "click",
}, {
    trigger: '.o_group_by_menu .dropdown-item:first-child',
    content: 'click on the first item in the group by menu',
    run: "click",
}, {
    trigger: '.o_favorite_menu .o_add_favorite',
    content: 'open accordion "save current search" in favorite menu',
    run: "click",
}, {
    trigger: '.o_favorite_menu .o_accordion_values .o_save_favorite',
    content: 'click to "save" button in favorite menu',
    run: "click",
}, {
    trigger: '.o_filter_menu .dropdown-item:first-child',
    content: 'click on the first item in the filter menu',
    run: "click",
}, {
    trigger: '.o_group_by_menu .dropdown-item:first-child',
    content: 'click on the first item in the group by menu',
    run: "click",
}, {
    trigger: '.o_favorite_menu .o_accordion_values .o_save_favorite',
    content: 'click to "save" button in favorite menu',
    run: "click",
}, {
    trigger: 'button.o_switch_view.o_list',
    content: 'Go to the list view',
    run: "click",
}, {
    trigger: '.o_list_view',
}, {
    trigger: '.o_optional_columns_dropdown_toggle',
    run: "click",
}, {
    trigger: '.dropdown-item:contains("Milestone")',
}, {
    trigger: '.o_list_view',
    content: 'Check the list view',
}];

registry.category("web_tour.tours").add('project_sharing_tour', {
    url: '/odoo',
    steps: () => {
        return projectSharingSteps;
    }
});

registry.category("web_tour.tours").add("portal_project_sharing_tour", {
    url: "/my/projects",
    steps: () => {
        // The begining of the project sharing feature
        const projectSharingStepIndex = projectSharingSteps.findIndex(s => s?.id === 'project_sharing_feature');
        return projectSharingSteps.slice(projectSharingStepIndex, projectSharingSteps.length);
    }
});

registry.category("web_tour.tours").add("project_sharing_with_blocked_task_tour", {
    url: "/my/projects",
    steps: () => [{
        trigger: 'table > tbody > tr a:has(span:contains("Project Sharing"))',
        content: 'Click on the portal project.',
        run: "click",
        expectUnloadPage: true,
    }, {
        trigger: 'article.o_kanban_record',
        content: 'Click on the task',
        run: "click",
    }, {
        trigger: 'button:contains("Blocked By")',
        content: 'Go to the Block by task tab',
        run: "click",
    }, {
        trigger: 'i:contains("This task is currently blocked by")',
        content: 'Check that the blocked task is not visible',
    },
]});

registry.category("web_tour.tours").add("portal_project_sharing_tour_with_disallowed_milestones", {
    url: "/my/projects",
    steps: () => [
        {
            id: "project_sharing_feature",
            trigger: "table > tbody > tr a:has(span:contains(Project Sharing))",
            content:
                'Select "Project Sharing" project to go to project sharing feature for this project.',
            run: "click",
            expectUnloadPage: true,
        },
        {
            trigger: ".o_project_sharing",
            content: "Wait the project sharing feature be loaded",
        },
        {
            trigger: "button.o_switch_view.o_list",
            content: "Go to the list view",
            run: "click",
        },
        {
            trigger: ".o_list_view",
        },
        {
            trigger: ".o_optional_columns_dropdown_toggle",
            run: "click",
        },
        {
            trigger: ".dropdown-item",
        },
        {
            trigger: ".dropdown-menu",
            run: function () {
                const optionalFields = Array.from(
                    this.anchor.ownerDocument.querySelectorAll(".dropdown-item")
                ).map((e) => e.textContent);

                if (optionalFields.includes("Milestone")) {
                    throw new Error(
                        "the Milestone field should be absent as allow_milestones is set to False"
                    );
                }
            },
        },
    ],
});

registry.category("web_tour.tours").add("test_04_project_sharing_chatter_message_reactions", {
    url: "/my/projects",
    steps: () => [
        {
            trigger: "table > tbody > tr a:has(span:contains(Project Sharing))",
            run: "click",
            expectUnloadPage: true,
        },
        { trigger: ".o_project_sharing" },
        { trigger: ".o_kanban_record:contains('Test Task with messages')", run: "click" },
        { trigger: ".o-mail-Message" },
        { trigger: ".o-mail-Message .o-mail-MessageReaction:contains('👀')" },
    ],
});

registry.category("web_tour.tours").add("portal_project_sharing_chatter_mention_users", {
    url: "/my/projects",
    steps: () => [
        {
            trigger: "table > tbody > tr a:has(span:contains(Project Sharing))",
            run: "click",
            expectUnloadPage: true,
        },
        { trigger: ".o_project_sharing" },
        { trigger: ".o_kanban_record:contains('Test Task')", run: "click" },
        { trigger: ".o-mail-Composer-input", run: "edit @xxx" },
        {
            trigger: "body:not(:has(.o-mail-Composer-suggestion))",
            run: async () => {
                await delay(odoo.loader.modules.get("@mail/core/common/suggestion_hook").DELAY_FETCH);
            },
        },
        { trigger: ".o-mail-Composer-input", run: "edit @Georges" },
        { trigger: ".o-mail-Composer-suggestion:contains('Georges')" },
    ],
});
