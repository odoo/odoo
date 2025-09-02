import { registry } from "@web/core/registry";

function newProject(i) {
    return [
        {
            trigger: ".o-kanban-button-new",
            run: "click",
        },
        {
            trigger: ".modal .o_project_name input",
            run: `edit new project ${i}`,
        },
        {
            //You can use HOOT pseudo-selector for trigger
            trigger: ".modal button:contains(/^Create project$/)",
            run: "click",
        },
        {
            trigger: ".o_breadcrumb a:contains(projects)",
            run: "click",
        },
        // {
        //     content: "This step causes a indeterminism",
        //     trigger: "nav a:contains(project)",
        // },
    ];
}

registry.category("web_tour.tours").add("example_of_tour1", {
    steps: () => [
        ...newProject(1),
        ...newProject(3),
        ...newProject(6),
        ...newProject(9),
        {
            content: "Click on already existing project",
            trigger: "article:contains(project 1)",
            run: "click",
        },
        {
            content: "Click on create a new task in todo list",
            trigger: ".o_kanban_group:contains(to do) .o_kanban_quick_add",
            run: "click",
        },
        {
            content: "Choose a name for your task",
            trigger: ".o_kanban_quick_create input",
            //Write && to chain interactions
            run: "edit(my new super task !) && press(Enter)",
            // run: "edit my new super task ! && press Enter",
        },
        {
            trigger: "body",
            pause: true,
        },
    ],
});
