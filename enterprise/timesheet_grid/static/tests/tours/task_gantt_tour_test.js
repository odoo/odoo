import { registry } from "@web/core/registry";
import { patch } from "@web/core/utils/patch";
import "@project_enterprise/../tests/tours/task_gantt_tour_test";

patch(registry.category("web_tour.tours").get("project_test_tour"), {
    steps() {
        const originalSteps = super.steps();
        const ganttAddTaskStepIndex = originalSteps.findIndex(
            (step) => step.id === "gantt_add_task"
        );
        originalSteps.splice(ganttAddTaskStepIndex + 1, 0, {
            trigger: 'div[name="allocated_hours"] input',
            content: "Set allocated_hours",
            run: "edit 200",
        });
        return originalSteps;
    },
});
