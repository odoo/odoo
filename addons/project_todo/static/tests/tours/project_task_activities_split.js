import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add('project_task_activities_split', {
    url: '/odoo',
    steps: () => [
        {
            content: 'Open Activity Systray',
            trigger: '.o-mail-ActivityMenu-counter',
            run: "click",
        }, {
            content: 'Open Task Activities',
            trigger: '.o-mail-ActivityGroup:contains("Task")',
            run: "click",
        }, {
            content: 'Task "New Task!" is listed in the activity view',
            trigger: 'td.o_data_cell:contains("New Task!")',
        }, {
            trigger: ".o_control_panel_navigation button i.fa-sliders",
            content: "Open embedded actions dropdown",
            run: "click",
        }, {
            content: 'Click on `Show Sub-Tasks` button to see sub-tasks in the main view',
            trigger: "span.o-dropdown-item:contains('Show Sub-Tasks')",
            run: 'click',
        }, {
            content: 'Task "New Sub-Task!" is listed in the activity view',
            trigger: 'td.o_data_cell:contains("New Sub-Task!")',
            run: () => {
                const nodes = document.querySelectorAll(".o_activity_record .d-block");
                for (const node of nodes) {
                    if (node.textContent === "New To-do!") {
                        console.error('Private task records with no parent task should not appear in this view');
                    }
                }
            },
        }, {
            content: 'Open Activity Systray',
            trigger: '.o-mail-ActivityMenu-counter',
            run: "click",
        }, {
            content: 'Open To-Do Activities',
            trigger: '.o-mail-ActivityGroup:contains("To-Do")',
            run: "click",
        }, {
            content: 'Record "New To-Do!" is listed in the activity view',
            trigger: 'td.o_data_cell:contains("New To-Do!")',
            run: () => {
                const nodes = document.querySelectorAll(".o_activity_record .d-block");
                for (const node of nodes) {
                    if (node.textContent === "New Task!" || node.textContent === "New Sub-Task!") {
                        console.error('Tasks linked to a project should not appear in this view');
                    }
                }
            },
        }
    ],
});
