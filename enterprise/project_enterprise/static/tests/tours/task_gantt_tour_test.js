/**
 * Add custom steps to go to map and gantt view in Project app
 */
import { registry } from "@web/core/registry";
import "@project/../tests/tours/project_tour";
import { patch } from "@web/core/utils/patch";


patch(registry.category("web_tour.tours").get("project_test_tour"), {
    steps() {
        const originalSteps = super.steps();
        const taskCreationStepIndex = originalSteps.findIndex((step) => step.id === "quick_create_tasks");

        originalSteps.splice(taskCreationStepIndex + 1, 0, {
            trigger: '.o_switch_view.o_gantt',
            content: 'Open Gantt View',
            run: "click",
        }, {
            id: 'gantt_add_task',
            trigger: '.o_gantt_button_add',
            content: 'Add a task in gantt',
            run: "click",
        });

        originalSteps.splice(originalSteps.length, 0, {
            trigger: ".o_gantt_renderer_controls .dropdown:nth-child(2)",
            content: "Open range menu",
            run: "click",
        },
        {
            trigger: '.o_gantt_range_menu .dropdown-item:nth-child(3)',
            content: 'Select "This Month"',
            run: "click",
        },
        {
            trigger: ".o_gantt_progress_bar.o_gantt_group_danger",
            content: "See user progress bar",
        })
        return originalSteps;
    }
});
