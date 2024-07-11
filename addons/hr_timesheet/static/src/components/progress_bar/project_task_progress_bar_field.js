/** @odoo-module **/

import { registry } from "@web/core/registry";
import { progressBarField, ProgressBarField } from "@web/views/fields/progress_bar/progress_bar_field";

export class ProjectTaskProgressBarField extends ProgressBarField {
    get progressBarColorClass() {
        if (this.currentValue > this.maxValue) {
            return super.progressBarColorClass;
        }

        return this.currentValue < 80 ? "bg-success" : "bg-warning";
    }
}

export const projectTaskProgressBarField = {
    ...progressBarField,
    component: ProjectTaskProgressBarField,
};

registry.category("fields").add("project_task_progressbar", projectTaskProgressBarField);
