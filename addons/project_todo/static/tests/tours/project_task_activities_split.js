/** @odoo-module */

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
            trigger: '.o_activity_record .d-block:contains("New Task!")',
            run: "click",
        }, {
            content: 'Task "New Sub-Task!" is listed in the activity view',
            trigger: '.o_activity_record .d-block:contains("New Sub-Task!")',
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
            trigger: '.o_activity_record .d-block:contains("New To-Do!")',
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
