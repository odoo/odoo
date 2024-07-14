/** @odoo-module **/

/**
 * Add custom steps to go to map and gantt view in Project app
 */
import { registry } from "@web/core/registry";
import "@project/../tests/tours/project_tour";
import { patch } from "@web/core/utils/patch";

function openProjectUpdateAndReturnToTasks(view, viewClass) {
    return [{
            trigger: '.o_project_updates_breadcrumb',
            content: 'Open Project Update from view : ' + view,
            extra_trigger: "." + viewClass,
        }, {
            trigger: ".o-kanban-button-new",
            content: "Create a new update from project task view : " + view,
            extra_trigger: '.o_project_update_kanban_view',
        }, {
            trigger: "button.o_form_button_cancel",
            content: "Discard project update from project task view : " + view,
        }, {
            trigger: ".o_switch_view.o_list",
            content: "Go to list of project update from view " + view,
        }, {
            trigger: '.o_back_button',
            content: 'Go back to the task view : ' + view,
            // extra_trigger: '.o_list_table', // FIXME: [XBO] uncomment it when sample data will be displayed after discarding creation of project update record.
        },
    ];
}

patch(registry.category("web_tour.tours").get("project_test_tour"), {
    steps() {
        const originalSteps = super.steps();
        const taskCreationStepIndex = originalSteps.findIndex((step) => step.id === "quick_create_tasks");

        originalSteps.splice(taskCreationStepIndex + 1, 0, {
            trigger: '.o_switch_view.o_gantt',
            content: 'Open Gantt View',
        }, {
            trigger: '.o_gantt_button_add',
            content: 'Add a task in gantt',
        });

        originalSteps.splice(originalSteps.length, 0, {
            trigger: ".o_gantt_progress_bar",
            content: "See user progress bar",
            run: function () {
                const $progressbar = $(".o_gantt_progress_bar:eq(0)");
                if ($progressbar.length) {
                    if ($progressbar.find("span:eq(0)")[0].style.width === '') {
                        console.error("Progress bar should be displayed");
                    }
                    if (!$progressbar[0].classList.contains("o_gantt_group_danger")) {
                        console.error("Progress bar should be displayed in danger");
                    }
                } else {
                    console.error("Not able to select progressbar");
                }
            }
        }, ...openProjectUpdateAndReturnToTasks("Gantt", "o_gantt_view"), {
            trigger: '.o_switch_view.o_map',
            content: 'Open Map View',
        }, ...openProjectUpdateAndReturnToTasks("Map", "o_map_view"));

        return originalSteps;
    }
});
